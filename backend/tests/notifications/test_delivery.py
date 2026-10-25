import json
import logging

import httpx
import pytest

from investment_agent.notifications.outbox import DeliveryStore, NotificationSettings, deliver
from investment_agent.notifications.render import MAX_MESSAGE, render_report, split_message
from investment_agent.notifications.telegram import TelegramSender

TOKEN = "123456789:" + "A" * 35
REPORT = {"report_id": "ab" * 16, "session_date": "2026-10-23", "status": "published", "provenance": "synthetic", "report_version": "1",
          "decision": {"action": "hold", "headline": "Giữ phân bổ hiện tại", "reasons": ["outside_research_universe"]},
          "ledger_summary": {"cash": "95000000", "realized_gain": "0", "dividend_income": "0", "dividend_receivable": "0", "net_contributions": "100000000"},
          "holdings": [{"security_id": "FPT", "quantity": 100, "market_value": "6000000", "unrealized_gain": "1000000", "weight_of_capital": "0.006",
                        "price_date": "2026-10-23"}],
          "items": [{"entity_id": "FPT", "action": "hold", "reasons": ["outside_research_universe"]}],
          "narrative": {"source": "no_ai", "text": "Thị trường đi ngang."}, "verification_flags": ["universe_incomplete"], "sources": ["doc-1"]}
ENABLED = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=False)


def test_render_has_portfolio_market_opportunity_and_risk_sections():
    text = render_report(REPORT)
    for heading in ("DANH MỤC", "THỊ TRƯỜNG", "CƠ HỘI", "RỦI RO"):
        assert heading in text
    assert "6.000.000 đ" in text and "FPT" in text and "dữ liệu synthetic" in text


def test_split_respects_limit_and_loses_nothing():
    text = "\n".join(f"Dòng {i}: " + "x" * 300 for i in range(60)) + "\n" + "y" * 9000
    parts = split_message(text)
    assert len(parts) > 2 and all(len(p) <= MAX_MESSAGE for p in parts)
    body = "".join(p.split("\n", 1)[1] for p in parts)
    assert body.replace("\n", "") == text.replace("\n", "")
    assert parts[0].startswith(f"(1/{len(parts)})")


class Transport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def __call__(self, request):
        self.calls.append(json.loads(request.content))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def ok(message_id):
    return httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})


def sender(transport, sleeps=None):
    return TelegramSender(TOKEN, client=httpx.Client(transport=httpx.MockTransport(transport)), sleep=sleeps.append if sleeps is not None else (lambda s: None), max_retries=2)


def long_report():
    return {**REPORT, "narrative": {"source": "no_ai", "text": "z" * 5000}}


def test_disabled_settings_send_nothing(tmp_path):
    t = Transport()
    result = deliver(long_report(), NotificationSettings(enabled=False, chat_id=None, members_may_view_personal_data=False, scheduled_enabled=False),
                     sender(t), DeliveryStore(tmp_path / "d.sqlite"))
    assert result.status == "disabled" and t.calls == []


def test_enabling_requires_member_acknowledgement():
    with pytest.raises(ValueError):
        NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=False, scheduled_enabled=False)


def test_parts_sent_in_order_with_message_ids(tmp_path):
    t = Transport(ok(11), ok(12))
    store = DeliveryStore(tmp_path / "d.sqlite")
    result = deliver(long_report(), ENABLED, sender(t), store)
    assert result.status == "sent" and [c["chat_id"] for c in t.calls] == ["-100123", "-100123"]
    assert [p.message_id for p in store.parts(REPORT["report_id"], "-100123")] == [11, 12]
    assert "parse_mode" not in t.calls[0]  # plain text: no escaping hazards


def test_rate_limit_retries_are_bounded_and_honour_retry_after(tmp_path):
    limited = httpx.Response(429, json={"ok": False, "error_code": 429, "parameters": {"retry_after": 3}})
    sleeps = []
    t = Transport(limited, limited, limited)
    result = deliver(REPORT, ENABLED, sender(t, sleeps), DeliveryStore(tmp_path / "d.sqlite"))
    assert result.status == "retryable" and len(t.calls) == 3 and sleeps == [3, 3]


def test_timeout_is_unknown_and_not_resent_automatically(tmp_path):
    store = DeliveryStore(tmp_path / "d.sqlite")
    t = Transport(httpx.ReadTimeout("slow"))
    assert deliver(REPORT, ENABLED, sender(t), store).status == "unknown"
    again = Transport(ok(5))
    assert deliver(REPORT, ENABLED, sender(again), store).status == "unknown" and again.calls == []
    store.resolve_unknown(REPORT["report_id"], "-100123", 0, outcome="not_received")
    assert deliver(REPORT, ENABLED, sender(again), store).status == "sent" and len(again.calls) == 1


def test_failure_on_part_two_never_resends_part_one(tmp_path):
    store = DeliveryStore(tmp_path / "d.sqlite")
    t = Transport(ok(21), httpx.Response(500, json={"ok": False}), httpx.Response(500, json={"ok": False}), httpx.Response(500, json={"ok": False}))
    assert deliver(long_report(), ENABLED, sender(t), store).status == "retryable"
    retry = Transport(ok(22))
    assert deliver(long_report(), ENABLED, sender(retry), store).status == "sent"
    assert len(retry.calls) == 1 and retry.calls[0]["text"].startswith("(2/2)")


def test_permanent_error_fails_without_retry(tmp_path):
    t = Transport(httpx.Response(403, json={"ok": False, "error_code": 403, "description": "bot was kicked"}))
    assert deliver(REPORT, ENABLED, sender(t), DeliveryStore(tmp_path / "d.sqlite")).status == "failed" and len(t.calls) == 1


def test_token_never_in_logs_or_errors(tmp_path, caplog):
    t = Transport(httpx.ConnectError(f"cannot reach https://api.telegram.org/bot{TOKEN}/sendMessage"))
    with caplog.at_level(logging.DEBUG):
        result = deliver(REPORT, ENABLED, sender(t), DeliveryStore(tmp_path / "d.sqlite"))
    assert TOKEN not in caplog.text and TOKEN not in str(result)


def test_report_version_change_creates_new_delivery(tmp_path):
    store = DeliveryStore(tmp_path / "d.sqlite")
    deliver(REPORT, ENABLED, sender(Transport(ok(1))), store)
    t = Transport(ok(2))
    assert deliver({**REPORT, "report_version": "2"}, ENABLED, sender(t), store).status == "sent" and len(t.calls) == 1
    assert deliver(REPORT, ENABLED, sender(Transport()), store).status == "sent"  # already delivered, nothing resent
