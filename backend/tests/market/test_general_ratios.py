"""Chỉ số tài chính doanh nghiệp thường: VNDirect's own quarterly ratios for every HOSE ticker outside banks, securities and insurance."""

import json
from datetime import datetime, timezone

from investment_agent.market.general_ratios import CODES, GeneralRatioStore, sync_general_ratios

NOW = datetime(2026, 11, 26, 13, tzinfo=timezone.utc)


def _setup(tmp_path, symbols, sectors):
    (tmp_path / "hose-listing.json").write_text(json.dumps({"listing": {"symbols": symbols}}), encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"sectors": sectors}), encoding="utf-8")


def answer(symbol):
    return json.dumps({"data": [
        {"code": symbol, "ratioCode": "ROAE_TR_AVG4Q", "itemName": "ROAE ", "reportDate": "2026-09-30", "value": 0.08199},
        {"code": symbol, "ratioCode": "GROSS_MARGIN_QR", "itemName": "Biên lợi nhuận gộp quý", "reportDate": "2026-09-30", "value": 0.1485},
        {"code": symbol, "ratioCode": "ROAE_TR_AVG4Q", "itemName": "ROAE ", "reportDate": "2026-06-30", "value": 0.09},
        {"code": symbol, "ratioCode": "PRICE_CHG_PCT_CR_1D", "itemName": "not asked", "reportDate": "2026-09-30", "value": 1},
        {"code": "OTHER", "ratioCode": "ROAE_TR_AVG4Q", "itemName": "ROAE", "reportDate": "2026-09-30", "value": 5}]})


def test_every_non_financial_hose_ticker_is_fetched_with_vndirects_names(tmp_path):
    _setup(tmp_path, ["ACB", "KDH", "SSI", "BVH", "ZZZ"], {"ACB": "Ngân hàng", "SSI": "Dịch vụ tài chính", "BVH": "Bảo hiểm", "KDH": "Bất động sản"})
    asked, urls = [], []

    def get(url):
        symbol = url.split("code:")[1].split("~")[0]
        asked.append(symbol)
        urls.append(url)
        return answer(symbol)

    out = sync_general_ratios(tmp_path, get=get, now=NOW, limit=10, sleep=lambda s: None)
    assert asked == ["KDH", "ZZZ"]  # banks, securities firms and insurers keep their own ratios; an unsectored ticker is asked too
    assert out == {"status": "ok", "due": 2, "updated": 2, "empty": 0, "failed": {}}
    assert all("ROAE_TR_AVG4Q" in u and "reportDate:gte:2017-01-01" in u for u in urls)
    rec = GeneralRatioStore(tmp_path).read("KDH")
    assert rec["kind"] == "general" and rec["source"] == "vndirect:finfo" and rec["fetched_at"] == NOW.isoformat()
    assert rec["names"] == {"GROSS_MARGIN_QR": "Biên lợi nhuận gộp quý", "ROAE_TR_AVG4Q": "ROAE"}
    assert rec["quarters"] == {"2026-06-30": {"ROAE_TR_AVG4Q": "0.09"}, "2026-09-30": {"ROAE_TR_AVG4Q": "0.08199", "GROSS_MARGIN_QR": "0.1485"}}


def test_a_ticker_refreshed_this_week_waits_and_an_empty_answer_keeps_the_file(tmp_path):
    _setup(tmp_path, ["KDH", "HPG"], {})
    store = GeneralRatioStore(tmp_path)
    store.save("KDH", {"symbol": "KDH", "fetched_at": "2026-11-24T00:00:00+00:00", "quarters": {"x": {}}})
    out = sync_general_ratios(tmp_path, get=lambda url: json.dumps({"data": []}), now=NOW, sleep=lambda s: None)
    assert out == {"status": "ok", "due": 1, "updated": 0, "empty": 1, "failed": {}}
    assert store.read("KDH")["quarters"] == {"x": {}} and store.read("HPG") is None


def test_the_codes_are_quarterly_company_ratios_not_daily_market_ones():
    assert "ROAE_TR_AVG4Q" in CODES and "DEBT_TO_EQUITY_AQ" in CODES and "INTEREST_COVERAGE_TR" in CODES
    assert not any(c.startswith(("PRICE_", "NMV", "FOREIGN_", "DOMESTIC_")) for c in CODES) and len(CODES) <= 30
