"""Thống kê lịch sử (owner, 21/11/2026): VN-Index H sessions later, grouped by a state known on the day: P/E against its own five
years, and the macro lights' levels. Every group says its samples and how many of them do not overlap (days at least H sessions
apart), and its t-statistic stands on those alone: overlapping windows are not independent."""

from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.history_stats import forward_returns, group_summary, independent, pe_groups

D = Decimal


def sessions(values, start=date(2018, 1, 1)):
    return [(start + timedelta(days=i), D(v)) for i, v in enumerate(values)]


def test_the_change_h_sessions_later_and_none_past_the_end():
    closes = sessions(["100", "110", "121", "100"])
    assert forward_returns(closes, 2) == {date(2018, 1, 1): D("0.21"), date(2018, 1, 2): D("100") / D("110") - 1}


def test_only_days_at_least_h_sessions_apart_count_as_independent():
    index = {date(2018, 1, 1) + timedelta(days=i): i for i in range(10)}
    days = [date(2018, 1, 1) + timedelta(days=i) for i in (0, 1, 2, 5, 6, 9)]
    assert independent(days, index, h=3) == [days[0], days[3], days[5]]  # 0, then 5 (≥ 0+3), then 9 (≥ 5+3)


def test_a_group_says_its_samples_the_independent_ones_and_a_t_on_those_alone():
    index = {date(2018, 1, 1) + timedelta(days=i): i for i in range(40)}
    returns = {d: D("0.10") if i % 2 == 0 else D("-0.02") for d, i in index.items()}
    out = group_summary(list(index), returns, index, h=10)
    assert out["n"] == 40 and out["n_independent"] == 4 and out["win_rate"] == "0.5000"
    assert out["mean"] == "0.0400" and out["t"] is None  # the four independent days all gained 10%: no spread, no t
    assert group_summary([], returns, index, h=10) == {"n": 0, "n_independent": 0, "mean": None, "median": None, "win_rate": None, "t": None}


def test_a_lights_past_levels_are_worked_out_as_the_light_does_and_each_session_takes_the_level_known_that_day():
    """Kiểm tra ngưỡng đèn: oil's 30-day rise is green under 10%, yellow from 10%, red from 20% (domain.macro_signals)."""
    from investment_agent.domain.history_stats import light_groups
    days = [date(2018, 1, 1) + timedelta(days=i) for i in range(200)]
    oil = [(d, D(50) if i < 100 else D(65)) for i, d in enumerate(days)]       # +30% on day 100: red for thirty days, then flat
    closes = [(d, D(1000 + i)) for i, d in enumerate(days)]
    out = light_groups("oil", {"factor_oil": oil}, closes, h=10)
    by = {g["level"]: g for g in out["groups"]}
    assert by["red"]["n"] == 30 and by["green"]["n"] > 100 and by["yellow"]["n"] == 0
    assert out["name"] == "Giá dầu WTI" and out["today"] == "green" and out["from"] == "2018-01-31"


def test_pe_days_fall_in_five_groups_by_where_they_sat_in_the_five_years_before():
    days = [date(2018, 1, 1) + timedelta(days=i) for i in range(700)]
    pe = [(d, D(10 + (i % 50) / 10)) for i, d in enumerate(days)]          # 10.0 … 14.9 over and over
    closes = [(d, D(1000 + i)) for i, d in enumerate(days)]
    out = pe_groups(pe, closes, h=20)
    assert [g["bucket"] for g in out["groups"]] == [0, 1, 2, 3, 4]
    assert sum(g["n"] for g in out["groups"]) < 700                         # the first 250 days have no five-year place yet
    assert out["today"]["bucket"] in range(5) and out["today"]["pe"] == "14.90"
    assert all(g["pe_low"] is not None for g in out["groups"])
    assert out["trend"] is not None and {"slope", "intercept", "r2"} <= set(out["trend"])
