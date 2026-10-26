"""Reproductions of the whole-branch review findings (Important 1-5)."""
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from investment_agent.brief.news import parse_rss, pick_news, window_items
from investment_agent.brief.snapshot import BriefStore, build_snapshot
from investment_agent.brief.view import market_for_session, market_view
from investment_agent.notifications.outbox import DeliveryStore, NotificationSettings, deliver
from investment_agent.notifications.render import render_report
from investment_agent.notifications.telegram import SendOutcome

VN = ZoneInfo("Asia/Ho_Chi_Minh")
ON = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=True)
REPORT = {"report_id": "cd" * 16, "session_date": "2026-10-26", "status": "published", "report_version": "1", "provenance": "x",
          "decision": {"headline": "Giữ phân bổ hiện tại", "reasons": []}, "reminders": [],
          "ledger_summary": {"cash": "0", "realized_gain": "0", "dividend_income": "0"}, "holdings": [], "items": [],
          "narrative": {"text": ""}, "verification_flags": [], "sources": []}


def market(news_count):
    return {"session_date": "2026-10-26", "indices": {"status": "missing", "rows": []}, "board": {"status": "missing", "reason": "x"},
            "hose": {"status": "missing", "reason": "x"}, "proprietary": {"status": "missing", "reason": "x"}, "tickers": [],
            "news": {"status": "ok", "items": [{"title": f"Tin {i} " + "x" * 1000, "url": f"https://x.vn/{i}", "source": "CafeF",
                                                "published": "2026-10-26T10:00:00+07:00", "reason": "vĩ mô"} for i in range(news_count)]}}


class Sender:
    def __init__(self, fail_at=()):
        self.sent, self.fail_at = [], set(fail_at)

    def send(self, chat_id, text):
        n = len(self.sent)
        self.sent.append(text)
        return SendOutcome("retryable" if n in self.fail_at else "sent", message_id=n + 1)


# Important 1: a retry resends the text that was frozen at the first attempt, even if the snapshot changed since.
def test_a_retry_sends_the_frozen_parts_even_when_the_market_changed(tmp_path):
    import investment_agent.notifications.render as render
    store = DeliveryStore(tmp_path / "d.sqlite")
    first = Sender(fail_at={1})
    long_market = market(10)  # long news titles: more than one Telegram part
    assert deliver(REPORT, ON, first, store, long_market).status != "sent"
    frozen = render.split_message(render_report(REPORT, long_market))
    assert len(frozen) > 1
    second = Sender()
    result = deliver(REPORT, ON, second, store, market(0))  # the snapshot now renders shorter
    assert result.status == "sent" and result.parts_total == len(frozen)
    assert second.sent == frozen[1:]


# Important 2: a broken snapshot or watchlist never breaks the brief.
def test_broken_snapshot_or_watchlist_gives_no_market_instead_of_an_error(tmp_path, monkeypatch):
    (tmp_path / "brief").mkdir()
    (tmp_path / "brief" / "2026-10-26.json").write_text("[1, 2]", encoding="utf-8")
    assert BriefStore(tmp_path).read("2026-10-26") is None
    (tmp_path / "brief" / "2026-10-26.json").write_text(json.dumps({"session_date": "2026-10-26", "board": {"status": "ok"}}), encoding="utf-8")
    import investment_agent.brief.view as view
    monkeypatch.setattr(view, "load_watchlist", lambda d: (_ for _ in ()).throw(ValueError("corrupt index-groups.json")))
    assert market_for_session(tmp_path, set())("2026-10-26") is None


def test_a_drifted_snapshot_renders_without_raising(tmp_path):
    (tmp_path / "brief").mkdir()
    bad = {"session_date": "2026-10-26", "indices": {"status": "ok", "rows": [{"id": "VNINDEX", "status": "ok"}]},
           "board": {"status": "ok", "symbols": {"FPT": {"pct": "abc"}}}}
    (tmp_path / "brief" / "2026-10-26.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    view = market_for_session(tmp_path, {"FPT"})("2026-10-26")
    text = render_report(REPORT, view)  # either the short text or, when the view is unusable, the old text
    assert "BẢN TIN SAU PHIÊN" in text


# Important 3: no price is not the same as no trade.
def test_held_ticker_without_a_board_reads_no_price_not_no_trade():
    snap = {"session_date": "2026-10-26", "board": {"status": "missing", "reason": "Không tải được bảng giá cả sàn"}}
    v = market_view(snap, watched=[], held={"FPT"})
    assert v["tickers"][0]["state"] == "no_price"
    traded = {"session_date": "2026-10-26", "board": {"status": "ok", "symbols": {"FPT": {"price": None, "pct": None, "change": None, "sector": "x"}}}}
    assert market_view(traded, watched=[], held={"FPT", "PVS"})["tickers"][0]["state"] == "no_trade"  # FPT on board, no match today
    assert {t["symbol"]: t["state"] for t in market_view(traded, watched=[], held={"FPT", "PVS"})["tickers"]}["PVS"] == "no_price"
    text = render_report(REPORT, {**market(0), "tickers": [{"symbol": "PVS", "price": None, "change": None, "pct": None, "held": True,
                                                              "sector": None, "state": "no_price"}]})
    assert "PVS: chưa có giá" in text and "chưa giao dịch" not in text


# Important 4: a later run keeps the session's earlier headlines that have since rotated out of the feeds.
def test_news_of_the_session_survive_feed_rotation(tmp_path):
    def rss(title, hhmm, day="26"):
        return (f"<rss><item><title>{title}</title><link>https://cafef.vn/{abs(hash(title))}.chn</link>"
                f"<pubDate>Mon, {day} Oct 2026 {hhmm}:00 +0700</pubDate></item></rss>")
    base = dict(session_date=date(2026, 10, 26), previous_session=date(2026, 10, 23),
                listing=lambda: {"symbols": [], "icb_names": {}}, board=lambda s: [], series=lambda i: [],
                hose_get=lambda u: json.dumps({"data": []}), store=BriefStore(tmp_path))
    build_snapshot(**base, now=datetime(2026, 10, 26, 15, 40, tzinfo=VN), rss_get=lambda u: rss("Tin chiều phiên", "14:00"))
    later = build_snapshot(**base, now=datetime(2026, 10, 27, 7, 0, tzinfo=VN), rss_get=lambda u: rss("Tin sáng hôm sau", "06:30", "27"))
    titles = [i["title"] for i in later["news"]["items"]]
    assert "Tin chiều phiên" in titles


# Important 5: newest-first must compare instants, not strings with different offsets.
def test_newest_first_compares_instants_across_offsets():
    a = parse_rss("<rss><item><title>A</title><link>https://x.vn/a</link><pubDate>Mon, 26 Oct 2026 09:00:00 +0000</pubDate></item></rss>", "Vneconomy")
    b = parse_rss("<rss><item><title>B</title><link>https://x.vn/b</link><pubDate>Mon, 26 Oct 2026 15:00:00 +0700</pubDate></item></rss>", "CafeF")
    out = window_items(a + b, since=datetime(2026, 10, 26, 0, tzinfo=VN), until=datetime(2026, 10, 27, tzinfo=VN))
    assert [i["title"] for i in out] == ["A", "B"]  # 09:00Z is 16:00 in Hà Nội, newer than 15:00
    assert a[0]["published"].endswith("+07:00")
    picked = pick_news([{**b[0]}, {**a[0], "title": "A lãi suất"}, {**b[0], "title": "B lãi suất"}], watched=[], held=set(), sector_names=set(), limit=1)
    assert picked[0]["title"] == "A lãi suất"
