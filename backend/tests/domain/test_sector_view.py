from investment_agent.domain.sector_view import heatmap, sector_key, valuation

B = 10**9


def q(**values) -> dict:
    return {k: str(v * B) for k, v in values.items()}


def test_sector_keys_are_plain_ascii():
    assert sector_key("Bất động sản") == "bat-dong-san"
    assert sector_key("Điện, nước & xăng dầu khí đốt") == "dien-nuoc-xang-dau-khi-dot"


def test_heatmap_cells_compare_each_quarter_with_the_same_quarter_a_year_before():
    a = {"2025-Q3": q(npat_parent=100, cfo=10, st_debt=100, lt_debt=0), "2026-Q3": q(npat_parent=150, cfo=-20, st_debt=50, lt_debt=0)}
    b = {"2025-Q3": q(npat_parent=-10, cfo=5, st_debt=10, lt_debt=10), "2026-Q3": q(npat_parent=30, cfo=8)}  # no borrowing lines this quarter
    view = heatmap({"AAA": a, "BBB": b}, n=1)
    assert view["quarters"] == ["2026-Q3"]
    cell = {r["symbol"]: r["cells"][0] for r in view["rows"]}
    assert cell["AAA"] == {"quarter": "2026-Q3", "profit_yoy": "0.5000", "profit_turn": None, "cfo": str(-20 * B), "debt_yoy": "-0.5000"}
    assert cell["BBB"]["profit_yoy"] is None and cell["BBB"]["profit_turn"] == "to_profit" and cell["BBB"]["debt_yoy"] is None
    total = view["total"][0]
    assert total["profit_yoy"] == "0.5000" and total["profit_count"] == 1  # BBB's year-ago loss cannot be a base
    assert total["cfo"] == str(-12 * B) and total["cfo_count"] == 2 and total["debt_yoy"] == "-0.5000" and total["debt_count"] == 1


def test_heatmap_marks_a_turn_to_loss_and_leaves_missing_quarters_blank():
    view = heatmap({"AAA": {"2025-Q3": q(npat_parent=40), "2026-Q3": q(npat_parent=-5), "2026-Q2": q(npat_parent=1)}}, n=2)
    cells = view["rows"][0]["cells"]
    assert [c["quarter"] for c in cells] == ["2026-Q2", "2026-Q3"]
    assert cells[0]["profit_yoy"] is None and cells[0]["profit_turn"] is None  # no 2025-Q2
    assert cells[1]["profit_turn"] == "to_loss"


def months(values: list) -> list[tuple[str, str | None]]:
    out, y, m = [], 2021, 1
    for v in values:
        out.append((f"{y}-{m:02d}", None if v is None else str(v)))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_sector_median_pb_each_month_needs_three_tickers_and_finds_how_long_it_has_not_been_this_low():
    a = months([2.0] * 10 + [1.0, 0.9])
    b = months([3.0] * 10 + [1.2, 1.1])
    c = months([1.5] * 10 + [0.7, 0.8])
    d = months([None] * 11 + [5.0])  # one month only
    view = valuation({"AAA": a, "BBB": b, "CCC": c, "DDD": d})
    assert view["median"][0] == {"month": "2021-01", "value": "2.00", "count": 3}
    now = view["now"]
    assert now["month"] == "2021-12" and now["value"] == "1.00" and now["count"] == 4  # median of 0.9, 1.1, 0.8, 5.0
    assert now["lowest_since"] is None and now["rank"] == "0.0000"  # the lowest month on record so far


def test_each_ticker_against_the_sector_median_and_its_own_five_year_low():
    a = months([2.0] * 30 + [0.8])
    b = months([1.0] * 31)
    c = months([3.0] * 31)
    view = valuation({"AAA": a, "BBB": b, "CCC": c})
    t = {r["symbol"]: r for r in view["tickers"]}
    assert t["AAA"]["pb"] == "0.80" and t["AAA"]["to_median"] == "0.8000" and t["AAA"]["below_own_low"] is True and t["AAA"]["own_low"] == "2.00"
    assert t["BBB"]["below_own_low"] is True  # equal to its lowest counts as at the low
    assert t["CCC"]["to_median"] == "3.0000" and [r["symbol"] for r in view["tickers"]] == ["AAA", "BBB", "CCC"]  # cheapest against the median first
