import json

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.statements import StatementStore
from investment_agent.services.receivable_signs import SIGNS, receivable_signs

BN = 10**9


def year(**v):
    return {k: str(x * BN) for k, x in v.items()}


def data(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("AAA\nBBB\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-11-11", "source": "t", "level": 2, "sectors": {
        "AAA": "Xây dựng và Vật liệu", "BBB": "Xây dựng và Vật liệu", "VCB": "Ngân hàng"}}), encoding="utf-8")
    base = dict(revenue=100, gross_profit=20, profit=10, total_assets=100, current_assets=50, current_liabilities=40, long_liabilities=10,
                receivables=10, cfo=12)
    fs = FundamentalsStore(tmp_path / "fundamentals")
    fs.save({"symbol": "AAA", "annual": {"2024": year(**base), "2025": year(**{**base, "fin_income": 40, "fin_expense": 2, "pbt": 50,
                                                                              "interest_received": 3, "other_receivables": 20, "other_receivables_lt": 0,
                                                                              "prepay_suppliers": 1})}, "share_issues": []})
    fs.save({"symbol": "BBB", "annual": {"2024": year(**base), "2025": year(**{**base, "fin_income": 1, "fin_expense": 1, "pbt": 50,
                                                                              "interest_received": 1, "other_receivables": 1, "other_receivables_lt": 0,
                                                                              "prepay_suppliers": 1})}, "share_issues": []})
    StatementStore(tmp_path / "statements").save({"symbol": "AAA", "quarters": {}, "years": {}})
    return tmp_path


def test_each_watched_non_financial_ticker_gets_its_receivable_signs_most_first(tmp_path):
    rows = receivable_signs(data(tmp_path))
    assert [r["symbol"] for r in rows] == ["AAA", "BBB"]  # the bank is left out
    aaa, bbb = rows
    assert aaa["signs"]["other_receivables"] is True and aaa["signs"]["paper_income"] is True and aaa["signs"]["financial_profit"] is True
    assert aaa["count"] == 3 and bbb["count"] == 0
    assert aaa["signs"]["other_high"] is None  # no quarters stored: not read
    assert [k for k, _ in SIGNS][:3] == ["other_receivables", "other_high", "prepay_suppliers"]


def test_lending_against_equity_is_a_sign_with_its_figure(tmp_path):
    from investment_agent.market.statements import StatementStore
    d = data(tmp_path)
    B = 10**9
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {}, "quarters": {
        "2025-Q1": {"other_receivables": str(100 * B), "other_receivables_lt": "0", "st_loans_receivable": "0", "lt_loans_receivable": "0", "equity": str(1000 * B)},
        "2026-Q1": {"other_receivables": str(350 * B), "other_receivables_lt": "0", "equity": str(1000 * B)}}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("lending", "Cho vay lớn so với vốn chủ") in SIGNS and aaa["signs"]["lending"] is True
    assert aaa["details"]["lending"] == "Cho vay và phải thu khác bằng 35% vốn chủ (quý 1/2026); xem Sổ phải thu bên liên quan trên hồ sơ mã."


def test_inventory_growing_faster_than_cost_of_sales_is_a_sign_with_its_figures(tmp_path):
    from investment_agent.market.statements import StatementStore
    d = data(tmp_path)
    B = 10**9
    q = lambda inv, cogs: {"inventory": str(inv * B), "cogs": str(cogs * B), "total_assets": str(1000 * B)}  # noqa: E731
    StatementStore(d / "statements").save({"symbol": "AAA", "years": {}, "quarters": {f"2024-Q{n}": q(200, 100) for n in range(1, 5)}
                                           | {f"2025-Q{n}": q(300, 110) for n in range(1, 5)}})
    aaa = next(r for r in receivable_signs(d) if r["symbol"] == "AAA")
    assert ("inventory_fast", "Tồn kho tăng nhanh hơn giá vốn") in SIGNS and aaa["signs"]["inventory_fast"] is True
    assert aaa["details"]["inventory_fast"] == "Tồn kho tăng 50% so cùng kỳ, giá vốn bốn quý tăng 10%; tồn kho đủ 249 ngày (cùng kỳ 183 ngày)."
