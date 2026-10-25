from datetime import datetime, timedelta, timezone

import pytest

from investment_agent.market.indicators import ema, four_hourly, macd, macd_state, monthly, rsi, rsi_value, weekly

VN = timezone(timedelta(hours=7))


def test_ema_is_seeded_with_the_simple_average():
    assert ema([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4]


def test_macd_line_and_signal_compose_two_emas():
    line, signal = macd([1, 2, 3, 4, 5, 6], fast=2, slow=3, signal=2)
    assert line == [None, None, 0.5, 0.5, 0.5, 0.5] and signal == [None, None, None, 0.5, 0.5, 0.5]


def test_rsi_uses_wilder_smoothing_seeded_with_the_average():
    assert rsi([1, 2, 1, 2], n=2) == [None, None, 50.0, 75.0]


def test_rsi_matches_the_stockcharts_reference_table():
    # StockCharts ChartSchool RSI example (14 periods): first values 70.53 and 66.32.
    closes = [44.3389, 44.0902, 44.1497, 43.6124, 44.3278, 44.8264, 45.0955, 45.4245, 45.8433, 46.0826, 45.8931, 46.0328,
              45.6140, 46.2820, 46.2820, 46.0028]
    values = rsi(closes)
    assert values[14] == pytest.approx(70.53, abs=0.01) and values[15] == pytest.approx(66.32, abs=0.01)


def test_state_text_needs_35_bars_and_reads_direction_and_sign():
    rising = [100 * 1.02 ** i for i in range(60)]  # accelerating, so MACD keeps rising above its signal
    falling = [200 - 1.05 ** i for i in range(60)]  # decline speeding up, so MACD keeps falling below its signal
    assert macd_state(rising) == "up,>0" and macd_state(falling) == "down,<0" and macd_state(rising[:34]) is None
    assert rsi_value(rising) == 100 and rsi_value(falling) == 0 and rsi_value(rising[:14]) is None


def test_weekly_and_monthly_keep_the_last_close_of_each_period():
    days = [datetime(2026, 9, 28) + timedelta(days=i) for i in range(10)]  # Mon 28/9 .. Wed 7/10
    points = [(d, float(i)) for i, d in enumerate(days)]
    assert weekly(points) == [6.0, 9.0] and monthly(points) == [2.0, 9.0]


def test_four_hour_bars_are_anchored_at_07_00_vietnam_time():
    hours = [datetime(2026, 10, 23, h, tzinfo=VN) for h in (9, 10, 11, 13, 14)]
    points = [(t, float(i)) for i, t in enumerate(hours)]
    assert four_hourly(points) == [1.0, 4.0]  # 09-10 in 07:00-11:00; 11, 13, 14 in 11:00-15:00
