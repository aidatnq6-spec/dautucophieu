"""Dòng tiền & kỹ thuật on Theo dõi (owner, 21/11/2026): per watched ticker, volume against its 20-session average, where the close sits
in the session's range, foreign net and its run, 52-week high/low and MA20/MA50 on closes, with quick filters. Missing data is said,
never filled."""

from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.flow_board import FLAGS, flag_counts, stock_row

D = Decimal
LAST = date(2026, 11, 20)


def sessions(n, end=LAST):
    """n weekdays ending at end, oldest first."""
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


def closes_of(values, end=LAST):
    return list(zip(sessions(len(values), end), [D(v) for v in values]))


def bars_of(volumes, high="11", low="9", close="10.5"):
    return [(d, D(high) * 1000, D(low) * 1000, D(close) * 1000, v) for d, v in zip(sessions(len(volumes)), volumes)]


def test_volume_against_its_20_session_average_and_the_close_in_the_range():
    row = stock_row("AAA", closes=closes_of(["10"] * 299 + ["10.5"]), bars=bars_of([1000] * 20 + [2500]), foreign=[], held=False)
    assert row["close"] == "10500" and row["pct"] == "0.0500" and row["date"] == "2026-11-20"
    assert row["volume"] == 2500 and row["volume_ratio"] == "2.50" and row["range_position"] == "0.75"  # (10.5 − 9) / (11 − 9)
    assert "volume_spike" in row["flags"]


def test_too_few_sessions_say_so_instead_of_guessing():
    row = stock_row("AAA", closes=closes_of(["10"] * 30), bars=bars_of([1000] * 10), foreign=[], held=False)
    assert row["volume_ratio"] is None and row["high_52w"] is None and row["ma50"] is None
    assert set(row["missing"]) == {"volume_20", "52w", "ma50"}


def test_a_close_above_every_close_of_the_past_52_weeks_is_a_new_high():
    values = ["10"] * 250 + ["12"] + ["11"] * 48 + ["12.5"]
    row = stock_row("AAA", closes=closes_of(values), bars=[], foreign=[], held=False)
    assert row["high_52w"] == "12000" and row["low_52w"] == "10000" and "new_high" in row["flags"] and "new_low" not in row["flags"]


def test_crossing_the_20_and_50_session_averages():
    up = stock_row("AAA", closes=closes_of(["10"] * 299 + ["11"]), bars=[], foreign=[], held=False)
    assert {"cross_up_ma20", "cross_up_ma50"} <= set(up["flags"]) and up["ma20"] == "10050"  # (19 × 10 + 11) / 20
    down = stock_row("AAA", closes=closes_of(["10"] * 299 + ["9"]), bars=[], foreign=[], held=False)
    assert {"cross_down_ma20", "cross_down_ma50", "new_low"} <= set(down["flags"])


def test_the_foreign_run_counts_sessions_in_a_row_of_the_same_side():
    days = sessions(7)
    foreign = list(zip(days, [D("-1"), D("2"), D("0.5"), D("1"), D("3"), D("0.2"), D("1.5")]))
    row = stock_row("AAA", closes=closes_of(["10"] * 300), bars=[], foreign=foreign, held=True)
    assert row["foreign_net_bn"] == "1.5" and row["foreign_run"] == 6 and "foreign_buy_5" in row["flags"] and row["held"] is True
    sold = stock_row("AAA", closes=closes_of(["10"] * 300), bars=[], foreign=list(zip(days, [D("-1")] * 7)), held=False)
    assert sold["foreign_run"] == -7 and "foreign_sell_5" in sold["flags"]


def test_foreign_from_another_day_than_the_last_close_is_not_shown_as_today():
    old = [(date(2026, 11, 19), D("2"))]
    row = stock_row("AAA", closes=closes_of(["10"] * 300), bars=[], foreign=old, held=False)
    assert row["foreign_net_bn"] is None and row["foreign_run"] is None


def test_counts_per_filter():
    rows = [{"flags": ["new_high", "volume_spike"]}, {"flags": ["new_high"]}, {"flags": []}]
    counts = flag_counts(rows)
    assert counts["new_high"] == 2 and counts["volume_spike"] == 1 and counts["new_low"] == 0 and set(counts) == set(FLAGS)
