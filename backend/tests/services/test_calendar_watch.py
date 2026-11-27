import json
from datetime import date, datetime

from investment_agent.services.calendar_watch import NEWS_URL, watch_calendar

TS = int(datetime(2026, 12, 30, 9, 0).timestamp())


def feed(*titles):
    return json.dumps({"data": {"list": [{"id": 2500000 + i, "title": t, "postedDate": TS} for i, t in enumerate(titles)]}})


def test_a_change_to_this_years_calendar_is_told_even_when_its_file_exists(tmp_path):
    # HOSE added 24/11/2026 (Ngày Văn hóa Việt Nam) on 11/11/2026 while the 2026 file existed; the watch used to stop once a file was there
    config, data = tmp_path / "config", tmp_path / "data"; config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    get = lambda u: feed("HOSE: Cập nhật chỉ số VN30 kỳ tháng 11/2026",  # noqa: E731
                         "HOSE: Thông báo về lịch nghỉ giao dịch Ngày Văn hóa Việt Nam năm 2026")
    sent = []
    out = watch_calendar(data, config, get=get, send=lambda t: sent.append(t) or True, today=date(2026, 11, 11))
    assert out == {"status": "ok", "watching": [2026], "looking_for": [], "sent": 1}
    assert sent == ["Lịch giao dịch HOSE 2026: HOSE vừa đăng “HOSE: Thông báo về lịch nghỉ giao dịch Ngày Văn hóa Việt Nam năm 2026” "
                    "(30/12/2026) https://www.hsx.vn/tin-tuc/tin-hose/chi-tiet/2500001\n"
                    "Kiểm lại config/trading-calendar-hose-2026.json: thông báo này có thể thêm hoặc đổi ngày nghỉ của năm đang dùng."]
    assert watch_calendar(data, config, get=get, send=lambda t: True, today=date(2026, 11, 12))["sent"] == 0  # told once


def test_a_holiday_notice_for_next_year_is_told_once_with_its_link(tmp_path):
    config, data = tmp_path / "config", tmp_path / "data"; config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    get = lambda u: feed("HOSE: Cập nhật chỉ số VN30 kỳ tháng 12/2026",  # noqa: E731
                         "HOSE: Thông báo lịch nghỉ giao dịch Tết Dương lịch và Tết Nguyên đán năm 2027")
    sent = []
    out = watch_calendar(data, config, get=get, send=lambda t: sent.append(t) or True, today=date(2026, 12, 30))
    assert out == {"status": "ok", "watching": [2026, 2027], "looking_for": [2027], "sent": 1} and NEWS_URL.startswith("https://api.hsx.vn/")
    assert sent == ["Lịch giao dịch HOSE 2027: HOSE vừa đăng “HOSE: Thông báo lịch nghỉ giao dịch Tết Dương lịch và Tết Nguyên đán năm 2027” "
                    "(30/12/2026) https://www.hsx.vn/tin-tuc/tin-hose/chi-tiet/2500001\n"
                    "Phần mềm chưa có tệp config/trading-calendar-hose-2027.json: gửi thông báo này để tạo lịch theo đúng số ngày nghỉ HOSE công bố."]
    again = watch_calendar(data, config, get=get, send=lambda t: sent.append(t) or True, today=date(2026, 12, 31))
    assert again["sent"] == 0 and len(sent) == 1


def test_a_note_not_sent_is_tried_again(tmp_path):
    config, data = tmp_path / "config", tmp_path / "data"; config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    get = lambda u: feed("HOSE: Lịch nghỉ giao dịch năm 2027")  # noqa: E731
    assert watch_calendar(data, config, get=get, send=lambda t: False, today=date(2026, 12, 20))["sent"] == 0
    assert watch_calendar(data, config, get=get, send=lambda t: True, today=date(2026, 12, 21))["sent"] == 1


def test_this_years_missing_calendar_is_looked_for_in_any_month_and_a_failing_feed_is_said(tmp_path):
    config = tmp_path / "config"; config.mkdir()
    def boom(url):
        raise OSError("down")
    out = watch_calendar(tmp_path / "data", config, get=boom, send=lambda t: True, today=date(2027, 3, 2))
    assert out == {"status": "source_error", "watching": [2027], "looking_for": [2027], "sent": 0}
