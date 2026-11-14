from decimal import Decimal

from investment_agent.domain.watch_quadrant import MIN_MONTHS, quadrant


def months(n, start=2020):
    return [f"{start + i // 12}-{i % 12 + 1:02d}" for i in range(n)]


def pb(values):
    return [(m, str(v)) for m, v in zip(months(len(values)), values)]


def quarters(*profits):
    return {f"{2024 + i // 4}-Q{i % 4 + 1}": {"npat_parent": str(p)} for i, p in enumerate(profits)}


def test_each_ticker_is_placed_by_its_p_b_against_its_own_past_and_its_profit_growth():
    cheap = pb([2.0] * 30 + [1.0])                     # lowest month so far
    dear = pb([1.0] * 30 + [3.0])
    out = quadrant({"AAA": {"pb": cheap, "quarters": quarters(10, 10, 10, 10, 12, 12, 12, 12)},
                    "BBB": {"pb": dear, "quarters": quarters(10, 10, 10, 10, 8, 8, 8, 8)}}, held={"AAA": Decimal(600), "CCC": Decimal(400)})
    points = {p["symbol"]: p for p in out["points"]}
    assert points["AAA"] == {"symbol": "AAA", "pb": "1", "cheaper_months": "0", "months": 31, "growth": "0.2", "quarter": "2025-Q4",
                             "held": "600", "zone": "cheap_growing"}
    assert points["BBB"]["cheaper_months"] == "1" and points["BBB"]["growth"] == "-0.2" and points["BBB"]["zone"] == "dear_shrinking"
    assert points["BBB"]["held"] is None


def test_a_ticker_short_of_history_or_with_a_loss_to_grow_from_is_listed_not_drawn():
    out = quadrant({"NEW": {"pb": pb([1.0] * (MIN_MONTHS - 1)), "quarters": quarters(1, 1, 1, 1, 2, 2, 2, 2)},
                    "LOSS": {"pb": pb([1.0] * 30), "quarters": quarters(-1, -1, -1, -1, 2, 2, 2, 2)},
                    "FEW": {"pb": pb([1.0] * 30), "quarters": quarters(1, 1, 1)}}, held={})
    assert out["points"] == []
    assert out["missing"] == {"FEW": "chưa đủ 8 quý lợi nhuận", "LOSS": "4 quý trước lỗ: không tính được tăng trưởng",
                              "NEW": f"chưa đủ {MIN_MONTHS} tháng P/B"}
