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
    assert fpt["liquidity"][-1]["cover"] == "0.2000" and (fpt["carry"]["quarter"], fpt["carry"]["yield"]) == (None, None)  # no financial income stored: nothing read
    assert fpt["receivables"]["rows"][-1]["customers"] is None and fpt["receivables"]["dso"]["sector_count"] == 0  # lines not stored
    assert fpt["raise_prepay"] == {"flag": False, "events": []}  # no fundamentals record: no raises known


def test_banks_and_unwatched_tickers_are_not_read_this_way(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/stock/VCB/balance").json()["code"] == "not_applicable"
    assert call(c, clock, "GET", "/internal/stock/HPG/balance").status_code == 404


def test_the_revisions_of_a_ticker_come_newest_first_with_the_lines_name(tmp_path):
    from datetime import date

    from investment_agent.market.statement_revisions import record_revisions
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/stock/FPT/balance").json()["revisions"] == []
    record_revisions(tmp_path, "FPT", [{"period": "2025", "line": "npat_parent", "old": "100000000000", "new": "80000000000"}], kind="years",
                     seen_on=date(2026, 11, 22))
    record_revisions(tmp_path, "FPT", [{"period": "2025", "line": "equity", "old": "900000000000", "new": "870000000000"}], kind="years",
                     seen_on=date(2026, 12, 1))
    rows = call(c, clock, "GET", "/internal/stock/FPT/balance").json()["revisions"]
    assert [(r["line"], r["label"]) for r in rows] == [("equity", "Vốn chủ sở hữu"), ("npat_parent", "LNST công ty mẹ")]


def test_the_balance_carries_lending_against_equity(tmp_path):
    c, clock = client(tmp_path)
    lending = call(c, clock, "GET", "/internal/stock/FPT/balance").json()["lending"]
    assert lending["quarter"] == "2026-Q1" and lending["share"] is None and lending["flag"] is None  # no receivable lines stored: blank, not 0


def test_the_balance_carries_the_provision_flow(tmp_path):
    c, clock = client(tmp_path)
    flow = call(c, clock, "GET", "/internal/stock/FPT/balance").json()["provision_flow"]
    assert flow["quarter"] == "2026-Q1" and flow["rows"][-1]["change"] is None and flow["flag"] is False  # no provision lines: blank


def test_the_balance_carries_the_inventory_block(tmp_path):
    c, clock = client(tmp_path)
    inv = call(c, clock, "GET", "/internal/stock/KDH/balance").json()["inventory"]
    assert inv["rows"][-1]["quarter"] == "2026-Q1" and inv["rows"][-1]["net"] == str(5200 * B) and inv["rows"][-1]["share"] == "2.6000"
    assert inv["rows"][-1]["gross"] is None  # cost not stored in this fixture: blank


def test_a_property_developer_gets_inventory_days_but_no_flag(tmp_path):
    c, clock = client(tmp_path)
    pace = call(c, clock, "GET", "/internal/stock/KDH/balance").json()["inventory_pace"]
    assert pace["quarter"] == "2026-Q1" and pace["flag"] in (False, None)


def test_the_balance_carries_the_gross_loss_check_and_a_property_developer_is_never_flagged(tmp_path):
    """Bán dưới giá vốn nhưng dự phòng không tăng (owner, 23/11/2026)."""
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/stock/FPT/balance").json()["gross_loss"]["quarter"] == "2026-Q1"
    assert call(c, clock, "GET", "/internal/stock/KDH/balance").json()["gross_loss"]["flag"] is False


def test_the_balance_carries_the_inventory_provision_flow(tmp_path):
    c, clock = client(tmp_path)
    flow = call(c, clock, "GET", "/internal/stock/FPT/balance").json()["inventory_provision_flow"]
    assert flow["quarter"] == "2026-Q1" and flow["kind"] is None and flow["rows"][-1]["change"] is None  # no provision lines: blank
