"""Định giá chuỗi so với 5 năm (owner, 21/11/2026): each chain's median P/E and P/B of its members week by week (each member priced
only with the reports already out that week), today's median against the five years before: the average and where today sits from
0% (cheapest) to 100% (dearest). The five-year figure is the median: a mean was dragged to P/E 1,987 by a year of tiny profits."""

from datetime import date, timedelta

from investment_agent.domain.chain_valuation import chain_valuation

TODAY = date(2026, 11, 21)


def weekly(values, end=date(2026, 11, 20)):
    """One point a week ending at `end`, oldest first."""
    return [{"date": (end - timedelta(weeks=len(values) - 1 - i)).isoformat(), "value": v} for i, v in enumerate(values)]


def test_today_is_placed_among_five_years_of_weekly_medians():
    history = [str(10 + (i % 10)) for i in range(270)]           # 10 … 19 over and over, more than five years
    members = {"AAA": {"pe": weekly(history[:-1] + ["11"]), "pb": weekly(["1.5"] * 270)},
               "BBB": {"pe": weekly(history[:-1] + ["11"]), "pb": weekly(["2.5"] * 270)}}
    (row,) = chain_valuation([{"id": "x", "name": "X", "symbols": ["AAA", "BBB", "CCC"]}], members, today=TODAY)
    assert row["members"] == 3 and row["priced"] == 2 and row["no_data"] == ["CCC"]
    assert row["pe"]["now"] == "11.00" and row["pe"]["median_5y"] == "14.00"  # the median of 5 years of weeks: a year of tiny profits cannot drag it
    assert row["pe"]["position"] == "0.20"  # 11 or less in two of each ten weeks
    assert row["pb"]["now"] == "2.00" and row["pb"]["position"] == "1.00" and row["since"] is None


def test_a_loss_gives_no_pe_and_a_short_history_is_said():
    members = {"AAA": {"pe": weekly(["-5"] * 60), "pb": weekly(["1.2"] * 60)}, "BBB": {"pe": weekly(["8"] * 60), "pb": weekly(["0.8"] * 60)}}
    (row,) = chain_valuation([{"id": "x", "name": "X", "symbols": ["AAA", "BBB"]}], members, today=TODAY)
    assert row["pe"]["now"] == "8.00" and row["pe"]["n"] == 1 and row["pb"]["n"] == 2
    assert row["since"] == (date(2026, 11, 20) - timedelta(weeks=59)).isoformat()  # less than five years stored


def test_a_member_without_a_recent_week_is_left_out_and_named():
    members = {"AAA": {"pe": weekly(["10"] * 300), "pb": weekly(["1"] * 300)},
               "OLD": {"pe": weekly(["50"] * 300, end=date(2026, 8, 1)), "pb": weekly(["9"] * 300, end=date(2026, 8, 1))}}
    (row,) = chain_valuation([{"id": "x", "name": "X", "symbols": ["AAA", "OLD"]}], members, today=TODAY)
    assert row["stale"] == ["OLD"] and row["pe"]["now"] == "10.00"
