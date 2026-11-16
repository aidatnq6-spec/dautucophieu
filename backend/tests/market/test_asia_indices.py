import json
from datetime import datetime
from zoneinfo import ZoneInfo

from investment_agent.market.asia_indices import FRED_NIKKEI, URL, asia_line, read_asia

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def board(nikkei="61142.35", kospi="5290.53"):
    rows = [{"code": "NIKKEI225", "price": float(nikkei), "changePct": 0.5310644505302259, "lastUpdated": "2026-11-16 23:59"},
            {"code": "KOSPI", "price": float(kospi), "changePct": -0.977028597739358, "lastUpdated": "2026-11-16 23:59"},
            {"code": "SHANGHAI", "price": 3634.353, "changePct": -0.5874726122385341, "lastUpdated": "2026-11-16 23:59"},
            {"code": "HANGSENG", "price": 23637.6, "changePct": -1.5450745671854402, "lastUpdated": "2026-11-16 23:59"}]
    return json.dumps({"data": rows})


FRED = "observation_date,NIKKEI225\n2026-11-12,60819.36\n2026-11-13,61142.35\n"


def getter(**kw):
    def get(url):
        if url == URL:
            return board(**kw)
        if url.startswith(FRED_NIKKEI):
            return FRED
        raise OSError(url)
    return get


def test_each_index_is_read_with_its_change_and_when_it_was_read_and_nikkei_is_dated_by_fred(tmp_path):
    out = read_asia(tmp_path, get=getter(), now=datetime(2026, 11, 16, 15, 32, tzinfo=VN))
    assert out["status"] == "ok" and out["read_at"] == "2026-11-16T15:32:00+07:00"
    rows = {r["code"]: r for r in out["rows"]}
    assert [r["code"] for r in out["rows"]] == ["NIKKEI225", "KOSPI", "SHANGHAI", "HANGSENG"]
    assert rows["KOSPI"] == {"code": "KOSPI", "name": "KOSPI", "price": "5290.53", "change_pct": "-0.0098", "unchanged_since": None, "fred_date": None}
    assert rows["NIKKEI225"]["fred_date"] == "2026-11-13"  # the same close as FRED's 13/11: an earlier session than the day it was read
    assert asia_line(out) == ("Châu Á (VNDirect, đọc 15:32 16/11): Nikkei 225 +0,53% (phiên 13/11 theo FRED) · KOSPI −0,98% · "
                              "Thượng Hải −0,59% · Hang Seng −1,55%")


def test_a_price_unchanged_since_an_earlier_day_is_said_not_new(tmp_path):
    read_asia(tmp_path, get=getter(), now=datetime(2026, 11, 16, 15, 32, tzinfo=VN))
    again = read_asia(tmp_path, get=getter(nikkei="61500"), now=datetime(2026, 11, 17, 15, 32, tzinfo=VN))
    rows = {r["code"]: r for r in again["rows"]}
    assert rows["KOSPI"]["unchanged_since"] == "2026-11-16" and rows["NIKKEI225"]["unchanged_since"] is None
    assert "KOSPI −0,98% (chưa có phiên mới từ 16/11)" in asia_line(again)
    same_day = read_asia(tmp_path, get=getter(nikkei="61500"), now=datetime(2026, 11, 17, 20, 0, tzinfo=VN))
    assert {r["code"]: r for r in same_day["rows"]}["NIKKEI225"]["unchanged_since"] is None  # first seen today: not stale


def test_a_failing_source_is_said(tmp_path):
    def down(url):
        raise OSError("down")
    out = read_asia(tmp_path, get=down, now=datetime(2026, 11, 16, 15, 32, tzinfo=VN))
    assert out == {"status": "missing", "reason": "Không đọc được chỉ số châu Á từ VNDirect"}
    assert asia_line(out) is None
