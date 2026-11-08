import json
from datetime import datetime, timedelta, timezone

from investment_agent.market.bank_notes import BankNoteStore, note_ratios, parse_car_years, parse_notes, sync_bank_notes


def _quarter(year, q, **over):
    # MBB, Q3/2026 consolidated notes as Vietcap serves them (đồng, floats): loan groups, then deposits by kind.
    row = {"ticker": "MBB", "yearReport": year, "lengthReport": q, "nob39": 1288128443000000.0, "nob40": 1249640585000000.0,
           "nob41": 17013532000000.0, "nob42": 7230947000000.0, "nob43": 4778315000000.0, "nob44": 9465064000000.0,
           "nob65": 993988042000000.0, "nob66": 326388841000000.0, "nob67": 653687908000000.0, "nob68": 0.0,
           "nob69": 11576830000000.0, "nob70": 2334463000000.0}
    row.update(over)
    return row


def _text(*quarters, years=()):
    return json.dumps({"status": 200, "successful": True, "data": {"years": list(years), "quarters": list(quarters)}})


def test_quarters_are_kept_by_quarter_end_in_whole_dong_and_annual_rows_left_out():
    out = parse_notes(_text(_quarter(2026, 3), _quarter(2018, 1, nob41=None), years=[_quarter(2025, 5)]), symbol="MBB")
    assert sorted(out) == ["2018-03-31", "2026-09-30"]
    assert out["2026-09-30"]["group2"] == "17013532000000" and out["2026-09-30"]["margin"] == "11576830000000"
    assert "group2" not in out["2018-03-31"]  # missing stays missing, never zero


def test_group2_share_and_casa_only_where_the_parts_add_up_to_the_printed_totals():
    q = parse_notes(_text(_quarter(2026, 3)), symbol="MBB")["2026-09-30"]
    ratios, problems = note_ratios(q)
    assert ratios == {"group2_ratio": "0.0132", "casa": "0.3400"}  # 17.013.532 / 1.288.128.443; (326.388.841 + 11.576.830) / 993.988.042
    assert problems == []
    off = parse_notes(_text(_quarter(2026, 3, nob43=4773315000000.0, nob69=11578830000000.0)), symbol="MBB")["2026-09-30"]
    ratios, problems = note_ratios(off)
    assert ratios == {} and len(problems) == 2
    assert "1.288.123.443" in problems[0] and "1.288.128.443" in problems[0]  # in triệu đồng, as the report prints them


def _stats(*rows):
    # Vietcap's statistics-financial: one row per quarter (car 0.0 there, meaning not given) and per year (quarter 5).
    return json.dumps({"status": 200, "successful": True, "data": [{"year": y, "quarter": q, "car": c} for y, q, c in rows]})


def test_year_end_car_is_taken_from_the_yearly_rows_only_and_a_zero_is_no_figure():
    text = _stats((2024, 5, 0.154), (2025, 5, 0.1461), (2025, 4, 0.0), (2026, 2, 0.0), (2023, 5, 0.0), (2025, 3, 0.1502))
    assert parse_car_years(text) == {"2024": "0.154", "2025": "0.1461"}


def _fake(calls, failing=()):
    def get(url):
        calls.append(url)
        symbol = url.split("/company/")[1].split("/")[0]
        if symbol in failing:
            raise RuntimeError("418")
        return _text(_quarter(2026, 3, ticker=symbol)) if "section=NOTE" in url else _stats((2025, 5, 0.1461))
    return get


def _who(url):
    return url.split("/company/")[1].split("/")[0] + (":note" if "section=NOTE" in url else ":stats")


def test_sync_reads_only_watched_banks_waits_between_calls_retries_once_and_skips_fresh_records(tmp_path):
    store = BankNoteStore(tmp_path / "bank-notes")
    now = datetime(2026, 11, 8, 13, tzinfo=timezone.utc)
    store.save({"symbol": "ACB", "fetched_at": (now - timedelta(days=2)).isoformat(), "source": "vietcap:iq", "quarters": {}, "car_years": {}})
    calls, waits = [], []
    results = sync_bank_notes(store, {"ACB": "Ngân hàng", "MBB": "Ngân hàng", "VCB": "Ngân hàng", "FPT": "Công nghệ Thông tin"},
                              get=_fake(calls, failing={"VCB"}), sleep=waits.append, now=now)
    assert results == {"ACB": "fresh", "MBB": "ok", "VCB": "error:RuntimeError"}
    # 10 s between calls, as robots.txt asks; a refusal is tried once more after 30 s.
    assert [_who(u) for u in calls] == ["MBB:note", "MBB:stats", "VCB:note", "VCB:note"] and waits == [10, 10, 30]
    record = store.read("MBB")
    assert record["source"] == "vietcap:iq" and record["quarters"]["2026-09-30"]["deposits"] == "993988042000000"
    assert record["car_years"] == {"2025": "0.1461"}
    assert sync_bank_notes(store, {"ACB": "Ngân hàng"}, get=_fake(calls), sleep=waits.append, now=now, force=True) == {"ACB": "ok"}


def test_a_refused_car_call_keeps_the_notes_and_the_earlier_car_and_comes_back_next_run(tmp_path):
    store = BankNoteStore(tmp_path / "bank-notes")
    now = datetime(2026, 11, 8, 13, tzinfo=timezone.utc)
    calls, waits = [], []

    def get(url):
        calls.append(url)
        if "section=NOTE" not in url:
            raise RuntimeError("418")
        return _text(_quarter(2026, 3))
    assert sync_bank_notes(store, {"MBB": "Ngân hàng"}, get=get, sleep=waits.append, now=now) == {"MBB": "error:car:RuntimeError"}
    record = store.read("MBB")
    assert "2026-09-30" in record["quarters"] and "car_years" not in record  # no CAR yet: due again on the next run
    calls.clear()
    assert sync_bank_notes(store, {"MBB": "Ngân hàng"}, get=_fake(calls), sleep=waits.append, now=now) == {"MBB": "ok"}
    assert store.read("MBB")["car_years"] == {"2025": "0.1461"}


def test_cli_bank_notes_sync_reads_the_watchlists_banks_and_reports_each(tmp_path, capsys):
    from investment_agent.cli import bank_notes_sync
    (tmp_path / "market-symbols.txt").write_text("MBB\nFPT\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"MBB": "Ngân hàng", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    assert bank_notes_sync(tmp_path, get=_fake([]), sleep=lambda s: None) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok", "results": {"MBB": "ok"}}
    assert BankNoteStore(tmp_path / "bank-notes").read("MBB")["quarters"]["2026-09-30"]["group2"] == "17013532000000"
