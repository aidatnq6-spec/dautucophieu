import json

from investment_agent.market.statements import StatementStore

from signed_client import call
from test_passive_income_route import client as base_client

B = 10**9


def q(**values) -> dict:
    return {k: str(v * B) for k, v in values.items()}


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("KDH\nNLG\nFPT\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-11-11", "source": "t", "level": 2, "sectors": {
        "KDH": "Bất động sản", "NLG": "Bất động sản", "FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}}), encoding="utf-8")
    store = StatementStore(tmp_path / "statements")
    year_ago = q(st_debt=100, lt_debt=100, cash=50, st_investments=0, equity=1000, total_assets=2000, advances_st=1000, advances_lt=0,
                 inventory=5000, cfo=10, npat_parent=40)
    kdh = {f"2024-Q{n}": year_ago for n in range(1, 5)} | {f"2025-Q{n}": year_ago for n in range(1, 5)} | {
        "2026-Q1": q(st_debt=300, lt_debt=200, cash=50, st_investments=0, equity=1000, total_assets=2000, advances_st=1400, advances_lt=100,
                     inventory=5200, cfo=300, npat_parent=30)}
    store.save({"symbol": "KDH", "quarters": kdh, "years": {}})
    store.save({"symbol": "NLG", "quarters": {"2026-Q1": q(st_debt=10, lt_debt=0, cash=500, st_investments=100, equity=900, total_assets=1500)}, "years": {}})
    store.save({"symbol": "FPT", "quarters": {"2026-Q1": q(st_debt=50, lt_debt=0, cash=10, st_investments=0, equity=500, total_assets=900)}, "years": {}})
    return base_client(tmp_path)


def test_a_property_developer_gets_net_debt_its_sectors_borrowing_and_customer_advances(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/stock/KDH/balance").json()
    assert body["symbol"] == "KDH" and body["sector"] == "Bất động sản"
    assert body["debt"]["rows"][-1]["net_debt"] == str(450 * B) and body["debt"]["flag"]["kind"] == "fast_borrowing"
    assert body["sector_debt"]["quarters"][-1]["count"] == 2 and body["sector_debt"]["members"] == 2
    assert body["property"]["signal"]["kind"] == "collecting" and body["property"]["rows"][-1]["advances"] == str(1500 * B)


def test_a_company_outside_property_has_no_advances_block_and_net_cash_shows(tmp_path):
    c, clock = client(tmp_path)
    nlg = call(c, clock, "GET", "/internal/stock/NLG/balance").json()
    assert nlg["debt"]["rows"][-1]["net_cash"] is True
    fpt = call(c, clock, "GET", "/internal/stock/FPT/balance").json()
    assert fpt["property"] is None and fpt["sector_debt"]["members"] == 1


def test_banks_and_unwatched_tickers_are_not_read_this_way(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/stock/VCB/balance").json()["code"] == "not_applicable"
    assert call(c, clock, "GET", "/internal/stock/HPG/balance").status_code == 404
