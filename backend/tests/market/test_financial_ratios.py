import json
from datetime import date

from investment_agent.market.financial_ratios import CODES, FinancialRatioStore, fetch_financial_ratios, kind_of


def _page(symbol, rows):
    """Shape of api-finfo.vndirect.com.vn/v4/ratios as served on 31/10/2026 (fields trimmed to those read)."""
    return json.dumps({"data": [{"code": symbol, "group": "FINANCE", "reportDate": d, "ratioCode": c, "value": v} for d, c, v in rows]})


def test_each_financial_ticker_gets_its_sector_codes_by_quarter(tmp_path):
    urls = []

    def get(url):
        urls.append(url)
        return _page("VCB", [("2026-09-30", "BAD_LOANS_RATIO_AQ", 0.0071), ("2025-09-30", "BAD_LOANS_RATIO_AQ", 0.0103),
                             ("2026-09-30", "OTHER", 1.0), ("2026-09-30", "NET_INTEREST_MARGIN_TR_AVG5Q", None)])

    store = FinancialRatioStore(tmp_path)
    out = fetch_financial_ratios(store, {"VCB": "Ngân hàng", "FPT": "Công nghệ Thông tin"}, get=get, today=date(2026, 10, 31))
    assert out == {"VCB": "ok"} and len(urls) == 1
    assert "code:VCB" in urls[0] and ",".join(CODES["bank"]) in urls[0] and "reportDate:gte:2024-08-22" in urls[0]
    rec = store.read("VCB")
    assert rec["kind"] == "bank" and rec["quarters"] == {"2025-09-30": {"BAD_LOANS_RATIO_AQ": "0.0103"}, "2026-09-30": {"BAD_LOANS_RATIO_AQ": "0.0071"}}


def test_a_failing_ticker_is_reported_and_kinds_follow_the_sector():
    assert kind_of("Ngân hàng") == "bank" and kind_of("Dịch vụ tài chính") == "securities" and kind_of("Bảo hiểm") == "insurance"
    assert kind_of("Công nghệ Thông tin") is None

    def get(url):
        raise OSError("timeout")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = fetch_financial_ratios(FinancialRatioStore(d), {"SSI": "Dịch vụ tài chính"}, get=get, today=date(2026, 10, 31), sleep=lambda s: None)
    assert out == {"SSI": "error:OSError"}


def test_cli_financial_ratios_sync_reads_watchlist_and_sectors(tmp_path, capsys):
    from investment_agent.cli import financial_ratios_sync
    (tmp_path / "market-symbols.txt").write_text("SSI\nFPT\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"SSI": "Dịch vụ tài chính", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    assert financial_ratios_sync(tmp_path, get=lambda url: _page("SSI", [("2026-09-30", "ROAA_TR_AVG4Q", 0.05)]), today=date(2026, 10, 31)) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"SSI": "ok"}
    assert FinancialRatioStore(tmp_path / "financial-ratios").read("SSI")["kind"] == "securities"
