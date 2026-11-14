import json
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

from investment_agent.market.index_closes import rebuild_index_history
from investment_agent.market.series import SeriesStore

TODAY = date(2026, 11, 14)


def days(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def level(d):  # a made-up level that moves every day
    return round(500 + (d - date(2000, 1, 1)).days * 0.37, 2)


def fake_get(vnd_from=date(2017, 8, 24), cafef_shift=0.0, cafef_from=date(2004, 1, 5)):
    calls = []

    def get(url):
        calls.append(url)
        q = parse_qs(urlparse(url).query)
        if "vndirect" in url:
            return json.dumps({"data": [{"code": "VNINDEX", "date": d.isoformat(), "close": level(d)} for d in days(vnd_from, TODAY)][::-1]})
        m, dd, y = q["StartDate"][0].split("/"); start = date(int(y), int(m), int(dd))
        m, dd, y = q["EndDate"][0].split("/"); end = date(int(y), int(m), int(dd))
        rows = [{"Ngay": d.strftime("%d/%m/%Y"), "GiaDongCua": level(d) + cafef_shift} for d in days(max(start, cafef_from), end)][::-1]
        page = int(q["PageIndex"][0])
        return json.dumps({"Data": {"TotalCount": len(rows), "Data": rows[(page - 1) * 30: page * 30]}, "Success": True})
    return get, calls


def seed(tmp_path):
    store = SeriesStore(tmp_path)
    old = [(d, format(round(level(d) / 1000, 2), "f")) for d in days(date(2004, 1, 5), date(2022, 10, 18))]  # thousand points
    old += [(d, str(level(d))) for d in days(date(2022, 10, 19), TODAY)]
    from datetime import datetime
    store.upsert("VNINDEX-1d", [(datetime.combine(d, datetime.min.time()), v) for d, v in old])
    return store


def test_the_series_is_rebuilt_in_points_from_vndirect_and_cafef_before_it(tmp_path):
    store = seed(tmp_path)
    get, calls = fake_get()
    out = rebuild_index_history(store, "VNINDEX", get=get, today=TODAY, sleep=lambda s: None)
    points = dict(store.points("VNINDEX-1d"))
    assert out["status"] == "ok" and out["vndirect_from"] == "2017-08-24" and out["cafef_days"] > 3000
    assert points["2021-11-12"] == str(level(date(2021, 11, 12))) and points["2004-01-05"] == str(level(date(2004, 1, 5)))
    assert min(float(v) for v in points.values()) >= 100
    assert out["coarse_mismatch"] == 0  # every old thousand-point close matches the new one rounded
    assert all("cafef.vn" in u or "vndirect" in u for u in calls)


def test_sources_that_disagree_where_they_overlap_change_nothing(tmp_path):
    store = seed(tmp_path)
    before = store.points("VNINDEX-1d")
    get, _ = fake_get(cafef_shift=5.0)
    out = rebuild_index_history(store, "VNINDEX", get=get, today=TODAY, sleep=lambda s: None)
    assert out == {"status": "error", "reason": "sources_disagree", "index": "VNINDEX"} and store.points("VNINDEX-1d") == before


def test_a_close_below_100_points_changes_nothing(tmp_path):
    store = seed(tmp_path)
    before = store.points("VNINDEX-1d")

    def get(url):
        if "vndirect" in url:
            return json.dumps({"data": [{"code": "VNINDEX", "date": "2026-11-13", "close": 1.73}, {"code": "VNINDEX", "date": "2026-11-12", "close": 1.72}]})
        return json.dumps({"Data": {"TotalCount": 0, "Data": []}})
    out = rebuild_index_history(store, "VNINDEX", get=get, today=TODAY, sleep=lambda s: None)
    assert out["status"] == "error" and out["reason"] in ("unit", "no_overlap") and store.points("VNINDEX-1d") == before


def test_health_names_an_index_series_stored_in_another_unit(tmp_path):
    from investment_agent.services.system_health import index_unit_problems
    seed(tmp_path / "trend-sources")
    problems = index_unit_problems(tmp_path)
    assert [p["id"] for p in problems] == ["index_units:VNINDEX"] and "nghìn điểm" in problems[0]["detail"]


def test_the_command_backs_up_the_held_files_before_rebuilding(tmp_path):
    from investment_agent.cli import index_closes_cli
    data = tmp_path / "data"
    seed(data / "trend-sources")
    get, _ = fake_get()
    code = index_closes_cli(data, get=get, today=TODAY, sleep=lambda s: None)
    backup = tmp_path / "backups" / "index-closes-2026-11-14" / "VNINDEX-1d.json"
    assert backup.is_file() and json.loads(backup.read_text(encoding="utf-8"))["points"][0][1].startswith("1.04")  # the old thousand-point file, as held
    assert code == 1  # the fake has no VN30, so that one fails and is said to
    assert min(float(v) for _, v in SeriesStore(data / "trend-sources").points("VNINDEX-1d")) >= 100
