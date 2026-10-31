from datetime import datetime, timezone
from decimal import Decimal

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.price_alerts import AlertError, change_alerts, check_alerts, read_alerts

OWNER = OwnerContext("owner-1", "owner", "test")
NOW = datetime(2026, 11, 2, 3, 30, tzinfo=timezone.utc)  # 10:30 in Hà Nội
ALLOWED = {"FPT", "HPG", "VNINDEX"}


def _repo():
    return PersonalRepository("owner-1", MemoryDocumentStore())


def test_alerts_are_added_validated_and_removed():
    repo = _repo()
    alerts, version = change_alerts(repo, OWNER, {"action": "add", "symbol": "fpt", "op": "above", "price": "56.3"}, expected_version=0,
                                    request_id="a1", allowed=ALLOWED, now=NOW)
    assert version == 1 and alerts[0] | {"id": "x"} == {"id": "x", "symbol": "FPT", "op": "above", "price": "56.3", "created_at": NOW.isoformat(),
                                                        "triggered_at": None, "triggered_price": None}
    for bad, code in (({"action": "add", "symbol": "ZZZ", "op": "above", "price": "1"}, "symbol_not_watched"),
                      ({"action": "add", "symbol": "FPT", "op": "near", "price": "1"}, "invalid_alert"),
                      ({"action": "add", "symbol": "FPT", "op": "below", "price": "-1"}, "invalid_alert"),
                      ({"action": "add", "symbol": "FPT", "op": "below", "price": "56,3"}, "invalid_alert"),  # the page sends plain decimals
                      ({"action": "remove", "id": "nope"}, "alert_not_found")):
        with pytest.raises(AlertError) as err:
            change_alerts(repo, OWNER, bad, expected_version=1, request_id="bad", allowed=ALLOWED, now=NOW)
        assert err.value.code == code
    alerts, version = change_alerts(repo, OWNER, {"action": "remove", "id": alerts[0]["id"]}, expected_version=1, request_id="a2", allowed=ALLOWED, now=NOW)
    assert alerts == [] and version == 2


def test_a_level_crossed_is_sent_once_with_the_price_then_can_be_armed_again():
    repo = _repo()
    change_alerts(repo, OWNER, {"action": "add", "symbol": "HPG", "op": "below", "price": "20"}, expected_version=0, request_id="a1", allowed=ALLOWED, now=NOW)
    change_alerts(repo, OWNER, {"action": "add", "symbol": "VNINDEX", "op": "above", "price": "1800"}, expected_version=1, request_id="a2",
                  allowed=ALLOWED, now=NOW)
    texts = []
    out = check_alerts(repo, OWNER, prices={"HPG": Decimal("19.95"), "VNINDEX": Decimal("1741.62")}, send=lambda t: texts.append(t) or True,
                       now=NOW, request_id="c1")
    assert out == {"status": "ok", "triggered": 1, "sent": True}
    assert "Cảnh báo giá" in texts[0] and "HPG 19,95 ≤ 20,00 (mức bạn đặt)" in texts[0] and "Không phải khuyến nghị" in texts[0]
    alerts, version = read_alerts(repo, OWNER)
    hpg = next(a for a in alerts if a["symbol"] == "HPG")
    assert hpg["triggered_at"] == NOW.isoformat() and hpg["triggered_price"] == "19.95"
    assert check_alerts(repo, OWNER, prices={"HPG": Decimal("19.5")}, send=lambda t: texts.append(t) or True, now=NOW, request_id="c2")["triggered"] == 0
    change_alerts(repo, OWNER, {"action": "rearm", "id": hpg["id"]}, expected_version=version, request_id="a3", allowed=ALLOWED, now=NOW)
    assert check_alerts(repo, OWNER, prices={"HPG": Decimal("19.5")}, send=lambda t: True, now=NOW, request_id="c3")["triggered"] == 1


def test_a_failed_delivery_leaves_the_alert_armed_and_a_missing_price_never_triggers():
    repo = _repo()
    change_alerts(repo, OWNER, {"action": "add", "symbol": "FPT", "op": "above", "price": "50"}, expected_version=0, request_id="a1", allowed=ALLOWED, now=NOW)
    assert check_alerts(repo, OWNER, prices={}, send=lambda t: True, now=NOW, request_id="c1")["triggered"] == 0
    assert check_alerts(repo, OWNER, prices={"FPT": Decimal("52.7")}, send=lambda t: False, now=NOW, request_id="c2")["sent"] is False
    assert read_alerts(repo, OWNER)[0][0]["triggered_at"] is None
