import json
from datetime import date, datetime, timedelta, timezone

from investment_agent.market.proprietary_history import ProprietaryStore, parse_session, sync_proprietary

EVENING = datetime(2026, 11, 27, 13, 30, tzinfo=timezone.utc)  # 20:30 in Vietnam


def row(code, day, buy_val, sell_val, buy_vol=100, sell_vol=40, kind="STOCK"):
    return {"code": code, "type": kind, "floor": "HOSE", "date": day, "buyingVol": float(buy_vol), "sellingVol": float(sell_vol),
            "buyingVal": float(buy_val), "sellingVal": float(sell_val)}


def page(day, stocks, index=True):
    rows = [row(c, day, b, s) for c, b, s in stocks] + [row("CSSI2601", day, 5, 5, kind="CW")]
    if index:
        rows.append(row("VNINDEX", day, sum(b for _, b, _ in stocks), sum(s for _, _, s in stocks), 200, 80, kind="INDEX"))
        rows.append(row("VN30", day, 1, 1, kind="INDEX"))
    return json.dumps({"data": rows})


def test_a_session_keeps_the_vnindex_row_and_hose_stocks_only_and_whether_they_add_up():
    rec = parse_session(page("2026-11-23", [("FPT", 3e9, 1e9), ("SSI", 1e9, 2e9)]), date(2026, 11, 23))
    assert rec["date"] == "2026-11-23" and rec["khop"] is True and set(rec["stocks"]) == {"FPT", "SSI"}
    assert rec["index"] == {"buy_volume": "200", "sell_volume": "80", "buy_value": "4000000000", "sell_value": "3000000000"}
    assert rec["stocks"]["FPT"] == {"buy_volume": "100", "sell_volume": "40", "buy_value": "3000000000", "sell_value": "1000000000"}
    off = json.loads(page("2026-11-23", [("FPT", 3e9, 1e9)]))
    off["data"].append(row("HPG", "2026-11-23", 1e9, 0))  # a ticker beyond the VNINDEX total
    assert parse_session(json.dumps(off), date(2026, 11, 23))["khop"] is False


def test_a_session_vndirect_has_not_posted_is_missing():
    rec = parse_session(json.dumps({"data": []}), date(2026, 11, 26))
    assert rec["date"] == "2026-11-26" and rec["thieu"] is True and "stocks" not in rec


def _sessions(last: date, n: int) -> list[date]:
    out, day = [], last
    while len(out) < n:
        if day.weekday() < 5:
            out.append(day)
        day -= timedelta(days=1)
    return sorted(out)


def test_sync_fetches_newest_first_skips_stored_ones_and_stops_at_the_limit(tmp_path):
    sessions = _sessions(date(2026, 11, 27), 5)
    store = ProprietaryStore(tmp_path)
    store.save(parse_session(page("2026-11-26", [("FPT", 1, 0)]), date(2026, 11, 26)))
    asked = []

    def get(url):
        day = url.split("date:")[1].split("&")[0]
        asked.append(day)
        return page(day, [("FPT", 1e9, 0)])
    out = sync_proprietary(tmp_path, get=get, now=EVENING, sessions=sessions, limit=2, sleep=lambda s: None)
    assert asked == ["2026-11-27", "2026-11-25"] and out == {"status": "ok", "due": 4, "fetched": 2, "missing": 0, "failed": {}}


def test_a_missing_recent_session_is_asked_again_and_an_older_one_only_once(tmp_path):
    sessions = _sessions(date(2026, 11, 27), 25)
    store = ProprietaryStore(tmp_path)
    for day in sessions:
        store.save(parse_session(page(day.isoformat(), [("FPT", 1, 0)]), day))
    recent, old = sessions[-3], sessions[0]  # recent: inside the last 20 sessions; old: the 25th back
    for day in (recent, old):
        store.save(parse_session(json.dumps({"data": []}), day))
    asked = []

    def get(url):
        day = url.split("date:")[1].split("&")[0]
        asked.append(day)
        return page(day, [("FPT", 2e9, 0)])
    out = sync_proprietary(tmp_path, get=get, now=EVENING, sessions=sessions, sleep=lambda s: None)
    assert asked == [recent.isoformat()] and out["fetched"] == 1  # VNDirect posted it late: the missing file is replaced
    assert store.read(recent)["khop"] is True and store.read(old)["thieu"] is True


def test_a_never_asked_old_session_is_asked_once_and_kept_as_missing(tmp_path):
    sessions = _sessions(date(2026, 11, 27), 25)
    out = sync_proprietary(tmp_path, get=lambda url: json.dumps({"data": []}), now=EVENING, sessions=sessions, sleep=lambda s: None)
    assert out["missing"] == 25 and ProprietaryStore(tmp_path).read(sessions[0])["thieu"] is True
    again = sync_proprietary(tmp_path, get=lambda url: json.dumps({"data": []}), now=EVENING, sessions=sessions, sleep=lambda s: None)
    assert again["due"] == 20  # only the last 20 are asked again


def test_sync_during_the_session_does_not_ask_for_today(tmp_path):
    asked = []
    sync_proprietary(tmp_path, get=lambda url: asked.append(url) or json.dumps({"data": []}),
                     now=datetime(2026, 11, 27, 3, 0, tzinfo=timezone.utc), sessions=_sessions(date(2026, 11, 27), 2), sleep=lambda s: None)
    assert len(asked) == 1 and "2026-11-26" in asked[0]


def test_a_failing_session_is_reported_and_files_past_a_year_are_removed(tmp_path):
    store = ProprietaryStore(tmp_path)
    store.save(parse_session(page("2025-10-01", [("FPT", 1, 0)]), date(2025, 10, 1)))

    def get(url):
        if "2026-11-27" in url:
            raise OSError("down")
        return page(url.split("date:")[1].split("&")[0], [("FPT", 1, 0)])
    out = sync_proprietary(tmp_path, get=get, now=EVENING, sessions=_sessions(date(2026, 11, 27), 2), sleep=lambda s: None)
    assert out["status"] == "partial" and out["failed"] == {"2026-11-27": "error:OSError"} and out["fetched"] == 1
    assert store.read(date(2025, 10, 1)) is None and store.days() == ["2026-11-26"]


def test_cli_sync_prints_what_it_did(tmp_path, capsys):
    from investment_agent.cli import proprietary_sync
    code = proprietary_sync(tmp_path, limit=1, get=lambda url: page(url.split("date:")[1].split("&")[0], [("FPT", 1, 0)]),
                            now=EVENING, sleep=lambda s: None)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["fetched"] == 1 and out["due"] > 200  # a year of HOSE sessions
