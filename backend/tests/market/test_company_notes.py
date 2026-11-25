"""Thuyết minh tự động từ Vietcap (spec 2026-11-25-thuyet-minh-tu-dong-design.md): the notes of non-financial companies, 10 s apart, weekly."""

import json
from datetime import datetime, timedelta, timezone

from investment_agent.market.company_notes import CompanyNoteStore, parse_company_notes, sync_company_notes

B = 10**9
NOW = datetime(2026, 11, 25, 13, tzinfo=timezone.utc)


def body(symbol="HPG", **more):
    """HPG 2021 as Vietcap gives it: amounts in đồng, floats."""
    year = {"ticker": symbol, "yearReport": 2021, "lengthReport": 5, "noc66": 37547.0 * B, "noc67": 6200.6 * B, "noc94": 13464.9 * B, "noc96": 0.0,
            "noc123": 1194.4 * B, "noc155": 504.2 * B, "noc128": 46.6 * B, "noc132": 2525.8 * B, "noc36": 82616.6 * B, "noc37": 9767.3 * B, "noc38": -1357.8 * B,
            "noc999": 1.0, "noc125": None, **more}
    quarter = {"ticker": symbol, "yearReport": 2026, "lengthReport": 3, "noc66": 1.0 * B}
    return json.dumps({"data": {"years": [year], "quarters": [quarter]}})


def test_the_notes_kept_are_named_in_whole_dong_and_missing_figures_are_left_out():
    out = parse_company_notes(body(), symbol="HPG")
    y = out["years"]["2021"]
    assert y["st_loans_contract"] == str(37547 * B) and y["lt_due"] == "6200600000000" and y["lt_bank"] == "13464900000000" and y["bonds"] == "0"
    assert y["fin_interest"] == "1194400000000" and y["fin_disposals"] == "504200000000" and y["fin_fx_unrealised"] == "46600000000"
    assert y["exp_interest"] == "2525800000000" and y["ppe_cost_open"] == "82616600000000" and y["ppe_cost_add"] == "9767300000000"
    assert y["ppe_cost_out"] == "-1357800000000"
    assert "fin_dividends" not in y  # None from the source: not a zero
    assert not any(k.startswith("noc") for k in y)  # only the named lines
    assert out["quarters"] == {"2026-Q3": {"st_loans_contract": str(B)}}
    assert parse_company_notes(body(symbol="FPT"), symbol="HPG")["years"] == {}  # another ticker's rows


def test_the_sync_waits_ten_seconds_before_every_call_takes_the_oldest_fifteen_and_stops_when_refused(tmp_path):
    store = CompanyNoteStore(tmp_path)
    for s in ("AAA", "BBB"):
        store.save({"symbol": s, "fetched_at": (NOW - timedelta(days=2)).isoformat(), "source": "vietcap:iq", "years": {}, "quarters": {}})
    sleeps, calls = [], []

    def get(url):
        calls.append(url)
        if "CCC" in url:
            raise RuntimeError("418")
        return body(symbol=url.split("/company/")[1].split("/")[0])
    sectors = {"AAA": "Công nghệ", "BBB": "Bán lẻ", "CCC": "Thép", "DDD": "Thép", "VCB": "Ngân hàng"}
    results = sync_company_notes(store, sectors, get=get, sleep=sleeps.append, now=NOW)
    assert results == {"AAA": "fresh", "BBB": "fresh", "CCC": "error:RuntimeError", "DDD": "skipped"}  # banks are not asked
    assert sleeps == [10] and len(calls) == 1  # waits even before the first call (Vietcap was just called by bank-notes-sync)
    later = sync_company_notes(store, {"DDD": "Thép"}, get=get, sleep=sleeps.append, now=NOW)
    assert later == {"DDD": "ok"} and store.read("DDD")["years"]["2021"]["lt_due"] == "6200600000000"
    many = {f"T{i:02d}": "Thép" for i in range(20)}
    done = sync_company_notes(CompanyNoteStore(tmp_path / "m"), many, get=get, sleep=lambda s: None, now=NOW)
    assert sum(1 for v in done.values() if v == "ok") == 15 and sum(1 for v in done.values() if v == "later") == 5  # at most 15 a run
