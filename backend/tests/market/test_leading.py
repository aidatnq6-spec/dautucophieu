import json
from datetime import date

import pytest

from investment_agent.market.leading import (
    MacroError, MacroStore, evaluate, fetch_auto, load_indicators, macro_rows, parse_fred_csv, parse_stockbiz_series, parse_te_pmi, parse_topi_fx, parse_topi_rate, parse_vcb_xml,
)

FRED_CPI = "observation_date,CPIAUCSL\n2025-08-01,322.0\n2025-09-01,324.0\n2026-08-01,333.5\n2026-09-01,336.298\n"
FRED_10Y = "observation_date,DGS10\n2026-10-21,4.91\n2026-10-22,.\n2026-10-23,4.96\n"
# Shapes of the two Topi pages as served on 2026-10-25 (tags trimmed); values are those pages' figures.
TOPI_FX = ('<html><script>var x = "Tự do 1 2";</script><div>Tự do 26.080đ SBV 26.858đ</div><table><tr><th>Loại vàng</th><th>Mua (USD/VND)</th>'
           '<th>Bán (USD/VND)</th></tr><tr><td>Tự do</td><td>26.000</td><td>26.080</td></tr><tr><td>SBV</td><td>24.396</td><td>26.858</td></tr>'
           '<tr><td>NHTM</td><td>25.610</td><td>26.020</td></tr></table></html>')
TOPI_RATE = ('<html><div>NHTM Nhà nước 5.4% NHTM Khác 5.63%</div><table><tr><th>Kỳ hạn</th><th>NHTM Nhà nước</th><th>NHTM Lớn</th><th>NHTM Khác</th></tr>'
             '<tr><td>1 tháng</td><td>2.22%</td><td>4.03%</td><td>4.16%</td></tr>'
             '<tr><td>12 tháng</td><td>5.4%</td><td>5.81%</td><td>5.63%</td></tr></table></html>')
VCB = ('<ExrateList><DateTime>10/25/2026 9:30:00 PM</DateTime>'
       '<Exrate CurrencyCode="EUR" Buy="1" Transfer="1" Sell="2" />'
       '<Exrate CurrencyCode="USD" CurrencyName="US DOLLAR" Buy="25,610.00" Transfer="25,640.00" Sell="26,020.00" /></ExrateList>')


def test_stockbiz_series_uses_period_dates_and_converts_m2_to_billion_vnd():
    m2 = "Recent readings 7/2026 | 20.456 nghìn tỷ đồng 6/2026 | 20.415 nghìn tỷ đồng Source: State Bank of Vietnam"
    rate = "Recent readings 10/23/2026 | 4.49% 10/22/2026 | 4.48% Source: Hanoi Stock Exchange"
    assert parse_stockbiz_series(m2, monthly=True, scale="1000") == [(date(2026, 6, 30), "20415000"), (date(2026, 7, 31), "20456000")]
    assert parse_stockbiz_series(rate) == [(date(2026, 10, 22), "4.48"), (date(2026, 10, 23), "4.49")]


def test_pmi_aggregator_requires_value_and_named_publication_month():
    assert parse_te_pmi("Vietnam Manufacturing PMI decreased to 51.9 points in September.", year=2026) == [(date(2026, 9, 30), "51.9")]
    with pytest.raises(MacroError):
        parse_te_pmi("Manufacturing PMI data is coming soon", year=2026)


def test_indicators_config_lists_auto_and_manual_rows():
    ind = load_indicators()
    assert len(ind) == 16 and {i["id"] for i in ind if i["source"]["kind"] != "manual"} == {
        "dollar_broad", "wti", "us_cpi_yoy", "usd_vnd_vcb", "fed_effr", "us10y", "usd_vnd_free", "usd_vnd_sbv", "deposit_12m",
        "foreign_net", "vnindex_value", "m2_vn", "vn10y", "vn_interbank_on", "vn_pmi"}  # us_pmi: manual since 26/10/2026 (sources block bots)


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
    assert rows["m2_vn"]["value"] is None and rows["m2_vn"]["auto"] is True
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



def test_topi_pages_give_the_sell_rates_and_the_deposit_rate_by_column():
    assert parse_topi_fx(TOPI_FX, row="Tự do") == "26080" and parse_topi_fx(TOPI_FX, row="SBV") == "26858"
    assert parse_topi_rate(TOPI_RATE, term="12 tháng", column="NHTM Khác") == "5.63"
    assert parse_topi_rate(TOPI_RATE, term="12 tháng", column="NHTM Lớn") == "5.81"
    for bad in ("<html>bảo trì</html>", TOPI_RATE.replace("NHTM Khác</th>", "Khác</th>")):
        with pytest.raises(MacroError):
            parse_topi_rate(bad, term="12 tháng", column="NHTM Khác")
    with pytest.raises(MacroError):
        parse_topi_fx("<html>bảo trì</html>", row="Tự do")


def test_topi_values_are_dated_on_the_fetch_day_and_failures_are_recorded(tmp_path):
    pages = {"https://online.topi.vn/market/ty-gia-usd-vnd": TOPI_FX}

    def get(url):
        if url not in pages:
            raise OSError("offline")
        return pages[url]
    store = MacroStore(tmp_path)
    fetch_auto(load_indicators(), store, get=get, today=date(2026, 10, 25))
    assert store.read("usd_vnd_free")[-1] == {**store.read("usd_vnd_free")[-1], "date": "2026-10-25", "value": "26080", "entry": "auto"}
    rows = {r["id"]: r for r in macro_rows(load_indicators(), store, today=date(2026, 10, 25))}
    assert rows["usd_vnd_free"]["source_error"] is None and rows["deposit_12m"]["source_error"] == "error:OSError"
    assert rows["deposit_12m"]["manual_allowed"] is True and rows["us10y"]["manual_allowed"] is False


# HOSE's foreign-trading report as served for 23/10/2026 (values in million đồng); weekends return no rows.
HOSE_2310 = json.dumps({"data": [
    {"trading_type_name": "Mua", "foreign_trading_value": "1,896,838.66", "market_value": "17,010,236.60", "percent": "11.15 %"},
    {"trading_type_name": "Bán", "foreign_trading_value": "2,374,562.09", "market_value": "", "percent": "13.96 %"},
    {"trading_type_name": "Mua - Bán", "foreign_trading_value": "-477,723.43", "market_value": "", "percent": ""}], "success": True, "message": None})
HOSE_EMPTY = json.dumps({"data": [], "success": True, "message": None})


def test_hose_report_gives_net_foreign_value_and_market_value_in_billions():
    from investment_agent.market.leading import parse_hose_foreign
    assert parse_hose_foreign(HOSE_2310) == {"net": "-477.72343", "market_value": "17010.2366"}
    assert parse_hose_foreign(HOSE_EMPTY) is None
    with pytest.raises(MacroError):
        parse_hose_foreign("<html>Request Rejected</html>")


def test_hose_indicators_collect_the_last_trading_days(tmp_path):
    seen = []

    def get(url):
        seen.append(url)
        if "api.hsx.vn" not in url:
            raise OSError("offline")
        return HOSE_2310 if "fromDate=2026-10-23&toDate=2026-10-23" in url or "fromDate=2026-10-22&toDate=2026-10-22" in url else HOSE_EMPTY
    store = MacroStore(tmp_path)
    result = fetch_auto(load_indicators(), store, get=get, today=date(2026, 10, 25))
    assert result["foreign_net"] == "ok" and result["vnindex_value"] == "ok"
    assert [(o["date"], o["value"]) for o in store.read("foreign_net")] == [("2026-10-22", "-477.72343"), ("2026-10-23", "-477.72343")]
    assert store.read("vnindex_value")[-1]["value"] == "17010.2366"
    assert len([u for u in seen if "api.hsx.vn" in u]) == 7  # one call per day, shared by both indicators


def test_reminders_name_manual_indicators_that_are_missing_or_overdue(tmp_path):
    from investment_agent.market.leading import macro_reminders
    store = MacroStore(tmp_path)
    store.upsert("vn_pmi", [(date(2026, 9, 20), "51.9")], entry="manual")   # 36 days old, monthly → overdue
    store.upsert("us_pmi", [(date(2026, 10, 1), "55.9")], entry="manual")   # 25 days old → fine
    store.upsert("vn10y", [(date(2026, 10, 25), "4.58")], entry="manual")   # fresh weekly value
    store.upsert("us10y", [(date(2026, 9, 1), "4.9")], entry="auto")       # automatic only: never a reminder
    got = macro_reminders(load_indicators(), store, today=date(2026, 10, 26))
    assert "PMI sản xuất Việt Nam đã 36 ngày chưa cập nhật" in got
    assert "Cung tiền M2 Việt Nam (tỷ đồng) chưa có số liệu" in got
    assert not any("PMI sản xuất Mỹ" in r or "10 năm của Việt Nam" in r or "Mỹ" in r and "Lợi suất" in r for r in got)


def test_monthly_and_weekly_update_rhythm_is_configured():
    ages = {i["id"]: i["max_age_days"] for i in load_indicators()}
    assert (ages["us_pmi"], ages["vn_pmi"], ages["m2_vn"], ages["vn10y"], ages["vn_interbank_on"]) == (35, 35, 35, 7, 7)


def news(title, published="2026-10-01T09:30:00+07:00"):
    return {"title": title, "url": "https://cafef.vn/x.chn", "source": "CafeF", "published": published}


def test_vietnam_pmi_is_read_from_news_headlines():
    from investment_agent.market.leading import parse_news_pmi
    items = [news("PMI ngành sản xuất Việt Nam tháng 9 đạt 51,9 điểm, cao nhất 6 tháng"),
             news("PMI tháng 8/2026 của Việt Nam giảm xuống 49,8 điểm", "2026-09-01T09:00:00+07:00"),
             news("PMI sản xuất Mỹ tháng 9 đạt 55,9 điểm"),               # another country
             news("PMI Trung Quốc tháng 9 tăng lên 50,3"),
             news("Chỉ số PMI của Việt Nam tiếp tục tăng"),                # no month or value
             news("PMI Việt Nam tháng 12 đạt 50,1 điểm", "2027-01-02T09:00:00+07:00")]
    assert parse_news_pmi(items) == [(date(2026, 8, 31), "49.8"), (date(2026, 9, 30), "51.9"), (date(2026, 12, 31), "50.1")]


def test_december_pmi_reported_in_january_is_dated_to_the_previous_year():
    from investment_agent.market.leading import parse_news_pmi
    assert parse_news_pmi([news("PMI Việt Nam tháng 12 ở mức 48,5 điểm", "2027-01-03T09:00:00+07:00")]) == [(date(2026, 12, 31), "48.5")]


def test_us_pmi_is_manual_and_vietnam_pmi_comes_from_the_news_feeds(tmp_path):
    rss = ('<rss><item><title>PMI ngành sản xuất Việt Nam tháng 9 đạt 51,9 điểm</title><link>https://cafef.vn/pmi.chn</link>'
           '<pubDate>Wed, 01 Oct 2026 09:30:00 +0700</pubDate></item></rss>')
    seen = []

    def get(url):
        seen.append(url)
        if url.endswith(".rss"):
            return rss
        raise OSError("offline")
    store = MacroStore(tmp_path)
    result = fetch_auto(load_indicators(), store, get=get, today=date(2026, 10, 2))
    assert result["vn_pmi"] == "ok" and store.read("vn_pmi")[-1]["value"] == "51.9" and store.read("vn_pmi")[-1]["date"] == "2026-09-30"
    assert "us_pmi" not in result and not any("tradingeconomics" in u for u in seen)
    rows = {r["id"]: r for r in macro_rows(load_indicators(), store, today=date(2026, 10, 2))}
    assert rows["us_pmi"]["auto"] is False and rows["us_pmi"]["manual_allowed"] is True
    assert rows["vn_pmi"]["auto"] is True and rows["vn_pmi"]["manual_allowed"] is True


def test_no_pmi_headline_today_is_not_an_error(tmp_path):
    get = lambda url: "<rss></rss>" if url.endswith(".rss") else (_ for _ in ()).throw(OSError("offline"))
    result = fetch_auto(load_indicators(), MacroStore(tmp_path), get=get, today=date(2026, 10, 20))
    assert result["vn_pmi"] == "ok"  # nothing new to record; the overdue reminder covers a missed month
