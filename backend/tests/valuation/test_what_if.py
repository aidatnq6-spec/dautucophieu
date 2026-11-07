from datetime import date, timedelta
from decimal import Decimal

from investment_agent.valuation.what_if import MIN_EPISODES, episodes, what_if


def series(values, closes=None, end=date(2026, 11, 6), basis="quý", period="2026-Q2", denominator="10000000000"):
    """Weekly points ending on `end`; close defaults to value × 10,000 đồng (1,000,000 shares over 10e9 equity)."""
    n = len(values)
    closes = closes or [None if v is None else str(int(Decimal(v) * 10000)) for v in values]
    return [{"date": (end - timedelta(weeks=n - 1 - i)).isoformat(), "close": c or "10000", "value": v, "basis": basis, "period": period,
             "denominator": denominator, "missing": []} for i, (v, c) in enumerate(zip(values, closes))]


def test_the_multiple_at_a_price_uses_the_latest_week_s_denominator_and_today_s_share_count():
    pts = series(["1.50"] * 200)
    out = what_if(pts, shares=1000000, price=Decimal(12000))
    assert out["multiple"] == "1.20" and out["close"] == "15000" and out["change"] == "-0.2000"
    assert out["per_share"] == "10000" and out["basis"] == "quý" and out["period"] == "2026-Q2"
    assert [w["label"] for w in out["windows"]] == ["3 năm", "5 năm", "Toàn bộ"]
    assert out["windows"][0]["rank"] == 0 and out["windows"][1]["reason"] == "Chuỗi chỉ có từ 01/2023, chưa đủ 5 năm"


def test_a_loss_or_negative_equity_gives_no_multiple():
    pts = series(["8.0"] * 60, denominator="-5000000000")
    out = what_if(pts, shares=1000000, price=Decimal(12000))
    assert out["multiple"] is None and out["windows"] == [] and out["reason"] == "Mẫu số không dương (lỗ hoặc vốn chủ âm): không có bội số"


def test_an_episode_starts_when_the_multiple_falls_to_the_level_and_is_judged_twelve_months_later():
    # 1.5 for a year, 1.0 for 8 weeks (entry 01/…), back to 1.5, then 2.0 a year after the entry.
    values = ["1.5"] * 52 + ["1.0"] * 8 + ["1.5"] * 44 + ["2.0"] * 60
    out = episodes(series(values), level=Decimal("1.1"))
    first = out["list"][0]
    assert first["entry"] == series(values)[52]["date"] and first["multiple"] == "1.00" and first["entry_close"] == "10000"
    assert first["exit"] == series(values)[105]["date"] and first["return"] == "1.0000"  # 10,000 → 20,000 on the first week a year on
    assert first["drawdown"] == "0.0000"
    assert out["done"] == 1 and out["pending"] == 0 and out["wins"] == 1
    assert out["win_rate"] is None and out["median"] is None and out["min_episodes"] == MIN_EPISODES  # one episode is not a sample


def test_a_new_episode_needs_the_multiple_back_above_the_level_and_a_year_since_the_last_entry():
    # Dips every 20 weeks: only the ones a year or more after the previous entry count, so the twelve-month results do not overlap.
    values = (["1.5"] * 19 + ["1.0"]) * 15
    out = episodes(series(values), level=Decimal("1.1"))
    entries = [date.fromisoformat(e["entry"]) for e in out["list"]]
    assert all((b - a).days >= 365 for a, b in zip(entries, entries[1:]))
    assert len(entries) == 5 and out["done"] == 4 and out["pending"] == 1
    assert out["list"][-1]["exit"] is None and out["list"][-1]["return"] is None


def test_enough_episodes_give_a_win_rate_median_worst_result_and_worst_fall():
    block = ["1.0"] + ["0.8"] * 10 + ["1.5"] * 42 + ["1.2"]  # entry 10,000; falls to 8,000; 53 weeks on (first week ≥ a year) 12,000
    values = ["1.5"] + block * 6 + ["1.5"] * 60
    out = episodes(series(values), level=Decimal("1.0"))
    assert out["done"] == 6 and out["wins"] == 6 and out["win_rate"] == "1.0000"
    assert out["median"] == "0.2000" and out["worst_drawdown"] == "-0.2000" and out["worst_return"] == "0.2000"


def test_a_loss_week_breaks_a_run_and_a_missing_year_on_close_leaves_the_episode_pending():
    values = ["1.5"] * 10 + ["1.0"] * 3 + [None] + ["1.0"] * 3 + ["1.5"] * 20
    out = episodes(series(values), level=Decimal("1.1"))
    assert len(out["list"]) == 1 and out["done"] == 0 and out["pending"] == 1  # the series ends before a year has passed


def test_a_series_that_starts_below_the_level_has_no_entry_until_it_has_been_above():
    values = ["1.0"] * 30 + ["1.5"] * 10 + ["1.0"] * 70
    out = episodes(series(values), level=Decimal("1.1"))
    assert [e["entry"] for e in out["list"]] == [series(values)[40]["date"]]  # the first weeks were already below: when they fell is unknown
