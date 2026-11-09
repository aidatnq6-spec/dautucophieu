from datetime import datetime
from decimal import Decimal

from investment_agent.valuation.statement_table import statement_table

B = 10**9


def q(revenue, npat, **more):
    """A quarter in tỷ đồng: costs positive, cash paid negative, as VNDirect gives them."""
    base = {"revenue": revenue, "cogs": revenue * 0.8, "gross_profit": revenue * 0.2, "selling": 10, "admin": 5, "fin_income": 2,
            "fin_expense": 8, "interest": 6, "associates": 0, "other_profit": 1, "pbt": npat * 1.25, "tax": npat * 0.25, "npat": npat,
            "npat_parent": npat, "depreciation": 20, "cfo": 50, "capex": -30, "equity": 1000, "minority_equity": 10, "st_debt": 300,
            "lt_debt": 200, "cash": 40, "st_investments": 60}
    base.update(more)
    return {k: str(Decimal(str(v)) * B) for k, v in base.items()}


QUARTERS = {f"{y}-Q{k}": q(100 * (y - 2023) + 10 * k, 20 * (y - 2023) + k) for y in (2024, 2025) for k in (1, 2, 3, 4)}
YEARS = {"2024": q(1000, 84, equity=900, cfo=200, capex=-120, interest=24, depreciation=80, charter_capital=100),
         "2025": q(2000, 164, equity=1000, cfo=210, capex=-130, interest=24, depreciation=80, charter_capital=100)}  # 10 million shares
RECORD = {"symbol": "AAA", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo", "quarters": QUARTERS, "years": YEARS,
          "quarters_conflicts": [], "years_conflicts": [{"period": "2012", "line": "depreciation", "values": ["1", "2"]}],
          "year_end_close": {"2024": {"date": "2024-12-31", "close": "20"}, "2025": {"date": "2025-12-31", "close": "30"}}}
# Adjusted closes in thousand đồng; 10,000,000 shares today.
CLOSES = [(datetime(2024, 12, 31), 20.0), (datetime(2025, 12, 31), 30.0), (datetime(2026, 11, 6), 25.0)]


def rows(table, part):
    return {r["key"]: r["values"] for r in table[part]["rows"]}


def test_quarters_carry_the_income_statement_core_profit_ebit_ebitda_and_their_growth_and_margins():
    t = statement_table(RECORD, closes=CLOSES, vnstock=None)
    assert t["quarters"]["periods"][-1] == "2025-Q4" and len(t["quarters"]["periods"]) == 8
    r = rows(t, "quarters")
    i = t["quarters"]["periods"].index("2025-Q4")
    assert r["revenue"][i] == "240000000000" and r["revenue_yoy"][i] == "0.7143"  # 240 against 140 a year before
    assert r["cogs"][i] == "-192000000000" and r["selling"][i] == "-10000000000"  # costs shown negative
    assert r["core_profit"][i] == "33000000000"  # gross 48 − selling 10 − admin 5
    assert r["gross_margin"][i] == "0.2000"
    assert r["ebit"][i] == "61000000000" and r["ebitda"][i] == "81000000000"  # profit before tax 55 + interest 6 ; + depreciation 20
    assert r["revenue_yoy"][0] is None  # 2024-Q1 has no quarter a year before it


def test_years_add_scale_and_valuation_on_the_year_end_close_and_that_year_s_share_count():
    t = statement_table(RECORD, closes=CLOSES, vnstock=None)
    r = rows(t, "years")
    i = t["years"]["periods"].index("2025")
    assert r["market_cap"][i] == "300000000000"  # unadjusted 30,000 đ × charter capital 100 tỷ ÷ 10,000 đ
    assert r["net_debt"][i] == "400000000000"  # 300 + 200 − 40 − 60
    assert r["ev"][i] == "710000000000"  # 300 + 400 + minority 10
    assert r["pe"][i] == "1.83" and r["pb"][i] == "0.30"  # 300 / 164 ; 300 / (1000 − 10)
    assert r["ev_ebitda"][i] == "2.30"  # 710 / (205 + 24 + 80)
    assert r["fcff"][i] == "99200000000"  # 210 + 24 × (1 − 0.2) − 130, effective tax 41 / 205
    assert r["fcff_yield"][i] == "0.1397"
    assert r["roe"][i] == "0.1745"  # 164 / average(990, 890)
    assert r["roe"][t["years"]["periods"].index("2024")] is None  # no year before 2024 to average with


def test_fcff_needs_a_positive_profit_before_tax_and_valuation_needs_a_price():
    years = {**YEARS, "2025": q(2000, -10, pbt=-12, tax=-2)}
    t = statement_table({**RECORD, "years": years, "year_end_close": {}}, closes=[], vnstock=None)
    r = rows(t, "years")
    i = t["years"]["periods"].index("2025")
    assert r["fcff"][i] is None and r["pe"][i] is None and r["market_cap"][i] is None


def test_the_summary_uses_the_last_four_quarters_and_today_s_close():
    quarters = {p: {**f, "charter_capital": str(100 * B)} for p, f in QUARTERS.items()}
    record = {**RECORD, "quarters": quarters, "quarter_end_close": {"2025-Q4": {"date": "2025-12-31", "close": "30"}}}
    # 10 million shares from the charter capital, 30,000 đ at the quarter's end, then 30 → 25 on the adjusted series. A share count passed in
    # from profit and EPS no longer reaches the cards: it missed by up to double.
    s = statement_table(record, closes=CLOSES, vnstock=None)["summary"]
    assert s["period"] == "2025-Q4" and s["market_cap"] == "250000000000" and s["npat_ttm"] == "170000000000"  # 41 + 42 + 43 + 44 tỷ
    assert s["pe"] == "1.47" and s["roe"] == "0.1717"  # 250 / 170 ; 170 / average(990, 990)
    # A bonus issue after the quarter halves the adjusted close of that session: the market value is unaffected.
    halved = [(datetime(2025, 12, 31), 15.0), (datetime(2026, 11, 6), 12.5)]
    assert statement_table(record, closes=halved, vnstock=None)["summary"]["market_cap"] == "250000000000"
    # No close on the quarter's last session: price-based cards blank, profit cards still there.
    s = statement_table(record, closes=[(datetime(2026, 11, 6), 25.0)], vnstock=None)["summary"]
    assert s["market_cap"] is None and s["pe"] is None and s["ev"] is None and s["npat_ttm"] == "170000000000"


def test_checks_flag_quarters_that_do_not_add_up_to_the_year_and_a_second_source_that_differs():
    quarters = {**QUARTERS, "2025-Q4": q(240, 24, gross_profit=50)}  # 240 − 192 ≠ 50
    t = statement_table({**RECORD, "quarters": quarters}, closes=CLOSES,
                        vnstock={"2025-Q3": {"npat": str(43 * B)}, "2025-Q2": {"npat": str(30 * B)}})
    found = {(c["period"], c["check"]) for c in t["checks"]}
    assert ("2025-Q4", "gross_profit") in found
    assert ("2025", "revenue") in found  # 210 + 220 + 230 + 240 ≠ 2000
    assert ("2025-Q2", "vnstock_npat") in found and ("2025-Q3", "vnstock_npat") not in found
    assert t["conflicts"] == [{"period": "2012", "line": "depreciation", "values": ["1", "2"]}]


def test_a_year_without_an_unadjusted_close_or_a_charter_capital_has_no_valuation():
    years = {**YEARS, "2025": {k: v for k, v in YEARS["2025"].items() if k != "charter_capital"}}
    r = rows(statement_table({**RECORD, "years": years}, closes=CLOSES, vnstock=None), "years")
    assert r["market_cap"] == ["200000000000", None] and r["pe"][1] is None  # 2024 still valued; 2025 lacks the share count


QUARTER_CLOSES = {"2024-Q4": {"date": "2024-12-31", "close": "20"}, "2025-Q3": {"date": "2025-09-30", "close": "28"},
                  "2025-Q4": {"date": "2025-12-31", "close": "30"}}


def test_quarters_carry_the_valuation_block_on_the_quarter_end_close_and_the_four_quarters_to_it():
    quarters = {p: {**f, "charter_capital": str(100 * B)} for p, f in QUARTERS.items()}
    t = statement_table({**RECORD, "quarters": quarters, "quarter_end_close": QUARTER_CLOSES}, closes=CLOSES, vnstock=None)
    labels = [r["label"] for r in t["quarters"]["rows"] if r["kind"] == "group"]
    assert labels[-1] == "Quy mô và định giá"
    r = rows(t, "quarters")
    i = t["quarters"]["periods"].index("2025-Q4")
    assert r["market_cap"][i] == "300000000000"  # unadjusted 30,000 đ at the quarter's last session × 10 million shares
    assert r["net_debt"][i] == "400000000000" and r["ev"][i] == "710000000000"  # quarter-end balance: 300 + 200 − 40 − 60 ; + minority 10
    assert r["pe"][i] == "1.76"  # 300 / (41 + 42 + 43 + 44)
    assert r["pb"][i] == "0.30"  # 300 / (1000 − 10)
    assert r["ev_ebitda"][i] == "2.24"  # 710 / four quarters of (pbt + 6 + 20): 212.5 + 104
    assert r["ev_revenue"][i] == "0.79"  # 710 / (210 + 220 + 230 + 240)
    assert r["roe"][i] == "0.1717"  # 170 / average(990, 990)
    assert r["debt_to_equity"][i] == "0.50"  # borrowings (300 + 200) / equity with minority (1000), as for a securities firm
    assert r["debt_to_equity"][t["quarters"]["periods"].index("2025-Q2")] == "0.50"  # the balance sheet alone: no price needed
    assert r["fcff_yield"][i] is not None
    assert r["market_cap"][t["quarters"]["periods"].index("2025-Q2")] is None  # no close kept for that quarter
    assert r["pe"][t["quarters"]["periods"].index("2024-Q4")] is not None and r["roe"][t["quarters"]["periods"].index("2024-Q4")] is None
    assert r["pe"][t["quarters"]["periods"].index("2025-Q3")] == "1.87"  # 280 / (24 + 41 + 42 + 43)


def test_a_quarter_without_four_quarters_behind_it_has_no_earnings_multiples():
    quarters = {p: {**f, "charter_capital": str(100 * B)} for p, f in QUARTERS.items() if p != "2025-Q2"}
    r = rows(statement_table({**RECORD, "quarters": quarters, "quarter_end_close": QUARTER_CLOSES}, closes=CLOSES,
                             vnstock=None), "quarters")
    periods = sorted(quarters)
    i = periods.index("2025-Q4")
    assert r["market_cap"][i] == "300000000000" and r["pb"][i] == "0.30"
    assert r["pe"][i] is None and r["ev_ebitda"][i] is None and r["roe"][i] is None and r["fcff_yield"][i] is None


def fin(npat, **more):
    """A bank or securities firm's period in tỷ đồng: equity with 10 tỷ of non-controlling interests, 10 million shares."""
    base = {"npat_parent": npat, "equity": 1000, "minority_equity": 10, "charter_capital": 100, "ppop": 2 * npat, "operating_income": 3 * npat,
            "operating_revenue": 4 * npat, "st_debt": 300, "lt_debt": 200}
    base.update(more)
    return {k: str(Decimal(str(v)) * B) for k, v in base.items()}


FIN_RECORD = {"symbol": "BBB", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo", "kind": "bank",
              "quarters": {f"{y}-Q{k}": fin(20 * (y - 2023) + k) for y in (2024, 2025) for k in (1, 2, 3, 4)},
              "years": {"2024": fin(84, equity=900), "2025": fin(164)}, "quarters_conflicts": [], "years_conflicts": [],
              "year_end_close": {"2025": {"date": "2025-12-31", "close": "30"}}, "quarter_end_close": QUARTER_CLOSES}


def test_a_bank_gets_only_its_scale_and_valuation_block_on_four_quarters_and_on_the_year():
    t = statement_table(FIN_RECORD, closes=CLOSES, vnstock=None, kind="bank")
    assert [r["label"] for r in t["quarters"]["rows"]][0] == "Quy mô và định giá" and t["summary"] is None
    assert [r["key"] for r in t["quarters"]["rows"][1:]] == ["market_cap", "parent_equity", "bvps", "pb", "pe", "roe", "p_ppop", "p_toi"]
    r = rows(t, "quarters")
    i = t["quarters"]["periods"].index("2025-Q4")
    assert r["market_cap"][i] == "300000000000" and r["parent_equity"][i] == "990000000000"
    assert r["bvps"][i] == "99000"  # 990 tỷ ÷ 10 million shares
    assert r["pb"][i] == "0.30" and r["pe"][i] == "1.76" and r["roe"][i] == "0.1717"  # 300 / 990 ; 300 / 170 ; 170 / 990
    assert r["p_ppop"][i] == "0.88" and r["p_toi"][i] == "0.59"  # 300 / 340 ; 300 / 510
    y = rows(t, "years")
    j = t["years"]["periods"].index("2025")
    assert y["pe"][j] == "1.83" and y["p_ppop"][j] == "0.91" and y["roe"][j] == "0.1745"  # 300 / 164 ; 300 / 328 ; 164 / average(990, 890)
    assert y["market_cap"][t["years"]["periods"].index("2024")] is None  # no close kept for 2024


def test_a_securities_firm_gets_borrowings_to_equity_and_capitalisation_to_operating_revenue():
    t = statement_table({**FIN_RECORD, "kind": "securities"}, closes=CLOSES, vnstock=None, kind="securities")
    assert [r["key"] for r in t["quarters"]["rows"][1:]] == ["market_cap", "parent_equity", "bvps", "pb", "pe", "roe", "debt_to_equity", "p_revenue"]
    r = rows(t, "quarters")
    i = t["quarters"]["periods"].index("2025-Q4")
    assert r["debt_to_equity"][i] == "0.50" and r["p_revenue"][i] == "0.44"  # (300 + 200) / 1000 ; 300 / 680


def test_a_bank_s_checks_compare_four_quarters_with_the_year_and_with_vnstock():
    years = {**FIN_RECORD["years"], "2025": fin(164, npat_parent=200)}  # 41 + 42 + 43 + 44 = 170, not 200
    t = statement_table({**FIN_RECORD, "years": years}, closes=CLOSES, vnstock={"2025-Q2": {"npat": str(30 * B)}}, kind="bank")
    assert {(c["period"], c["check"]) for c in t["checks"]} >= {("2025", "npat_parent"), ("2025-Q2", "vnstock_npat")}


def ins(npat, **more):
    """An insurer's period in tỷ đồng whose parts add up to its profit before tax: 2 × npat from investments, the rest from insurance."""
    pbt = npat * 1.25
    base = {"npat_parent": npat, "pbt": pbt, "equity": 1000, "minority_equity": 10, "charter_capital": 100, "net_premium": 10 * npat,
            "fin_profit": 2 * npat, "other_ops": 0, "other_profit": 1, "associates_before": 2, "associates": 0, "ins_result": pbt - 2 * npat - 3,
            "cash": 50, "st_investments": 4000, "lt_investments": 5950}
    base.update(more)
    return {k: str(Decimal(str(v)) * B) for k, v in base.items()}


INS_RECORD = {**FIN_RECORD, "kind": "insurance", "quarters": {f"{y}-Q{k}": ins(20 * (y - 2023) + k) for y in (2024, 2025) for k in (1, 2, 3, 4)},
              "years": {"2024": ins(84, equity=900), "2025": ins(164)}}


def test_an_insurer_gets_premium_and_investment_multiples_and_where_its_profit_comes_from():
    t = statement_table(INS_RECORD, closes=CLOSES, vnstock=None, kind="insurance")
    assert [r["key"] for r in t["quarters"]["rows"][1:]] == ["market_cap", "parent_equity", "bvps", "pb", "pe", "roe", "p_premium",
                                                             "investments_to_equity", "ins_result", "fin_profit"]
    labels = {r["key"]: r["label"] for r in t["quarters"]["rows"]}
    assert labels["ins_result"] == "Kết quả kinh doanh bảo hiểm (4 quý)"
    assert {r["key"]: r["label"] for r in t["years"]["rows"]}["ins_result"] == "Kết quả kinh doanh bảo hiểm"
    r = rows(t, "quarters")
    i = t["quarters"]["periods"].index("2025-Q4")
    assert r["p_premium"][i] == "0.18" and r["investments_to_equity"][i] == "10.00"  # 300 / 1700 ; (50 + 4000 + 5950) / 1000
    assert r["fin_profit"][i] == "340000000000" and r["ins_result"][i] == "-139500000000"  # 2 × 170 ; 212.5 − 340 − 4 × 3
    assert not [c for c in t["checks"] if c["check"] == "ins_reconcile"]  # every period adds up


def test_an_insurer_s_result_is_left_blank_where_its_parts_do_not_add_up_to_profit_before_tax():
    quarters = {**INS_RECORD["quarters"], "2025-Q2": ins(42, ins_result=-200)}  # an older layout: the parts miss the profit before tax
    t = statement_table({**INS_RECORD, "quarters": quarters}, closes=CLOSES, vnstock=None, kind="insurance")
    r = rows(t, "quarters")
    assert r["ins_result"][t["quarters"]["periods"].index("2025-Q4")] is None and r["fin_profit"][t["quarters"]["periods"].index("2025-Q4")] is not None
    assert r["ins_result"][t["quarters"]["periods"].index("2025-Q1")] is not None
    assert ("2025-Q2", "ins_reconcile") in {(c["period"], c["check"]) for c in t["checks"]}


def test_every_kind_gets_its_multiples_at_the_latest_close_from_the_quarter_end_market_value():
    quarters = {p: {"npat_parent": str(2 * B), "equity": str(50 * B), "charter_capital": str(5 * B)} for p in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3")}
    record = {**RECORD, "quarters": quarters, "years": {}, "year_end_close": {}, "quarter_end_close": {"2026-Q3": {"date": "2026-09-30", "close": "30"}}}
    # 500,000 shares × 30,000 đ = 15 tỷ at the quarter's end; the price has since fallen by a third: 10 tỷ, on 8 tỷ profit and 50 tỷ equity.
    closes = [(datetime(2026, 9, 30), 30.0), (datetime(2026, 11, 6), 20.0)]
    t = statement_table(record, closes=closes, vnstock=None, kind="bank")
    assert t["current"] == {"pe": "1.25", "pb": "0.20", "market_cap": "10000000000", "close_date": "2026-11-06", "shares_from_vndirect": False} and t["summary"] is None
    # A bonus issue after the quarter: the adjusted series has the quarter's close at half, so the market value has not moved.
    t = statement_table(record, closes=[(datetime(2026, 9, 30), 15.0), (datetime(2026, 11, 6), 15.0)], vnstock=None, kind="bank")
    assert t["current"]["pb"] == "0.30"
    # No close on the quarter's last session: left blank, not worked out some other way.
    t = statement_table(record, closes=[(datetime(2026, 11, 6), 20.0)], vnstock=None, kind="bank")
    assert t["current"] == {"pe": None, "pb": None, "market_cap": None, "close_date": "2026-11-06", "shares_from_vndirect": False}
    assert statement_table(record, closes=[], vnstock=None, kind="bank")["current"] == {"pe": None, "pb": None, "market_cap": None, "close_date": None, "shares_from_vndirect": False}


def test_roic_is_core_profit_after_the_effective_tax_over_average_invested_capital():
    s = statement_table(RECORD, closes=CLOSES, vnstock=None)["summary"]
    # Core profit of the four quarters of 2025: gross 42 + 44 + 46 + 48, less 15 a quarter = 120; tax 42,5 on 212,5 = 20%: 96.
    # Invested capital at both ends: equity 1000 (minority included) + borrowings 500 - cash and short-term investments 100 = 1400.
    assert s["roic"] == "0.0686"
    missing = {p: f for p, f in QUARTERS.items() if p != "2024-Q4"}  # no balance sheet a year before: no average, no figure
    assert statement_table({**RECORD, "quarters": missing}, closes=CLOSES, vnstock=None)["summary"]["roic"] is None
    odd = {p: {**f, "tax": str(900 * B)} for p, f in QUARTERS.items()}  # tax above the profit is no rate to use
    assert statement_table({**RECORD, "quarters": odd}, closes=CLOSES, vnstock=None)["summary"]["roic"] is None
    loss = {p: {**f, "pbt": str(-1 * B)} for p, f in QUARTERS.items()}  # no effective tax rate from a loss
    assert statement_table({**RECORD, "quarters": loss}, closes=CLOSES, vnstock=None)["summary"]["roic"] is None


def test_vndirects_current_shares_replace_the_quarter_end_count_only_when_the_market_value_is_more_than_a_tenth_away():
    quarters = {p: {"npat_parent": str(2 * B), "equity": str(50 * B), "charter_capital": str(5 * B)} for p in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3")}
    record = {**RECORD, "quarters": quarters, "years": {}, "year_end_close": {}, "quarter_end_close": {"2026-Q3": {"date": "2026-09-30", "close": "20"}}}
    closes = [(datetime(2026, 9, 30), 20.0), (datetime(2026, 11, 6), 20.0)]  # 500,000 shares at 20,000 đ = 10 tỷ; shares issued later left the adjusted series alone
    t = statement_table(record, closes=closes, vnstock=None, kind="bank", check={"market_cap": str(18 * B), "shares": "900000"})
    assert t["current"] == {"pe": "2.25", "pb": "0.36", "market_cap": "18000000000", "close_date": "2026-11-06", "shares_from_vndirect": True}  # 900,000 × 20,000 đ
    near = statement_table(record, closes=closes, vnstock=None, kind="bank", check={"market_cap": str(10.5 * B), "shares": "900000"})["current"]
    assert near["market_cap"] == "10000000000" and near["shares_from_vndirect"] is False  # within a tenth: the differences are expected
    none = statement_table(record, closes=closes, vnstock=None, kind="bank", check={"market_cap": str(18 * B), "shares": None})["current"]
    assert none["market_cap"] == "10000000000" and none["shares_from_vndirect"] is False  # nothing to use instead: left as worked out, and the comparison shows it
    general = statement_table({**RECORD, "quarters": {p: {**f, "charter_capital": str(100 * B)} for p, f in QUARTERS.items()}, "quarter_end_close": {"2025-Q4": {"date": "2025-12-31", "close": "30"}}},
                              closes=CLOSES, vnstock=None, check={"market_cap": str(500 * B), "shares": "20000000"})
    assert general["summary"]["market_cap"] == "500000000000" and general["summary"]["shares_from_vndirect"] is True  # the cards follow: 20 million × 25,000 đ

