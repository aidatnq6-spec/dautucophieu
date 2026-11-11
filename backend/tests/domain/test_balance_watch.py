from investment_agent.domain.balance_watch import borrowing_flag, net_debt_rows, property_cash, sector_debt

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
