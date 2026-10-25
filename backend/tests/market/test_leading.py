import json
from datetime import date

import pytest

from investment_agent.market.leading import (
    MacroError, MacroStore, evaluate, fetch_auto, load_indicators, macro_rows, parse_fred_csv, parse_vcb_xml,
)

FRED_CPI = "observation_date,CPIAUCSL\n2025-08-01,322.0\n2025-09-01,324.0\n2026-08-01,333.5\n2026-09-01,336.298\n"
FRED_10Y = "observation_date,DGS10\n2026-10-21,4.91\n2026-10-22,.\n2026-10-23,4.96\n"
VCB = ('<ExrateList><DateTime>10/25/2026 9:30:00 PM</DateTime>'
       '<Exrate CurrencyCode="EUR" Buy="1" Transfer="1" Sell="2" />'
       '<Exrate CurrencyCode="USD" CurrencyName="US DOLLAR" Buy="25,610.00" Transfer="25,640.00" Sell="26,020.00" /></ExrateList>')


def test_indicators_config_lists_auto_and_manual_rows():
    ind = load_indicators()
    assert len(ind) == 16 and {i["id"] for i in ind if i["source"]["kind"] != "manual"} == {
        "dollar_broad", "wti", "us_cpi_yoy", "usd_vnd_vcb", "fed_effr", "us10y"}


def test_fred_csv_skips_missing_values_and_cpi_becomes_year_on_year():
    assert parse_fred_csv(FRED_10Y) == [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")]
    assert parse_fred_csv(FRED_CPI, transform="yoy") == [(date(2026, 8, 1), "3.57"), (date(2026, 9, 1), "3.80")]


def test_vcb_xml_gives_the_usd_sell_rate_and_publication_date():
    assert parse_vcb_xml(VCB, currency="USD", field="Sell") == (date(2026, 10, 25), "26020")
    with pytest.raises(MacroError):
        parse_vcb_xml("<html>maintenance</html>", currency="USD", field="Sell")


@pytest.mark.parametrize("rule, values, expected", [
    ("up", ["101.2", "101.8"], ("Tăng", "Xấu")), ("up", ["101.8", "101.2"], ("Giảm", "Tốt")), ("up", ["5", "5"], ("Đi ngang", "Trung tính")),
    ("down", ["19000000", "19974984"], ("Tăng", "Tốt")), ("sign", ["-100", "-535"], ("Giảm", "Xấu")), ("sign", ["-535", "120"], ("Tăng", "Tốt")),
    ("pmi", ["55.1", "55.9"], ("Tăng", "Tốt")), ("pmi", ["52.4", "51.9"], ("Giảm", "Xấu")), ("pmi", ["48.0", "49.0"], ("Tăng", "Xấu")),
    ("up", ["4.96"], (None, None)),
])
def test_trend_and_assessment_follow_the_owner_rules(rule, values, expected):
    assert evaluate(rule, values) == expected


def test_store_upserts_by_date_and_keeps_history(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("us10y", [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")], entry="auto")
    store.upsert("us10y", [(date(2026, 10, 23), "4.97")], entry="auto")  # same date: the newer value replaces it
    assert [(o["date"], o["value"]) for o in store.read("us10y")] == [("2026-10-21", "4.91"), ("2026-10-23", "4.97")]
    assert json.loads((tmp_path / "macro" / "us10y.json").read_text(encoding="utf-8"))["indicator"] == "us10y"


def test_fetch_auto_uses_each_source_and_reports_failures_per_indicator(tmp_path):
    pages = {"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10": FRED_10Y,
             "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx": VCB}

    def get(url):
        if url not in pages:
            raise OSError("offline")
        return pages[url]
    store = MacroStore(tmp_path)
    result = fetch_auto(load_indicators(), store, get=get)
    assert result["us10y"] == "ok" and result["usd_vnd_vcb"] == "ok" and result["wti"] == "error:OSError"
    assert store.read("usd_vnd_vcb")[-1]["value"] == "26020"


def test_rows_show_value_trend_assessment_age_and_entry_kind(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("us10y", [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")], entry="auto")
    store.upsert("vn_pmi", [(date(2026, 9, 1), "52.4"), (date(2026, 10, 1), "51.9")], entry="manual", source_url="https://example.vn/pmi")
    rows = {r["id"]: r for r in macro_rows(load_indicators(), store, today=date(2026, 10, 25))}
    assert {k: rows["us10y"][k] for k in ("value", "date", "previous", "trend", "assessment", "stale", "auto")} == {
        "value": "4.96", "date": "2026-10-23", "previous": "4.91", "trend": "Tăng", "assessment": "Xấu", "stale": False, "auto": True}
    assert rows["vn_pmi"]["trend"] == "Giảm" and rows["vn_pmi"]["assessment"] == "Xấu" and rows["vn_pmi"]["source_url"] == "https://example.vn/pmi"
    assert rows["m2_vn"]["value"] is None and rows["m2_vn"]["auto"] is False
    old = {r["id"]: r for r in macro_rows(load_indicators(), store, today=date(2026, 11, 20))}
    assert old["us10y"]["stale"] is True


def test_cli_macro_sync_writes_automatic_indicators(tmp_path, capsys):
    from investment_agent.cli import macro_sync
    assert macro_sync(tmp_path, get=lambda url: FRED_10Y if "DGS10" in url else (_ for _ in ()).throw(OSError("offline"))) == 1
    assert MacroStore(tmp_path).read("us10y")[-1]["value"] == "4.96"
    assert '"us10y": "ok"' in capsys.readouterr().out


def test_backup_includes_macro_observations(tmp_path):
    from datetime import datetime, timezone
    from investment_agent.operations.backup import create_backup
    MacroStore(tmp_path / "data").upsert("vn_pmi", [(date(2026, 10, 1), "51.9")], entry="manual")
    manifest = create_backup(tmp_path / "data", tmp_path / "backups", personal_export=None, now=datetime(2026, 10, 25, tzinfo=timezone.utc), kind="manual")
    assert "data/macro/vn_pmi.json" in [f["path"] for f in manifest.files]
