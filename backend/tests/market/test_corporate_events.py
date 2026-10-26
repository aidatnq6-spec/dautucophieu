from datetime import date

from investment_agent.market.corporate_events import EventStore, due_reminders, normalise, render_reminders

RAW = [
    {"id": 1, "symbol": "MBB", "event_code": "DIV", "event_title_vi": "Trả cổ tức bằng tiền mặt - Cả năm 2025 - 1,000 VND",
     "exright_date": "2026-11-03 00:00:00+07:00", "record_date": "2026-11-04 00:00:00+07:00", "payout_date": "2026-11-17 00:00:00+07:00",
     "display_date1": "2026-11-03 00:00:00+07:00", "exercise_ratio": 0.1, "value_per_share": 1000.0},
    {"id": 2, "symbol": "MBB", "event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Trả Cổ tức bằng Cổ phiếu tỉ lệ 15.0%",
     "exright_date": "2026-11-20 00:00:00+07:00", "record_date": None, "payout_date": None, "display_date1": "2026-11-20 00:00:00+07:00",
     "exercise_ratio": 0.15, "value_per_share": None},
    {"id": 3, "symbol": "MBB", "event_code": "AGME", "event_title_vi": "MBB - Tổ chức ĐHĐCĐ bất thường 2026",
     "exright_date": "2026-10-01 00:00:00+07:00", "record_date": "2026-10-02 00:00:00+07:00", "payout_date": None,
     "display_date1": "2026-10-30 00:00:00+07:00", "exercise_ratio": None, "value_per_share": None},
    {"id": 4, "symbol": "MBB", "event_code": "DDIND", "event_title_vi": "Nguyễn Văn A - Đăng kí Mua 100 MBB",
     "exright_date": None, "record_date": None, "payout_date": None, "display_date1": "2026-10-28 00:00:00+07:00",
     "exercise_ratio": None, "value_per_share": None},
    {"id": 5, "symbol": "MBB", "event_code": "DIV", "event_title_vi": "Trả cổ tức - chưa có ngày", "exright_date": None,
     "record_date": None, "payout_date": None, "display_date1": None, "exercise_ratio": None, "value_per_share": 500.0},
]


def test_events_are_normalised_with_the_date_that_matters():
    out = {e["id"]: e for e in normalise(RAW)}
    assert out["MBB-1"]["kind"] == "dividend_cash" and out["MBB-1"]["key_date"] == "2026-11-03" and out["MBB-1"]["payout"] == "2026-11-17"
    assert out["MBB-2"]["kind"] == "issue" and out["MBB-2"]["key_date"] == "2026-11-20"
    assert out["MBB-3"]["kind"] == "meeting" and out["MBB-3"]["key_date"] == "2026-10-30"  # the meeting day, not the record date
    assert out["MBB-4"]["kind"] == "insider"
    assert out["MBB-5"]["key_date"] is None


def test_reminders_cover_the_next_five_days_once_and_skip_insiders_and_undated(tmp_path):
    store = EventStore(tmp_path)
    store.save("MBB", normalise(RAW), fetched_at="2026-10-26T15:40:00+07:00")
    due = due_reminders(store, symbols=["MBB"], today=date(2026, 10, 29), days=5)
    assert [e["id"] for e in due] == ["MBB-3", "MBB-1"]  # meeting 30/10, dividend ex-date 03/11; issue 20/11 is too far
    store.mark_notified([e["id"] for e in due])
    assert due_reminders(store, symbols=["MBB"], today=date(2026, 10, 29), days=5) == []


def test_reminder_text_names_dates_and_amounts_and_marks_held_tickers():
    events = [e for e in normalise(RAW) if e["id"] in ("MBB-1", "MBB-3")]
    text = render_reminders(events, held={"MBB"}, today=date(2026, 10, 29))
    assert "LỊCH SỰ KIỆN 5 NGÀY TỚI" in text
    assert "MBB (đang nắm)" in text and "GDKHQ 03/11/2026" in text and "1.000 đ/cp" in text and "trả 17/11/2026" in text
    assert "ĐHĐCĐ bất thường 2026" in text and "họp 30/10/2026" in text
    assert "không phải khuyến nghị" in text


def test_run_refreshes_stale_tickers_then_reminds_once(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from investment_agent.market.corporate_events import events_run
    (tmp_path / "market-symbols.txt").write_text("MBB\nFPT\n", encoding="utf-8")
    fetched, sent = [], []

    def fetch(symbol):
        fetched.append(symbol)
        if symbol == "FPT":
            raise OSError("rate limited")
        return RAW
    now = datetime(2026, 10, 29, 15, 40, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    out = events_run(tmp_path, fetch=fetch, notify=lambda due: sent.append([e["id"] for e in due]) or True, now=now, pace=0)
    assert out == {"status": "ok", "refreshed": 1, "errors": {"FPT": "OSError"}, "reminded": 2}
    assert sent == [["MBB-3", "MBB-1"]]
    again = events_run(tmp_path, fetch=fetch, notify=lambda due: sent.append(due) or True, now=now, pace=0)
    assert fetched.count("MBB") == 1 and again["reminded"] == 0 and len(sent) == 1  # fresh data kept, nothing reminded twice


def test_a_failed_send_is_retried_next_run(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from investment_agent.market.corporate_events import events_run
    (tmp_path / "market-symbols.txt").write_text("MBB\n", encoding="utf-8")
    now = datetime(2026, 10, 29, 15, 40, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    assert events_run(tmp_path, fetch=lambda s: RAW, notify=lambda due: False, now=now, pace=0)["reminded"] == 0
    assert events_run(tmp_path, fetch=lambda s: RAW, notify=lambda due: True, now=now, pace=0)["reminded"] == 2
