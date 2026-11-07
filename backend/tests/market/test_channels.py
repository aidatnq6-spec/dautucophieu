from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from investment_agent.market.channels import channels, cutoff, find_bases, frame_bars, hull, line_at, point_zero, running

VN = timezone(timedelta(hours=7))
MON = date(2022, 1, 3)


def wk(i):
    return (MON + timedelta(weeks=i)).isoformat()


def bars(lows, highs=None, closes=None):
    highs = highs or [l + 10 for l in lows]
    closes = closes or [l + 5 for l in lows]
    return [{"t": wk(i), "h": Decimal(h), "l": Decimal(l), "c": Decimal(c)} for i, (l, h, c) in enumerate(zip(lows, highs, closes))]


def test_bars_by_frame_weeks_from_days_days_and_hours_as_given_closes_alone_for_all_three():
    daily = [{"t": "2022-01-03", "o": "10", "h": "12", "l": "9", "c": "11"}, {"t": "2022-01-05", "o": "11", "h": "14", "l": "10", "c": "13"},
             {"t": "2022-01-10", "o": "13", "h": "13", "l": "12", "c": "12.5"}]
    assert frame_bars(daily, "W") == [{"t": "2022-01-03", "h": Decimal(14), "l": Decimal(9), "c": Decimal(13)},
                                      {"t": "2022-01-10", "h": Decimal(13), "l": Decimal(12), "c": Decimal("12.5")}]
    assert frame_bars(daily, "D")[1] == {"t": "2022-01-05", "h": Decimal(14), "l": Decimal(10), "c": Decimal(13)}
    assert frame_bars([{"t": 1700000000, "c": "7"}], "H") == [{"t": 1700000000, "h": Decimal(7), "l": Decimal(7), "c": Decimal(7)}]


def test_a_base_is_the_lowest_low_between_the_bearish_and_the_bullish_cross_known_from_the_bullish_cross():
    b = bars([50, 48, 40, 30, 35, 38, 45, 50, 49, 44, 42, 47])
    diff = [1, 1, -1, -1, -1, -1, 1, 1, -1, -1, 1, 1]  # MACD minus signal: bearish cross at 2, bullish at 6; bearish at 8, bullish at 10
    out = find_bases(b, diff, [0] * 12)
    assert [(x["cross"], x["low_i"], x["low"], x["zone_from"], x["zone_to"]) for x in out] == [
        (6, 3, Decimal(30), 2, 6),  # zone starts two bars before the low, but not before the bearish cross
        (10, 10, Decimal(42), 8, 10),
    ]


def test_a_bullish_cross_without_an_earlier_bearish_cross_is_not_a_base():
    b = bars([50, 40, 45, 50])
    assert find_bases(b, [-1, -1, 1, 1], [0, 0, 0, 0]) == []
    assert find_bases(b, [None, -1, 1, 1], [None, 0, 0, 0]) == []


def base(i_low, low, i_cross, zone_lows=None):
    zone = zone_lows or [low + 5, low, low + 5]
    return {"low_i": i_low, "low": Decimal(low), "cross": i_cross, "zone_from": i_low - 1, "zone_to": i_cross,
            "zone": [(i_low - 1 + k, Decimal(v)) for k, v in enumerate(zone)]}


def test_the_lookback_for_point_zero_is_years_for_weeks_months_for_days_and_weeks_for_hours():
    assert cutoff(datetime(2026, 11, 2), "W", 5) == datetime(2021, 11, 2)
    assert cutoff(datetime(2026, 3, 31), "D", 1) == datetime(2026, 2, 28)
    assert cutoff(datetime(2026, 11, 2, 14), "H", 4) == datetime(2026, 10, 5, 14)


def test_point_zero_is_the_lowest_base_low_at_or_after_the_cutoff():
    b = bars([100] * 300)
    bases = [base(10, 20, 12), base(80, 15, 82), base(200, 30, 202), base(260, 40, 262)]
    assert point_zero(bases, b, frame="W", since=datetime.fromisoformat(wk(50))) == 1
    assert point_zero(bases, b, frame="W", since=datetime.fromisoformat(wk(150))) == 2
    assert point_zero([], b, frame="W", since=datetime.fromisoformat(wk(50))) is None


def test_the_hull_joins_each_zone_at_the_flattest_point_and_drops_a_point_on_or_above_the_next_line():
    p0, b1 = base(1, 100, 3), base(11, 110, 13)
    b2 = base(21, 140, 23, zone_lows=[150, 140, 145])
    b3 = base(31, 150, 33)  # 150 lies below the line 110 → 140 extended (170), so 140 is dropped: line 110 → 150
    assert hull([p0, b1, b2, b3]) == [(1, Decimal(100)), (11, Decimal(110)), (31, Decimal(150))]
    b4 = base(41, 200, 43, zone_lows=[200, 201, 202])
    assert hull([p0, b4])[-1] == (42, Decimal(202))  # slopes from 100: 200 → 2.564, 201 → 2.525, 202 → 2.488 per bar
    assert hull([p0, b1, base(21, 120, 23)]) == [(1, Decimal(100)), (21, Decimal(120))]  # lows on one line: one channel


def test_lines_run_by_bar_count_not_calendar_time():
    assert line_at((0, Decimal(100)), (10, Decimal(200)), 15) == Decimal(250)


def test_the_bar_still_running_is_this_week_today_or_this_hour():
    now = datetime(2026, 11, 7, 10, 30, tzinfo=VN)  # Saturday morning in Hà Nội, Friday night UTC
    assert running("2026-11-02", "W", now) and not running("2026-10-26", "W", now)
    assert running("2026-11-07", "D", now) and running("2026-11-06", "D", datetime(2026, 11, 7, 3, tzinfo=VN))  # UTC day still open
    assert not running("2026-11-06", "D", now)
    hour = int(datetime(2026, 11, 7, 10, tzinfo=timezone.utc).timestamp())  # 10:00 Hà Nội wall-clock, as the chart keys hours
    assert running(hour, "H", now) and not running(hour - 3600, "H", now)


def sawtooth(frame, n=208, step=lambda k: 3 + k):
    price, out = Decimal(100), []
    for i in range(n):
        price += Decimal(step(i // 16)) if i % 16 < 12 else Decimal(-6)
        t = wk(i) if frame in ("W", "D") else 1_600_000_000 + i * 3600
        out.append({"t": t, "h": str(price + 4), "l": str(price), "c": str(price + 2)})
    return out


def test_channels_status_and_breaks_on_a_rising_series_with_pullbacks_then_a_fall():
    raw = sawtooth("D", n=128) + [{"t": wk(128 + i), "h": "1", "l": "1", "c": "1"} for i in range(6)]
    out = channels(raw, frame="D", now=datetime(2030, 1, 1, tzinfo=VN), n=120)
    assert out["reason"] is None and out["frame"] == "D" and out["n"] == 120 and len(out["bases"]) >= 4
    assert all(b["cross"] >= b["low_date"] for b in out["bases"])
    assert out["points"]["0"]["date"] == out["bases"][out["zero"]]["low_date"]
    chans = out["channels"]
    assert chans[0]["kind"] == "basic" and chans[-1]["kind"] == "final"
    assert all(Decimal(a["slope"]) < Decimal(b["slope"]) for a, b in zip(chans, chans[1:]))
    assert all(Decimal(c["upper_now"]) > Decimal(c["lower_now"]) for c in chans)
    assert out["status"]["state"] == "below" and out["breaks"][-1]["date"] > chans[-1]["to"]["date"]


def test_hourly_bars_keep_their_numeric_keys():
    out = channels(sawtooth("H", n=208), frame="H", now=datetime(2030, 1, 1, tzinfo=VN), n=520)
    assert out["reason"] is None and isinstance(out["last_bar"], int) and isinstance(out["channels"][-1]["to"]["date"], int)


def test_without_enough_bars_or_bases_there_is_a_reason():
    daily = [{"t": wk(i), "c": "10"} for i in range(20)]
    assert channels(daily, frame="W", now=datetime(2030, 1, 1, tzinfo=VN), n=5)["reason"] == "Chỉ có 20 nến tuần, cần ít nhất 35 nến để có MACD"
    assert channels([], frame="D", now=datetime(2030, 1, 1, tzinfo=VN), n=12)["reason"] == "Chưa có dữ liệu giá"
    flat = [{"t": wk(i), "c": "10"} for i in range(60)]
    assert channels(flat, frame="D", now=datetime(2030, 1, 1, tzinfo=VN), n=12)["reason"] == "Không có đáy vùng MACD nào trong 12 tháng"


def test_the_bar_still_running_is_shown_but_not_used():
    daily = [{"t": wk(i), "c": str(100 + i)} for i in range(60)]
    out = channels(daily, frame="W", now=datetime.fromisoformat(wk(59) + "T12:00:00+07:00"), n=5)
    assert out["in_progress"] == {"t": wk(59), "c": "159"} and out["last_bar"] == wk(58)
