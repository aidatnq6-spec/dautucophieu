"""Hiệu suất theo kỳ on Chuỗi giá trị (owner, 21/11/2026): each chain's members moved over a week, a month, three months, a year and
since the year began, averaged with equal weight over the members that have the figure (the count is shown), with today's breadth,
where the members sit in their 52-week range and the strongest member over a month. Closes only; nothing is estimated."""

from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.chain_returns import chain_returns, period_change

D = Decimal
LAST = date(2026, 11, 20)


def daily(start_value, step, days=400, end=LAST):
    """One close a calendar day, ending at end: start_value + step per day."""
    return [(end - timedelta(days=days - 1 - i), D(start_value) + D(step) * i) for i in range(days)]


def test_a_change_is_the_last_close_against_the_last_close_on_or_before_the_start():
    closes = [(date(2026, 10, 20), D("10")), (date(2026, 11, 13), D("11")), (LAST, D("12"))]
    assert period_change(closes, days=7) == D("12") / D("11") - 1
    assert period_change(closes, days=31) == D("12") / D("10") - 1
    assert period_change(closes, days=365) is None  # history too short: not a year
    assert period_change(closes, ytd=True) is None   # no close of last year stored
    assert period_change([(date(2025, 12, 31), D("8")), *closes], ytd=True) == D("12") / D("8") - 1


def test_a_chain_averages_its_members_with_equal_weight_and_counts_them():
    chains = [{"id": "steel", "name": "Thép", "symbols": ["AAA", "BBB", "CCC"]}]
    closes = {"AAA": daily("100", "0.1"), "BBB": daily("100", "-0.1"), "CCC": []}
    (row,) = chain_returns(chains, closes, today=LAST)
    assert row["id"] == "steel" and row["members"] == 3 and row["priced"] == 2 and row["no_data"] == ["CCC"]
    w1 = row["periods"]["w1"]
    expected = ((D("100") + D("0.1") * 399) / (D("100") + D("0.1") * 392) - 1 + (D("100") - D("0.1") * 399) / (D("100") - D("0.1") * 392) - 1) / 2
    assert w1["n"] == 2 and w1["change"] == format(expected.quantize(D("0.0001")), "f")
    assert row["breadth"] == {"up": 1, "down": 1, "flat": 0}
    assert row["leader"]["symbol"] == "AAA"
    assert row["position_52w"] == "0.50"  # AAA at the top of its year, BBB at the bottom: the middle of the two


def test_a_member_whose_last_close_is_old_is_left_out_and_named():
    chains = [{"id": "x", "name": "X", "symbols": ["AAA", "OLD"]}]
    closes = {"AAA": daily("100", "0.1"), "OLD": daily("100", "0.1", end=LAST - timedelta(days=30))}
    (row,) = chain_returns(chains, closes, today=LAST)
    assert row["priced"] == 1 and row["stale"] == ["OLD"]
