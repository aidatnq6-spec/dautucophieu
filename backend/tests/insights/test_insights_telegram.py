from types import SimpleNamespace

from investment_agent.insights.store import InsightStore
from investment_agent.insights.summary import link, summarise
from investment_agent.insights.telegram import render_insight, send_new
from investment_agent.notifications.telegram import SendOutcome


def s(sector, effect):
    return {"sector": sector, "effect": effect, "reason": f"lý do {sector}", "quote": "q", "page": 2}


RECORD = {"source": "acbs", "ref_id": "vi-mo-10", "title": "Cập nhật vĩ mô tháng 10/2026", "page_url": "https://acbs.com.vn/x",
          "published": "2026-10-01", "status": "ok", "telegram_sent": False,
          "insight": {"macro_now": {"view": "favourable", "reasons": [{"text": "GDP tăng 7,5%", "quote": "q", "page": 1}]},
                      "macro_outlook": {"view": "unfavourable", "reasons": []},
                      "sectors": [s("Ngân hàng", "benefit"), s("Bất động sản", "harm")]
                      + [s(f"Ngành {i}", "benefit") for i in range(6)]}}


def linked(record):
    return link(summarise([record]), sectors={"BID": "Ngân hàng", "KDH": "Bất động sản"},
                valuation_rows=[{"symbol": "BID", "verdict": "cheap"}, {"symbol": "KDH", "verdict": "expensive"}], held={"KDH"})["sectors"]


def test_message_has_title_macro_sectors_with_tickers_and_link():
    text = render_insight(RECORD, linked(RECORD))
    assert "Cập nhật vĩ mô tháng 10/2026" in text and "ACBS" in text
    assert "Vĩ mô hiện tại: Thuận lợi" in text and "6–12 tháng: Bất lợi" in text and "GDP tăng 7,5%" in text
    assert "Ngân hàng" in text and "BID (Rẻ)" in text
    assert "KDH (Đắt) ⚠ đang nắm" in text
    assert text.count("\n+ ") == 5  # at most five benefiting sectors
    assert "https://acbs.com.vn/x" in text and "không phải khuyến nghị" in text


class Sender:
    def __init__(self, status="sent"):
        self.sent, self.status = [], status

    def send(self, chat_id, text):
        self.sent.append((chat_id, text))
        return SendOutcome(self.status)


ON = SimpleNamespace(enabled=True, scheduled_enabled=True, chat_id="-1001234")


def test_new_reports_are_sent_once_and_marked(tmp_path):
    store = InsightStore(tmp_path)
    store.save(RECORD)
    store.save({**RECORD, "ref_id": "bad", "status": "no_reliable_claims", "insight": None})
    sender = Sender()
    assert send_new(store, sender, ON, lambda r: "msg " + r["ref_id"]) == {"sent": 1, "failed": 0}
    assert sender.sent == [("-1001234", "(1/1)\nmsg vi-mo-10")]  # split_message numbers the parts
    assert store.read("acbs", "vi-mo-10")["telegram_sent"] is True
    assert send_new(store, sender, ON, lambda r: "again") == {"sent": 0, "failed": 0}


def test_nothing_is_sent_when_scheduled_sending_is_off_or_fails(tmp_path):
    store = InsightStore(tmp_path)
    store.save(RECORD)
    sender = Sender()
    assert send_new(store, sender, SimpleNamespace(enabled=True, scheduled_enabled=False, chat_id="-1001234"), lambda r: "x") == {"sent": 0, "failed": 0}
    assert sender.sent == []
    assert send_new(store, Sender("failed"), ON, lambda r: "x") == {"sent": 0, "failed": 1}
    assert store.read("acbs", "vi-mo-10")["telegram_sent"] is False
