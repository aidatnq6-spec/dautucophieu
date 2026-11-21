"""Trạng thái vĩ mô 2×2 (owner, 21/11/2026): two yes/no conditions, each known on a day only once its figure was out (a month's
CPI, industrial production and exports from the 10th of the next month, the month's average USD/VND from the 1st, FRED's daily figures
the next day), and VN-Index some sessions later in each of the four combinations."""

from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.history_states import CONDITIONS, condition_days, states_table

D = Decimal


def months(values, start=(2015, 1)):
    from calendar import monthrange
    y, m, out = start[0], start[1], []
    for v in values:
        out.append((date(y, m, monthrange(y, m)[1]), D(v)))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_a_months_cpi_counts_only_from_the_tenth_of_the_next_month():
    cpi = months(["3", "3", "3", "4"])                        # April 2015 is higher than January
    known = condition_days("cpi_up", {"wb_vn_cpi_yoy": cpi}, fx=D("0.01"))
    assert known == [(date(2015, 5, 10), True)]                 # April's figure, out on 10 May


def test_the_usd_vnd_condition_follows_the_chosen_threshold():
    fx = months(["21000", "21000", "21000", "21400"])         # +1.9% in three months
    assert condition_days("fx_up", {"wb_vn_usdvnd": fx}, fx=D("0.01")) == [(date(2015, 5, 1), True)]
    assert condition_days("fx_up", {"wb_vn_usdvnd": fx}, fx=D("0.02")) == [(date(2015, 5, 1), False)]


def test_a_daily_series_compares_with_three_months_before_and_counts_from_the_next_day():
    days = [date(2020, 1, 1) + timedelta(days=i) for i in range(120)]
    oil = [(d, D(50) if i < 100 else D(60)) for i, d in enumerate(days)]
    known = dict(condition_days("oil_up", {"factor_oil": oil}, fx=D("0.01")))
    assert known[date(2020, 4, 2)] is False and known[date(2020, 4, 11)] is True   # 10 April's 60 against 50, from 11 April


def test_the_four_combinations_and_today():
    days = [date(2020, 1, 1) + timedelta(days=i) for i in range(400)]
    closes = [(d, D(1000 + i)) for i, d in enumerate(days)]
    a = [(d, i % 2 == 0) for i, d in enumerate(days)]
    b = [(d, i % 4 < 2) for i, d in enumerate(days)]
    out = states_table(a, b, closes, h=20)
    assert [r["a"] for r in out["rows"]] == [True, True, False, False] and [r["b"] for r in out["rows"]] == [True, False, True, False]
    assert sum(r["n"] for r in out["rows"]) == out["all"]["n"] == 380   # the last 20 sessions have no later figure yet
    assert out["today"] == {"a": False, "b": False}                    # day 399: odd, so not A; 399 % 4 = 3, so not B


def test_today_is_only_said_when_both_states_are_known_on_the_latest_session():
    days = [date(2020, 1, 1) + timedelta(days=i) for i in range(200)]
    closes = [(d, D(1000 + i)) for i, d in enumerate(days)]
    a = [(d, True) for d in days]
    b = [(days[0], True)]                                    # known once, then never again: stale after 10 days (daily)
    assert states_table(a, b, closes, h=20)["today"] is None


def test_a_months_figure_stands_for_130_days_the_world_banks_lag():
    """The World Bank's figures run about four months behind: July's, known on 10 August, still stands on 18 November."""
    from investment_agent.domain.history_states import STALE
    assert STALE["monthly"] == timedelta(days=130)


def test_conditions_are_named_in_vietnamese():
    assert set(CONDITIONS) == {"cpi_up", "fx_up", "iip_up", "exports_up", "oil_up", "usd_up", "us10y_up", "pe_high"}
    assert all(CONDITIONS[k]["label"] for k in CONDITIONS)
