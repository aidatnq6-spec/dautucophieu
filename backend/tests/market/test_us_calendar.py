import json
from datetime import date, datetime

from investment_agent.market.us_calendar import (
    BLS_CPI, fed_month_url, parse_bls_cpi, parse_fed_month, refresh_us_calendar, remind_us_calendar, upcoming,
)

FED_DEC = """<div class="row cal-nojs__rowTitle"><h4 class="col-md-12">FOMC Meetings </h4></div>
<div class="row"><div class="col-xs-2"><h6>Time:</h6></div><div class="col-xs-offset-7 col-xs-3"><h6>Release Date(s):</h6></div></div>
<div class="row"><div class="panel panel-unstyled col-xs-12"><div class="panel-body"><div class="row">
 <div class="col-xs-2"><p>2:00 p.m.</p></div>
 <div class="col-xs-7"><p>FOMC Minutes</p><p><p>Meeting of December 8-9</p></p></div>
 <div class="col-xs-3"><p>30</p></div></div></div></div></div>
<div class="row"><div class="panel panel-unstyled col-xs-12"><div class="panel-body"><div class="row">
 <div class="col-xs-2"><p>2:30 p.m.</p></div>
 <div class="col-xs-7"><p><a href="https://www.federalreserve.gov/live-broadcast.htm">FOMC Press Conference</a>  </p><p></p></div>
 <div class="col-xs-3"><p>9</p></div></div></div></div></div>
<div class="row"><div class="panel border panel-unstyled col-xs-12"><div class="panel-body"><div class="row">
 <div class="col-xs-2"><p>2:00 p.m.</p></div>
 <div class="col-xs-7"><p>FOMC Meeting</p><p><p>Two-day meeting, December&nbsp;8 - 9</p>
<p>Press Conference</p></p></div>
 <div class="col-xs-3"><p>9</p></div></div></div></div></div>
<div class="row cal-nojs__rowTitle"><h4 class="col-md-12">Statistical Releases</h4></div>
<div class="col-xs-2"><p>2:00 p.m.</p></div><div class="col-xs-7"><p>Senior Loan Officer Survey</p></div><div class="col-xs-3"><p>7</p></div>"""
FED_NOV = FED_DEC.replace("Meeting of December 8-9", "Meeting of October 27-28").replace("<p>30</p>", "<p>18</p>") \
    .replace("FOMC Meeting</p>", "Not a meeting</p>")
BLS = """<table class="release-list"><thead><tr><th>Reference Month</th><th>Release Date</th><th>Release Time</th></tr></thead><tbody>
<tr class="release-list-even-row"><td>October 2026</td><td>Nov. 10, 2026</td><td>08:30 AM</td></tr>
<tr class="release-list-odd-row"><td>November 2026</td><td>Dec. 10, 2026</td><td>08:30 AM</td></tr>
<tr class="release-list-even-row"><td>June 2027</td><td>Jul. 14, 2027</td><td>08:30 AM</td></tr></tbody></table>"""


def test_the_fed_month_page_gives_the_decision_and_the_minutes_in_eastern_time():
    got = parse_fed_month(FED_DEC, 2026, 12)
    assert got == [{"kind": "minutes", "et": "2026-12-30T14:00:00-05:00", "detail": "Meeting of December 8-9"},
                   {"kind": "fomc", "et": "2026-12-09T14:00:00-05:00", "detail": "Two-day meeting, December 8 - 9"}]
    assert fed_month_url(2026, 12) == "https://www.federalreserve.gov/newsevents/2026-december.htm"


def test_the_bls_table_gives_each_cpi_release():
    got = parse_bls_cpi(BLS)
    assert got[0] == {"kind": "cpi", "et": "2026-11-10T08:30:00-05:00", "detail": "October 2026"}
    assert got[2]["et"] == "2027-07-14T08:30:00-04:00"  # summer time in New York


def pages(url):
    if url == BLS_CPI:
        return BLS
    if url.endswith("2026-november.htm"):
        return FED_NOV
    if url.endswith("2026-december.htm"):
        return FED_DEC
    raise OSError("down")


def test_the_calendar_is_kept_with_vietnam_times_and_a_failing_source_keeps_what_it_had(tmp_path):
    out = refresh_us_calendar(tmp_path, get=pages, today=date(2026, 11, 16))
    assert out["status"] == "ok" and out["errors"] == ["https://www.federalreserve.gov/newsevents/2027-january.htm"]
    rows = upcoming(tmp_path, today=date(2026, 11, 16), days=30)
    assert [(r["on"], r["at"], r["text"]) for r in rows] == [
        ("2026-11-19", "02:00", "Fed công bố biên bản họp FOMC (cuộc họp 27–28/10)"),
        ("2026-12-10", "02:00", "Fed công bố quyết định lãi suất (họp 8–9/12)"),
        ("2026-12-10", "20:30", "Mỹ công bố CPI tháng 11/2026")]
    assert rows[0]["source"] == "https://www.federalreserve.gov/newsevents/2026-november.htm"
    def down(url):
        raise OSError("down")
    again = refresh_us_calendar(tmp_path, get=down, today=date(2026, 11, 17))
    assert again["status"] == "error" and len(upcoming(tmp_path, today=date(2026, 11, 16), days=30)) == 3


def test_each_event_is_reminded_once_the_day_before_or_on_the_day(tmp_path):
    refresh_us_calendar(tmp_path, get=pages, today=date(2026, 11, 16))
    sent = []
    out = remind_us_calendar(tmp_path, send=lambda t: sent.append(t) or True, today=date(2026, 11, 18))
    assert out == {"sent": 1} and sent == ["Lịch vĩ mô Mỹ: ngày mai 19/11 lúc 02:00 (giờ Việt Nam), Fed công bố biên bản họp FOMC (cuộc họp 27–28/10). "
                                           "Nguồn: federalreserve.gov"]
    assert remind_us_calendar(tmp_path, send=lambda t: sent.append(t) or True, today=date(2026, 11, 19)) == {"sent": 0}
    assert remind_us_calendar(tmp_path, send=lambda t: False, today=date(2026, 12, 9)) == {"sent": 0}
    later = remind_us_calendar(tmp_path, send=lambda t: sent.append(t) or True, today=date(2026, 12, 10))  # not sent the day before: on the day
    assert later == {"sent": 2} and sent[-2].startswith("Lịch vĩ mô Mỹ: hôm nay 10/12 lúc 02:00")
    assert json.loads((tmp_path / "alerts" / "us-calendar.json").read_text(encoding="utf-8"))["told"]


def test_a_later_fed_month_page_not_yet_posted_is_not_an_error_but_this_month_and_bls_still_are(tmp_path):
    from investment_agent.market.us_calendar import NotPublished
    jan = "https://www.federalreserve.gov/newsevents/2027-january.htm"
    def posted_later(url):
        if url == jan:
            raise NotPublished(url)
        return pages(url)
    out = refresh_us_calendar(tmp_path, get=posted_later, today=date(2026, 11, 16))
    assert out == {"status": "ok", "events": 6, "errors": [], "not_published": [jan]}
    saved = json.loads((tmp_path / "macro" / "us-calendar.json").read_text(encoding="utf-8"))
    assert saved["errors"] == [] and saved["not_published"] == [jan]
    def none_posted(url):
        raise NotPublished(url)
    again = refresh_us_calendar(tmp_path, get=none_posted, today=date(2026, 11, 17))
    assert again["errors"] == ["https://www.federalreserve.gov/newsevents/2026-november.htm", BLS_CPI]
    assert again["not_published"] == ["https://www.federalreserve.gov/newsevents/2026-december.htm", jan]


def test_the_default_reader_turns_a_404_into_not_published(monkeypatch):
    import httpx
    import pytest
    from investment_agent.market import us_calendar
    request = httpx.Request("GET", "https://www.federalreserve.gov/newsevents/2027-january.htm")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(404, request=request))
    with pytest.raises(us_calendar.NotPublished):
        us_calendar.default_get(str(request.url))
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(503, request=request))
    with pytest.raises(httpx.HTTPStatusError):
        us_calendar.default_get(str(request.url))
