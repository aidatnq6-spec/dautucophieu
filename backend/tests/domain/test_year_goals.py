"""Mục tiêu năm (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md): up to three goals, each set
against an even pace through the year, a comparison and never a forecast."""

from datetime import date

import pytest

from investment_agent.domain.year_goals import GoalError, goals_progress, pace, validate_goals


def test_goals_are_whole_dong_or_a_share_and_at_least_one_is_set():
    assert validate_goals({"contribution": "120000000", "savings_rate": "0.3", "total_assets": ""}) == {"contribution": "120000000", "savings_rate": "0.3"}
    for bad in ({}, {"contribution": "0"}, {"contribution": "1.5"}, {"contribution": "abc"}, {"savings_rate": "1"}, {"savings_rate": "-0.1"}):
        with pytest.raises(GoalError):
            validate_goals(bad)


def test_the_even_pace_is_the_share_of_the_years_days_gone():
    assert pace(2027, date(2026, 12, 31)) == 0 and pace(2027, date(2028, 1, 1)) == 1
    assert str(pace(2027, date(2027, 3, 31)).quantize(pace(2027, date(2027, 3, 31)).__class__("0.01"))) == "0.25"  # 90 of 365 days


def test_each_goal_reads_where_it_stands_and_more_than_ten_points_under_the_pace_is_behind():
    goals = {"contribution": "120000000", "savings_rate": "0.3", "total_assets": "2000000000"}
    out = goals_progress(goals, year=2027, today=date(2027, 7, 2), put_in="30000000", savings_rate="0.32", total_now="1600000000",
                         total_start="1500000000")
    by = {r["id"]: r for r in out["rows"]}
    assert out["pace"] == "0.5014"  # 2 July: 183 of 365 days
    assert by["contribution"]["share"] == "0.2500" and by["contribution"]["behind"] is True
    assert by["savings_rate"]["behind"] is False
    assert by["total_assets"]["share"] == "0.2000" and by["total_assets"]["behind"] is True  # 100 tr of the 500 tr from the start to the goal
    missing = goals_progress(goals, year=2027, today=date(2027, 7, 2), put_in=None, savings_rate=None, total_now="1600000000", total_start=None)
    assert all(r["behind"] is False for r in missing["rows"]) and {r["id"]: r["share"] for r in missing["rows"]}["total_assets"] is None


def test_a_total_assets_goal_under_the_start_gives_no_reading_never_a_negative_share():
    out = goals_progress({"total_assets": "1000000000"}, year=2027, today=date(2027, 7, 2), put_in=None, savings_rate=None,
                         total_now="1250000000", total_start="1200000000")
    row = out["rows"][0]
    assert row["share"] is None and row["behind"] is False and row["below_start"] is True
