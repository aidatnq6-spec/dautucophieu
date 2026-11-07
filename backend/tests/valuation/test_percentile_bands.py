from datetime import date, timedelta

from investment_agent.valuation.bands import MIN_WEEKS, percentile, percentile_bands


def weekly(values, end=date(2026, 11, 6), basis="năm"):
    """One point per week ending on `end`, oldest first."""
    n = len(values)
    return [{"date": (end - timedelta(weeks=n - 1 - i)).isoformat(), "value": v, "basis": basis} for i, v in enumerate(values)]


def test_percentile_interpolates_between_the_two_nearest_values():
    from decimal import Decimal
    xs = [Decimal(v) for v in ("1", "2", "3", "4", "5")]
    assert percentile(xs, 50) == Decimal("3") and percentile(xs, 10) == Decimal("1.4") and percentile(xs, 95) == Decimal("4.8")


def test_each_window_gives_percentiles_mean_spread_and_where_today_stands():
    values = [str(1 + (i % 10) / 10) for i in range(5 * 52 + 10)]  # 1.0 … 1.9 repeating, more than five years
    values[-1] = "1.25"
    out = percentile_bands(weekly(values))
    assert out["current"] == "1.25" and out["date"] == "2026-11-06" and out["reason"] is None
    three, five, whole = out["windows"]
    assert [w["label"] for w in out["windows"]] == ["3 năm", "5 năm", "Toàn bộ"]
    assert three["weeks"] == 157 and three["from"] == "2023-11-10" and three["reason"] is None
    assert whole["weeks"] == len(values) and whole["from"] == weekly(values)[0]["date"]
    assert three["p"]["p50"] == "1.50" and three["p"]["p10"] == "1.10" and three["p"]["p70"] == "1.62" and three["p"]["p95"] == "1.90"
    assert three["min"] == "1.00" and three["max"] == "1.90"
    assert three["rank"] == 29  # share of weeks at or below today's 1.25, in whole percent
    assert three["mean"] == "1.45" and three["skew"] == "-0.01" and three["z"] == "-0.71"  # checked with numpy
    assert three["bases"] == {"năm": 157}


def test_a_window_longer_than_the_series_is_not_drawn():
    out = percentile_bands(weekly(["2"] * 100 + ["3"] * 100))
    three, five, whole = out["windows"]
    assert three["reason"] is None and three["weeks"] == 157
    assert five["reason"] == "Chuỗi chỉ có từ 01/2023, chưa đủ 5 năm" and five["p"] is None
    assert whole["weeks"] == 200


def test_too_few_weeks_with_a_value_give_a_reason_and_losses_are_counted_not_used():
    values = [None] * (3 * 52) + ["10"] * (MIN_WEEKS - 1)
    out = percentile_bands(weekly(values))
    three = out["windows"][0]
    assert three["reason"] == f"Chỉ có {MIN_WEEKS - 1} tuần có số, cần ít nhất {MIN_WEEKS}" and three["empty_weeks"] == 106


def test_a_flat_series_has_no_z_or_skew_and_a_loss_today_has_no_rank():
    out = percentile_bands(weekly(["2"] * 200))
    assert out["windows"][0]["z"] is None and out["windows"][0]["skew"] is None and out["windows"][0]["rank"] == 100
    out = percentile_bands(weekly(["2"] * 199 + [None]))
    assert out["current"] is None and out["windows"][0]["rank"] is None and out["windows"][0]["p"]["p50"] == "2.00"


def test_no_points_give_a_reason():
    assert percentile_bands([]) == {"current": None, "date": None, "windows": [], "reason": "Chưa có chuỗi theo tuần"}
