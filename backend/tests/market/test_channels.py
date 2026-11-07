from datetime import date, timedelta
from decimal import Decimal

from investment_agent.market.channels import find_bases, hull, line_at, point_zero, weekly_bars, weekly_channels

MON = date(2022, 1, 3)


def wk(i):
    return MON + timedelta(weeks=i)


def bars(lows, highs=None, closes=None):
    highs = highs or [l + 10 for l in lows]
    closes = closes or [l + 5 for l in lows]
    return [{"t": wk(i), "h": Decimal(h), "l": Decimal(l), "c": Decimal(c)} for i, (l, h, c) in enumerate(zip(lows, highs, closes))]


def test_weekly_bars_take_the_week_s_highest_high_lowest_low_and_last_close_or_closes_alone():
    daily = [{"t": "2022-01-03", "o": "10", "h": "12", "l": "9", "c": "11"}, {"t": "2022-01-05", "o": "11", "h": "14", "l": "10", "c": "13"},
             {"t": "2022-01-10", "o": "13", "h": "13", "l": "12", "c": "12.5"}]
    assert weekly_bars(daily) == [{"t": date(2022, 1, 3), "h": Decimal(14), "l": Decimal(9), "c": Decimal(13)},
                                  {"t": date(2022, 1, 10), "h": Decimal(13), "l": Decimal(12), "c": Decimal("12.5")}]
    assert weekly_bars([{"t": "2022-01-04", "c": "7"}]) == [{"t": date(2022, 1, 3), "h": Decimal(7), "l": Decimal(7), "c": Decimal(7)}]


def test_a_base_is_the_lowest_low_between_the_bearish_and_the_bullish_cross_known_from_the_bullish_cross():
    weeks = bars([50, 48, 40, 30, 35, 38, 45, 50, 49, 44, 42, 47])
    line = [1, 1, -1, -1, -1, -1, 1, 1, -1, -1, 1, 1]  # MACD minus signal: bearish cross at 2, bullish at 6; bearish at 8, bullish at 10
    signal = [0] * 12
    out = find_bases(weeks, line, signal)
    assert [(b["cross"], b["low_date"], b["low"], b["zone_from"], b["zone_to"]) for b in out] == [
        (wk(6), wk(3), Decimal(30), wk(2), wk(6)),  # zone starts two weeks before the low, but not before the bearish cross
        (wk(10), wk(10), Decimal(42), wk(8), wk(10)),
    ]


def test_a_bullish_cross_without_an_earlier_bearish_cross_is_not_a_base():
    weeks = bars([50, 40, 45, 50])
    assert find_bases(weeks, [-1, -1, 1, 1], [0, 0, 0, 0]) == []
    assert find_bases(weeks, [None, -1, 1, 1], [None, 0, 0, 0]) == []


def base(i_low, low, i_cross, zone_lows=None):
    return {"low_date": wk(i_low), "low": Decimal(low), "cross": wk(i_cross), "zone_from": wk(i_low - 1), "zone_to": wk(i_cross),
            "zone": [(wk(i_low - 1 + k), Decimal(v)) for k, v in enumerate(zone_lows or [low + 5, low, low + 5])]}


def test_point_zero_is_the_lowest_base_low_within_the_last_n_years():
    bases = [base(10, 20, 12), base(80, 15, 82), base(200, 30, 202), base(260, 40, 262)]
    assert point_zero(bases, last=wk(300), years=5) == 1
    assert point_zero(bases, last=wk(300), years=3) == 2  # the 15 low is more than three years back
    assert point_zero([], last=wk(300), years=5) is None


def test_the_hull_joins_each_zone_at_the_flattest_point_and_drops_a_point_that_falls_above_the_next_line():
    p0 = base(1, 100, 3)
    b1 = base(11, 110, 13)
    b2 = base(21, 140, 23, zone_lows=[150, 140, 145])
    b3 = base(31, 150, 33)  # 150 lies below the line 110 → 140 extended (170), so 140 is dropped: line 110 → 150
    pts = hull([p0, b1, b2, b3])
    assert [(d, p) for d, p in pts] == [(wk(1), Decimal(100)), (wk(11), Decimal(110)), (wk(31), Decimal(150))]
    # The connection point is the flattest one seen from the previous point, not always the zone's lowest.
    b4 = base(41, 200, 43, zone_lows=[200, 201, 202])
    assert hull([p0, b4])[-1] == (wk(42), Decimal(202))  # slopes from 100: 200 → 2.564, 201 → 2.525, 202 → 2.488 per week


def test_line_value_runs_along_the_two_points_by_calendar_day():
    assert line_at((wk(0), Decimal(100)), (wk(10), Decimal(200)), wk(15)) == Decimal(250)


def test_channels_status_and_breaks_on_a_rising_series_with_pullbacks():
    # Rising saw-tooth: 12 weeks up, 4 weeks down, repeated; then a deep fall at the end.
    lows, price = [], Decimal(100)
    for cycle in range(8):
        for _ in range(12):
            price += Decimal(3 + cycle)  # steeper every cycle, so each base sits above the line through the earlier ones
            lows.append(price)
        for _ in range(4):
            price -= Decimal(6)
            lows.append(price)
    for _ in range(8):
        price -= Decimal(10)
        lows.append(price)
    daily = [{"t": wk(i).isoformat(), "h": str(l + 4), "l": str(l), "c": str(l + 2)} for i, l in enumerate(lows)]
    out = weekly_channels(daily, today=wk(len(lows)) + timedelta(days=1), years=5)
    assert out["reason"] is None and len(out["bases"]) >= 4
    assert all(b["cross"] >= b["low_date"] for b in out["bases"])  # known only from the bullish cross
    assert out["points"]["0"]["date"] == out["bases"][out["zero"]]["low_date"]
    chans = out["channels"]
    assert chans[0]["kind"] == "basic" and chans[-1]["kind"] == "final"
    assert all(Decimal(a["slope"]) <= Decimal(b["slope"]) for a, b in zip(chans, chans[1:]))  # each later channel at least as steep
    assert all(Decimal(c["upper_now"]) > Decimal(c["lower_now"]) for c in chans)
    assert out["status"]["state"] == "below"  # the deep fall closed under the final channel
    assert out["breaks"] and out["breaks"][-1]["date"] > chans[-1]["to"]["date"]


def test_without_enough_weeks_there_is_a_reason():
    daily = [{"t": wk(i).isoformat(), "c": "10"} for i in range(20)]
    assert weekly_channels(daily, today=wk(21), years=5)["reason"] == "Chỉ có 20 tuần, cần ít nhất 35 tuần để có MACD tuần"
    assert weekly_channels([], today=wk(1), years=5)["reason"] == "Chưa có dữ liệu giá"


def test_the_week_still_running_is_shown_but_not_used():
    daily = [{"t": wk(i).isoformat(), "c": str(100 + i)} for i in range(60)]
    out = weekly_channels(daily, today=wk(59) + timedelta(days=2), years=5)
    assert out["in_progress"] == {"t": wk(59).isoformat(), "c": "159"} and out["last_week"] == wk(58).isoformat()


def test_lows_on_one_straight_line_make_one_channel_not_several_of_the_same_slope():
    p0, b1, b2 = base(1, 100, 3), base(11, 110, 13), base(21, 120, 23)
    assert hull([p0, b1, b2]) == [(wk(1), Decimal(100)), (wk(21), Decimal(120))]
