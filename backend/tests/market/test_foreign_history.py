import json
from datetime import date, datetime, timedelta, timezone

from investment_agent.market.foreign_history import ForeignStore, parse_foreign_session, sync_foreign

EVENING = datetime(2026, 11, 27, 13, 30, tzinfo=timezone.utc)  # 20:30 in Vietnam


def row(code, day, buy_val, sell_val, kind="STOCK", buy_vol=100, sell_vol=40):
    return {"code": code, "type": kind, "floor": "HOSE", "tradingDate": day, "buyVol": float(buy_vol), "sellVol": float(sell_vol),
            "buyVal": float(buy_val), "sellVal": float(sell_val), "netVal": float(buy_val - sell_val)}


def page(day, stocks):
    rows = [row(c, day, b, s) for c, b, s in stocks]
    rows += [row("VNINDEX", day, 9e9, 1e9, kind="INDEX"), row("E1VFVN30", day, 5e9, 0, kind="ETF"), row("CFPT2601", day, 1, 1, kind="CW")]
    return json.dumps({"data": rows})


def test_a_session_keeps_hose_stocks_apart_from_etfs_warrants_and_indices():
    rec = parse_foreign_session(page("2026-11-26", [("FPT", 3e9, 1e9), ("HPG", 0, 2e9)]), date(2026, 11, 26))
    assert rec["date"] == "2026-11-26" and set(rec["stocks"]) == {"FPT", "HPG"}
    assert rec["stocks"]["FPT"] == {"buy_volume": "100", "sell_volume": "40", "buy_value": "3000000000", "sell_value": "1000000000"}
    assert rec["index"]["buy_value"] == "9000000000"  # VNDirect's VNINDEX row, kept beside: it is not the net the brief shows


def test_a_session_with_only_index_rows_is_missing():
    # VNDirect served 24/11/2026 this way
    only_index = json.dumps({"data": [row("VNINDEX", "2026-11-24", 1, 1, kind="INDEX"), row("VN30", "2026-11-24", 1, 1, kind="INDEX")]})
    assert parse_foreign_session(only_index, date(2026, 11, 24))["thieu"] is True


def test_an_empty_figure_is_never_stored_as_zero():
    rows = json.loads(page("2026-11-26", [("FPT", 3e9, 1e9), ("HPG", 1e9, 0)]))["data"]
    next(r for r in rows if r["code"] == "HPG")["sellVal"] = None
    rec = parse_foreign_session(json.dumps({"data": rows}), date(2026, 11, 26))
    assert set(rec["stocks"]) == {"FPT"} and rec["bo_qua"] == ["HPG"]


def test_sync_asks_newest_first_and_again_for_a_recent_missing_session(tmp_path):
    days = [date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 26), date(2026, 11, 27)]
    store = ForeignStore(tmp_path)
    store.save({"date": "2026-11-24", "thieu": True, "hoi_luc": "x"})
    store.save({**parse_foreign_session(page("2026-11-25", [("FPT", 1, 0)]), date(2026, 11, 25)), "fetched_at": "x"})
    asked = []

    def get(url):
        day = url.split("tradingDate:")[1].split("&")[0]
        asked.append(day)
        return page(day, [("FPT", 2e9, 0)])
    out = sync_foreign(tmp_path, get=get, now=EVENING, sessions=days, sleep=lambda s: None)
    assert asked == ["2026-11-27", "2026-11-26", "2026-11-24"] and out["fetched"] == 3 and out["status"] == "ok"
    assert store.read(date(2026, 11, 24))["stocks"]["FPT"]["buy_value"] == "2000000000"


def test_cli_foreign_sync_prints_what_it_did(tmp_path, capsys):
    from investment_agent.cli import foreign_sync
    code = foreign_sync(tmp_path, limit=1, get=lambda url: page(url.split("tradingDate:")[1].split("&")[0], [("FPT", 1, 0)]),
                        now=EVENING, sleep=lambda s: None)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["fetched"] == 1 and out["due"] > 200
