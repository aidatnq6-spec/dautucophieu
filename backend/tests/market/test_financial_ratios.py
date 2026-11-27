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
    assert "code:VCB" in urls[0] and ",".join(CODES["bank"]) in urls[0] and "reportDate:gte:2017-01-01" in urls[0] and "size=2000" in urls[0]  # all VNDirect keeps: from Q4/2017
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


def test_a_banks_year_end_car_is_fetched_with_its_ratios_to_check_vietcaps_but_not_shown_as_a_row():
    from investment_agent.market.financial_ratios import CODES, DISPLAY
    assert "BANK_CAR_AQ" in CODES["bank"] and "BANK_CAR_AQ" not in [code for code, _, _ in DISPLAY["bank"]]


def _watch_ssi_fpt(root):
    (root / "market-symbols.txt").write_text("SSI\nFPT\n", encoding="utf-8")
    (root / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                     "sectors": {"SSI": "Dịch vụ tài chính", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")


def _by_symbol(url):
    symbol = url.split("code:")[1].split("~")[0]
    return _page(symbol, [("2026-09-30", "ROAA_TR_AVG4Q", 0.01)])


def test_cli_financial_ratios_sync_adds_every_hose_bank_to_the_watched_financials(tmp_path, capsys):
    from investment_agent.cli import financial_ratios_sync
    _watch_ssi_fpt(tmp_path)
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "t", "listing": {"symbols": ["VCB", "ACB", "FPT"],
        "icb_codes": {"VCB": "8300", "ACB": "8300", "FPT": "9500"}, "icb_names": {"8300": "Ngân hàng", "9500": "Công nghệ Thông tin"}}}),
        encoding="utf-8")
    assert financial_ratios_sync(tmp_path, get=_by_symbol, today=date(2026, 11, 27)) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"ACB": "ok", "SSI": "ok", "VCB": "ok"}
    assert FinancialRatioStore(tmp_path / "financial-ratios").read("VCB")["kind"] == "bank"
    assert FinancialRatioStore(tmp_path / "financial-ratios").read("SSI")["kind"] == "securities"


def test_cli_financial_ratios_sync_without_a_listing_keeps_to_the_watched(tmp_path, capsys):
    from investment_agent.cli import financial_ratios_sync
    _watch_ssi_fpt(tmp_path)
    assert financial_ratios_sync(tmp_path, get=_by_symbol, today=date(2026, 11, 27)) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"SSI": "ok"}


def test_cli_financial_ratios_sync_adds_every_hose_investment_services_firm_but_not_other_financials(tmp_path, capsys):
    from investment_agent.cli import financial_ratios_sync
    _watch_ssi_fpt(tmp_path)
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "t", "listing": {"symbols": ["SSI", "VND", "EVF", "FPT"],
        "icb_codes": {"SSI": "8700", "VND": "8700", "EVF": "8700", "FPT": "9500"},
        "icb_names": {"8700": "Dịch vụ tài chính", "9500": "Công nghệ Thông tin"},
        "icb4_codes": {"SSI": "8777", "VND": "8777", "EVF": "8773", "FPT": "9537"}}}), encoding="utf-8")
    assert financial_ratios_sync(tmp_path, get=_by_symbol, today=date(2026, 11, 27)) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"SSI": "ok", "VND": "ok"}
    assert FinancialRatioStore(tmp_path / "financial-ratios").read("VND")["kind"] == "securities"


def test_cli_financial_ratios_sync_fails_only_for_a_watched_ticker(tmp_path, capsys):
    from investment_agent.cli import financial_ratios_sync
    _watch_ssi_fpt(tmp_path)
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "t", "listing": {"symbols": ["VCB", "ACB"],
        "icb_codes": {"VCB": "8300", "ACB": "8300"}, "icb_names": {"8300": "Ngân hàng"}}}), encoding="utf-8")

    def get(url):
        if "code:VCB" in url:
            raise OSError("down")
        return _by_symbol(url)
    assert financial_ratios_sync(tmp_path, get=get, today=date(2026, 11, 27)) == 0  # VCB is not watched
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok" and out["results"]["VCB"].startswith("error:") and out["unwatched_failed"] == 1

    def get_ssi_down(url):
        if "code:SSI" in url:
            raise OSError("down")
        return _by_symbol(url)
    assert financial_ratios_sync(tmp_path, get=get_ssi_down, today=date(2026, 11, 27)) == 1  # SSI is watched
    assert json.loads(capsys.readouterr().out)["status"] == "partial"


def test_cli_financial_ratios_sync_adds_every_hose_insurer(tmp_path, capsys):
    from investment_agent.cli import financial_ratios_sync
    _watch_ssi_fpt(tmp_path)
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "t", "listing": {"symbols": ["BVH", "PGI"],
        "icb_codes": {"BVH": "8500", "PGI": "8500"}, "icb_names": {"8500": "Bảo hiểm"}}}), encoding="utf-8")
    assert financial_ratios_sync(tmp_path, get=_by_symbol, today=date(2026, 11, 27)) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"BVH": "ok", "PGI": "ok", "SSI": "ok"}
    assert FinancialRatioStore(tmp_path / "financial-ratios").read("BVH")["kind"] == "insurance"
