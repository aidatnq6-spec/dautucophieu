from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.gold_moves import drawdown, pass_through

D = Decimal


def days(start: date, values: list[str]) -> list[tuple[date, Decimal]]:
    return [(start + timedelta(days=i), D(v)) for i, v in enumerate(values)]


def test_drawdown_is_the_latest_against_the_highest_since_the_first_figure():
    r = drawdown(days(date(2026, 1, 1), ["100", "120", "90", "96"]), today=date(2026, 1, 4), max_age_days=7)
    assert r == {"since": "2026-01-01", "peak": "120", "peak_date": "2026-01-02", "latest": "96", "latest_date": "2026-01-04",
                 "change": "-0.2000", "stale": False, "missing": None}


def test_a_new_high_is_no_drawdown_and_an_old_figure_is_marked_stale():
    r = drawdown(days(date(2026, 1, 1), ["100", "120"]), today=date(2026, 1, 20), max_age_days=7)
    assert (r["change"], r["peak_date"], r["stale"]) == ("0.0000", "2026-01-02", True)


def test_no_figure_says_so():
    assert drawdown([], today=date(2026, 1, 1), max_age_days=7) == {"since": None, "peak": None, "peak_date": None, "latest": None,
                                                                    "latest_date": None, "change": None, "stale": False, "missing": "no_data"}


# world price in đồng a chỉ = XAU (USD/oz) × USD/VND × 3.75 / 31.1034768 (as the SJC gap)
def test_pass_through_compares_sjc_with_the_world_price_in_dong_over_thirty_days():
    start = date(2026, 11, 1)
    sjc = [(start, D("15000000")), (start + timedelta(days=31), D("14000000"))]
    xau = [(start, D("4000")), (start + timedelta(days=31), D("3600"))]
    fx = [(start - timedelta(days=1), D("26000")), (start + timedelta(days=30), D("26000"))]
    r = pass_through(sjc, xau, fx, today=start + timedelta(days=31))
    assert (r["from"], r["to"], r["days"], r["missing"]) == ("2026-11-01", "2026-12-02", 31, None)
    assert (r["sjc_change"], r["world_change"]) == ("-0.0667", "-0.1000")
    assert r["world_from"] == str((D("4000") * D("26000") * D("3.75") / D("31.1034768")).quantize(D("1")))


def test_pass_through_waits_for_thirty_days_of_both_and_says_when():
    start = date(2026, 11, 14)
    sjc = days(start, ["15000000"] * 7)
    xau = days(start + timedelta(days=2), ["4000"] * 5)
    fx = days(date(2026, 10, 25), ["26000"] * 27)
    r = pass_through(sjc, xau, fx, today=date(2026, 11, 20))
    assert r == {"missing": "not_enough_history", "since": "2026-11-16", "ready_on": "2026-12-16", "days": None, "from": None, "to": None,
                 "sjc_from": None, "sjc_to": None, "world_from": None, "world_to": None, "sjc_change": None, "world_change": None}


def test_a_day_without_a_recent_exchange_rate_is_left_out():
    start = date(2026, 11, 1)
    sjc = [(start, D("15000000")), (start + timedelta(days=31), D("14000000"))]
    xau = [(start, D("4000")), (start + timedelta(days=31), D("3600"))]
    fx = [(start - timedelta(days=10), D("26000"))]  # older than 7 days on both days
    assert pass_through(sjc, xau, fx, today=start + timedelta(days=31))["missing"] == "no_data"
