"""Lợi suất cần có để đạt đúng hạn (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-tu-do-tai-chinh-thuc-design.md): the yearly
rate that reaches the target on time, the year it is reached at a given rate, and the monthly contribution that reaches it on time."""

from datetime import date
from decimal import Decimal

from investment_agent.domain.required_return import contribution_for, months_at, months_until, required_return, yearly_growth

B = Decimal(10**9)


def test_the_rate_needed_is_solved_backwards_to_a_hundredth_of_a_point():
    # The VWA note: 3.1 tỷ, 700 tr a year, 12.5% a year: about 16–18 tỷ in 6 to 9 years
    at = months_at(capital=Decimal("3.1") * B, contribution=Decimal(700_000_000) / 12, goal=18 * B, yearly_pct=Decimal("12.5"))
    assert 6 * 12 <= at <= 9 * 12
    out = required_return(capital=Decimal("3.1") * B, contribution=Decimal(700_000_000) / 12, goal=18 * B, months=at)
    assert out["status"] == "ok" and Decimal("12.3") <= Decimal(out["rate"]) <= Decimal("12.5")


def test_already_there_not_feasible_and_no_time_are_said():
    assert required_return(capital=20 * B, contribution=Decimal(0), goal=18 * B, months=60)["status"] == "reached"
    assert required_return(capital=B, contribution=Decimal(0), goal=1000 * B, months=12)["status"] == "not_feasible"
    assert required_return(capital=B, contribution=Decimal(0), goal=18 * B, months=0)["status"] == "no_time"


def test_the_contribution_that_reaches_the_target_on_time():
    need = contribution_for(capital=Decimal("3.1") * B, goal=18 * B, yearly_pct=Decimal("11"), months=96)
    assert need is not None and need > Decimal(700_000_000) / 12  # at a lower rate it takes more than 700 tr a year
    assert contribution_for(capital=20 * B, goal=18 * B, yearly_pct=Decimal("11"), months=96) == 0


def test_months_until_the_end_of_the_target_year_and_the_yearly_growth_of_a_series():
    assert months_until(date(2035, 1, 1), date(2026, 11, 22)) == 9 * 12 + 1
    assert yearly_growth((date(2000, 7, 28), Decimal(100)), (date(2026, 11, 20), Decimal("1688.79"))) == "11.34"
    assert yearly_growth((date(2026, 1, 1), Decimal(100)), (date(2026, 1, 1), Decimal(110))) is None
