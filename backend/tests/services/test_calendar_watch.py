import json
from datetime import date, datetime

from investment_agent.services.calendar_watch import NEWS_URL, watch_calendar

TS = int(datetime(2026, 12, 30, 9, 0).timestamp())


def feed(*titles):
    return json.dumps({"data": {"list": [{"id": 2500000 + i, "title": t, "postedDate": TS} for i, t in enumerate(titles)]}})


def test_nothing_is_fetched_before_december_while_this_years_calendar_is_there(tmp_path):
    config = tmp_path / "config"; config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    calls = []
    out = watch_calendar(tmp_path / "data", config, get=lambda u: calls.append(u) or feed(), send=lambda t: True, today=date(2026, 11, 16))
    assert out == {"status": "ok", "looking_for": [], "sent": 0} and calls == []


def test_a_holiday_notice_for_next_year_is_told_once_with_its_link(tmp_path):
    config, data = tmp_path / "config", tmp_path / "data"; config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    get = lambda u: feed("HOSE: Cập nhật chỉ số VN30 kỳ tháng 12/2026",  # noqa: E731
                         "HOSE: Thông báo lịch nghỉ giao dịch Tết Dương lịch và Tết Nguyên đán năm 2027",
                         "HOSE: Thông báo về việc cập nhật lịch nghỉ giao dịch Tết Dương lịch năm 2026")
    sent = []
    out = watch_calendar(data, config, get=get, send=lambda t: sent.append(t) or True, today=date(2026, 12, 30))
    assert out == {"status": "ok", "looking_for": [2027], "sent": 1} and NEWS_URL.startswith("https://api.hsx.vn/")
    assert sent == ["Lịch giao dịch HOSE 2027: HOSE vừa đăng “HOSE: Thông báo lịch nghỉ giao dịch Tết Dương lịch và Tết Nguyên đán năm 2027” "
                    "(30/12/2026) https://www.hsx.vn/tin-tuc/tin-hose/chi-tiet/2500001\n"
                    "Phần mềm chưa có tệp config/trading-calendar-hose-2027.json: gửi thông báo này để tạo lịch theo đúng số ngày nghỉ HOSE công bố."]
    again = watch_calendar(data, config, get=get, send=lambda t: sent.append(t) or True, today=date(2026, 12, 31))
    assert again["sent"] == 0 and len(sent) == 1


def test_a_note_not_sent_is_tried_again_and_the_watch_stops_once_the_file_exists(tmp_path):
    config, data = tmp_path / "config", tmp_path / "data"; config.mkdir()
    (config / "trading-calendar-hose-2026.json").write_text("{}", encoding="utf-8")
    get = lambda u: feed("HOSE: Lịch nghỉ giao dịch năm 2027")  # noqa: E731
    assert watch_calendar(data, config, get=get, send=lambda t: False, today=date(2026, 12, 20))["sent"] == 0
    assert watch_calendar(data, config, get=get, send=lambda t: True, today=date(2026, 12, 21))["sent"] == 1
    (config / "trading-calendar-hose-2027.json").write_text("{}", encoding="utf-8")
    calls = []
    assert watch_calendar(data, config, get=lambda u: calls.append(u) or feed(), send=lambda t: True, today=date(2026, 12, 22))["looking_for"] == []
    assert calls == []


def test_this_years_missing_calendar_is_looked_for_in_any_month_and_a_failing_feed_is_said(tmp_path):
    config = tmp_path / "config"; config.mkdir()
    def boom(url):
        raise OSError("down")
    out = watch_calendar(tmp_path / "data", config, get=boom, send=lambda t: True, today=date(2027, 3, 2))
    assert out == {"status": "source_error", "looking_for": [2027], "sent": 0}
