from investment_agent.domain.balance_watch import (
    borrowing_flag, carry, liquidity_rows, net_debt_rows, property_cash, receivables_view, sector_debt,
)

B = 10**9


def q(**values) -> dict:
    return {k: str(v * B) for k, v in values.items()}


def quarters_from(start_year: int, rows: list[dict]) -> dict:
    out, y, n = {}, start_year, 1
    for r in rows:
        out[f"{y}-Q{n}"] = r
        y, n = (y + 1, 1) if n == 4 else (y, n + 1)
    return out


def test_net_debt_is_borrowing_less_cash_and_short_term_investments_and_a_negative_one_is_net_cash():
    qs = {"2026-Q2": q(st_debt=100, lt_debt=300, cash=50, st_investments=20, equity=800, total_assets=2000),
          "2026-Q3": q(st_debt=50, lt_debt=100, cash=150, st_investments=100, equity=900, total_assets=2000)}
    rows = net_debt_rows(qs)
    assert [r["quarter"] for r in rows] == ["2026-Q2", "2026-Q3"]
    assert rows[0]["debt"] == str(400 * B) and rows[0]["net_debt"] == str(330 * B) and rows[0]["net_cash"] is False
    assert rows[0]["debt_to_equity"] == "0.5000"
    assert rows[1]["net_debt"] == str(-100 * B) and rows[1]["net_cash"] is True


def test_a_missing_line_leaves_net_debt_blank():
    rows = net_debt_rows({"2026-Q3": q(st_debt=50, lt_debt=100, cash=150, equity=900)})  # no short-term investments line
    assert rows[0]["debt"] == str(150 * B) and rows[0]["net_debt"] is None and rows[0]["net_cash"] is None


def test_borrowing_that_doubled_in_two_years_is_flagged_only_when_it_matters():
    base = [q(st_debt=100, lt_debt=100, total_assets=1000)] * 8
    doubled = quarters_from(2024, base + [q(st_debt=250, lt_debt=200, total_assets=1500)])
    flag = borrowing_flag(doubled)
    assert flag["kind"] == "fast_borrowing" and flag["quarter"] == "2026-Q1" and flag["ratio"] == "2.2500"
    small = quarters_from(2024, [q(st_debt=1, lt_debt=1, total_assets=1000)] * 8 + [q(st_debt=10, lt_debt=10, total_assets=1000)])
    assert borrowing_flag(small)["kind"] is None  # 2% of assets: not worth a warning
    steady = quarters_from(2024, base + [q(st_debt=120, lt_debt=120, total_assets=1000)])
    assert borrowing_flag(steady)["kind"] is None and borrowing_flag(steady)["ratio"] == "1.2000"


def test_no_quarter_two_years_back_means_no_comparison():
    flag = borrowing_flag({"2026-Q3": q(st_debt=100, lt_debt=100, total_assets=1000)})
    assert flag["kind"] is None and flag["ratio"] is None


def test_sector_debt_adds_the_tickers_that_report_each_quarter_and_compares_two_years_on_those_with_both():
    a = quarters_from(2024, [q(st_debt=100, lt_debt=0, cash=10, st_investments=0)] * 8 + [q(st_debt=300, lt_debt=0, cash=10, st_investments=0)])
    b = quarters_from(2025, [q(st_debt=50, lt_debt=0, cash=60, st_investments=0)] * 5)  # listed later: no two-year comparison
    view = sector_debt({"AAA": a, "BBB": b})
    last = view["quarters"][-1]
    assert last["quarter"] == "2026-Q1" and last["count"] == 2 and last["debt"] == str(350 * B) and last["net_debt"] == str(280 * B)
    assert view["growth_2y"] == "2.0000" and view["compared"] == 1 and view["top"] == "AAA"


def test_property_cash_reads_handover_when_profit_jumps_as_customer_advances_fall():
    rows = [q(advances_st=1000, advances_lt=200, inventory=5000, cfo=100, npat_parent=40)] * 4 + \
           [q(advances_st=600, advances_lt=100, inventory=4000, cfo=-50, npat_parent=500)]
    view = property_cash(quarters_from(2025, rows))
    assert view["rows"][-1]["advances"] == str(700 * B) and view["rows"][-1]["inventory"] == str(4000 * B)
    assert view["signal"]["kind"] == "handover" and view["signal"]["advances_yoy"] == "-0.4167"


def test_property_cash_reads_collecting_when_advances_rise_and_says_nothing_otherwise():
    rising = [q(advances_st=1000, advances_lt=0, inventory=5000, cfo=100, npat_parent=40)] * 4 + \
             [q(advances_st=1500, advances_lt=0, inventory=5200, cfo=400, npat_parent=30)]
    assert property_cash(quarters_from(2025, rising))["signal"]["kind"] == "collecting"
    flat = [q(advances_st=1000, advances_lt=0, inventory=5000, cfo=100, npat_parent=40)] * 5
    assert property_cash(quarters_from(2025, flat))["signal"]["kind"] is None


def test_property_cash_without_the_advances_lines_says_so_rather_than_guessing():
    view = property_cash(quarters_from(2025, [q(inventory=5000, cfo=100, npat_parent=40)] * 5))
    assert view["rows"][-1]["advances"] is None and view["signal"]["kind"] is None and view["signal"]["advances_yoy"] is None


# T3 Thang thanh khoản: cash and short-term investments against short-term borrowing, and their share of total assets.
def test_liquidity_rows_set_cash_against_short_term_borrowing():
    qs = {"2026-Q2": q(cash=40, st_investments=160, st_debt=100, lt_debt=50, total_assets=1000),
          "2026-Q3": q(cash=30, st_investments=20, st_debt=0, lt_debt=50, total_assets=1000),
          "2026-Q4": q(cash=30, st_debt=100, total_assets=1000)}  # short-term investments missing
    r2, r3, r4 = liquidity_rows(qs)
    assert r2 == {"quarter": "2026-Q2", "cash": str(40 * B), "st_investments": str(160 * B), "cash_like": str(200 * B), "st_debt": str(100 * B),
                  "cover": "2.0000", "cash_share": "0.2000"}
    assert r3["cover"] is None and r3["st_debt"] == "0"  # no short-term borrowing: nothing to cover, not infinitely covered
    assert (r4["cash_like"], r4["cover"], r4["cash_share"]) == (None, None, None)


def year_of_quarters(**over):
    """Five quarter ends 2025-Q3 … 2026-Q3; the last four carry their quarter's financial income and interest."""
    base = dict(cash=100, st_investments=300, st_debt=150, lt_debt=50, total_assets=2000)
    out = {"2025-Q3": q(**base)}
    for p in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"):
        out[p] = q(**{**base, "fin_income": 7, "interest": 2, **over})
    return out


# T1 Chênh lệch lãi vay – lãi gửi over the last four quarters, on the averages of the five quarter ends around them.
def test_carry_reads_four_quarters_of_financial_income_and_interest_on_average_balances():
    c = carry(year_of_quarters())
    assert c == {"quarter": "2026-Q3", "kind": "carry", "missing": [], "fin_income": str(28 * B), "interest": str(8 * B), "net": str(20 * B),
                 "avg_cash_like": str(400 * B), "avg_debt": str(200 * B), "yield": "0.0700", "cost": "0.0400", "spread": "0.0300"}


def test_carry_is_named_only_when_both_borrowing_and_cash_are_material_and_the_spread_is_positive():
    small_debt = year_of_quarters()
    for p in small_debt:
        small_debt[p] = {**small_debt[p], "st_debt": str(10 * B), "lt_debt": "0"}  # 0.5% of total assets
    assert carry(small_debt)["kind"] is None and carry(small_debt)["spread"] is not None
    dear = year_of_quarters(interest=10)  # 40 on 200 borrowed: 20% against 7% earned
    assert carry(dear)["kind"] is None and carry(dear)["spread"] == "-0.1300"
    no_debt = year_of_quarters(interest=0)
    for p in no_debt:
        no_debt[p] = {**no_debt[p], "st_debt": "0", "lt_debt": "0"}
    assert (carry(no_debt)["kind"], carry(no_debt)["cost"], carry(no_debt)["yield"]) == ("no_debt", None, "0.0700")


def test_figures_no_deposit_pays_or_no_loan_costs_are_named_instead_of_carry():
    rich = year_of_quarters(fin_income=30)  # 120 on 400: 30% a year, no deposit pays that (exchange gains, gains on investments)
    assert (carry(rich)["kind"], carry(rich)["yield"]) == ("unusual_income", "0.3000")
    cheap = year_of_quarters(interest=0.5)  # 2 on 200: 1% a year, interest likely capitalised into projects or assets being built
    assert (carry(cheap)["kind"], carry(cheap)["cost"]) == ("low_interest", "0.0100")
    edge = year_of_quarters(fin_income=10, interest=1)  # exactly 10% earned and 2% paid: still carry
    assert carry(edge)["kind"] == "carry"


def test_carry_with_a_quarter_missing_names_it_and_computes_nothing():
    qs = year_of_quarters()
    del qs["2026-Q1"]["interest"]
    del qs["2025-Q3"]
    c = carry(qs)
    assert c["quarter"] == "2026-Q3" and c["missing"] == ["2025-Q3", "2026-Q1"] and c["yield"] is None and c["kind"] is None
    assert carry({})["quarter"] is None


def ar_quarter(customers=100, prepay=20, loans=0, other=30, provision=-10, total_st=140, lt_total=50, lt_customers=0, lt_loans=0,
               lt_other=50, lt_provision=0, revenue=91.25, assets=1000):
    return q(ar_customers=customers, prepay_suppliers=prepay, st_loans_receivable=loans, other_receivables=other, bad_debt_st=provision,
             receivables=total_st, receivables_lt=lt_total, ar_customers_lt=lt_customers, lt_loans_receivable=lt_loans,
             other_receivables_lt=lt_other, bad_debt_lt=lt_provision, revenue=revenue, total_assets=assets)


# R1 Bóc tách phải thu: short and long-term parts side by side, each row adding the two.
def test_receivable_rows_add_short_and_long_term_parts_and_their_share_of_total_assets():
    qs = quarters_from(2025, [ar_quarter() for _ in range(8)])
    row = receivables_view(qs)["rows"][-1]
    assert row == {"quarter": "2026-Q4", "customers": str(100 * B), "prepay": str(20 * B), "loans": str(0), "other": str(80 * B),
                   "provision": str(-10 * B), "total": str(190 * B), "total_share": "0.1900", "other_share": "0.0800", "dso": "100"}


# R2 Số ngày thu tiền: short-term customer receivables at the quarter's end against the last four quarters' revenue, × 365.
def test_days_to_collect_on_four_quarters_of_revenue_and_against_the_sector_median():
    qs = quarters_from(2025, [ar_quarter(customers=100 + 10 * i) for i in range(8)])
    v = receivables_view(qs, peers={"AAA": quarters_from(2025, [ar_quarter(customers=50)] * 8),
                                    "BBB": quarters_from(2025, [ar_quarter(customers=80)] * 8),
                                    "CCC": quarters_from(2025, [ar_quarter(customers=200)] * 8)})
    assert v["dso"] == {"quarter": "2026-Q4", "days": "170", "year_ago": "130", "change": "40", "sector_median": "80", "sector_count": 3}
    assert receivables_view(quarters_from(2026, [ar_quarter()] * 3))["dso"]["days"] is None  # fewer than four quarters of revenue


# R3 Dự phòng phải thu khó đòi: its share of gross short-term receivables, and a jump against a year before.
def test_bad_debt_provision_share_and_a_jump_from_a_year_before():
    qs = quarters_from(2025, [ar_quarter(provision=-10)] * 4 + [ar_quarter(provision=-10)] * 3 + [ar_quarter(provision=-20, total_st=130)])
    p = receivables_view(qs)["provision"]
    assert p == {"quarter": "2026-Q4", "amount": str(20 * B), "share": "0.1333", "year_ago": str(10 * B), "kind": "jump"}  # 20 of 150 gross
    calm = receivables_view(quarters_from(2025, [ar_quarter()] * 8))["provision"]
    assert (calm["kind"], calm["share"]) == (None, "0.0667")
    none = receivables_view(quarters_from(2025, [ar_quarter(provision=0, total_st=150)] * 8))["provision"]
    assert (none["kind"], none["amount"]) == ("none", "0")


def test_missing_receivable_lines_leave_their_cells_blank():
    v = receivables_view({"2026-Q3": q(receivables=100, total_assets=1000)})
    row = v["rows"][-1]
    assert (row["customers"], row["other"], row["total"], row["dso"]) == (None, None, None, None)
    assert v["provision"]["amount"] is None and v["dso"]["days"] is None
