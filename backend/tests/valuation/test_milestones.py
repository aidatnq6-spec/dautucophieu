from datetime import date, datetime, timedelta
from decimal import Decimal

from investment_agent.valuation.milestones import price_milestones, weekly_closes, zigzag

PRICES = [100, 110, 120, 100, 90, 95, 110, 130, 110, 100]  # thousand đồng, one per week


def days(n, start=date(2020, 6, 5)):
    return [start + timedelta(weeks=i) for i in range(n)]


def daily(prices, start=date(2020, 6, 5)):
    return [(datetime.combine(d, datetime.min.time()), float(p)) for d, p in zip(days(len(prices), start), prices)]


# Shares 1,000,000 (npat 1e10 / eps 10,000); equity 5e10, so 100,000 đ is P/B 2.0 and P/E 10.
RECORD = {"years": {"2019": {"npat": "10000000000", "eps": "10000", "equity": "50000000000"}}, "quarters": {}, "issues": [], "dividends": []}


def test_weekly_closes_keep_the_last_close_of_each_week_in_dong():
    pts = [(datetime(2020, 6, 1), 10.0), (datetime(2020, 6, 5), 12.5), (datetime(2020, 6, 8), 0.0), (datetime(2020, 6, 9), 13.0)]
    assert weekly_closes(pts) == [(date(2020, 6, 5), Decimal("12500")), (date(2020, 6, 9), Decimal("13000"))]


def test_zigzag_confirms_a_turn_only_after_a_move_of_the_threshold_from_the_extreme():
    closes = [(d, Decimal(p * 1000)) for d, p in zip(days(10), PRICES)]
    out = zigzag(closes, Decimal("0.15"))
    assert [(p["kind"], int(p["price"]) // 1000, p["date"]) for p in out["pivots"]] == [
        ("trough", 100, days(10)[0]), ("peak", 120, days(10)[2]), ("trough", 90, days(10)[4]), ("peak", 130, days(10)[7])]
    assert out["trend"] == "down" and out["extreme"] == (days(10)[9], Decimal(100000))


def test_zigzag_without_a_move_of_the_threshold_has_no_pivot():
    out = zigzag([(d, Decimal(p)) for d, p in zip(days(4), [100, 105, 98, 104])], Decimal("0.15"))
    assert out["pivots"] == [] and out["trend"] is None


def test_milestones_list_today_the_earlier_troughs_below_it_and_the_price_at_the_lowest_p_b():
    out = price_milestones(RECORD, daily(PRICES), today=date(2020, 9, 1), threshold=Decimal("0.15"))
    assert out["reason"] is None and out["close"] == "100000" and out["peak"] == {"date": days(10)[7].isoformat(), "price": "130000"}
    assert out["drawdown"] == "-0.2308" and out["corrections"] == [{"peak": days(10)[2].isoformat(), "trough": days(10)[4].isoformat(), "depth": "-0.2500"}]
    rows = [(r["kind"], r["price"], r["drop"], r["pb"], r["pe"], r["vs_floor"], r["deeper"]) for r in out["rows"]]
    assert rows == [
        ("current", "100000", "-0.2308", "2.00", "10.00", "0.1111", 1),  # the −25% correction went deeper
        ("trough", "90000", "-0.3077", "1.80", "9.00", "0.0000", 0),
        ("pb_floor", "90000", "-0.3077", "1.80", "9.00", "0.0000", 0),
    ]
    assert out["floor"] == {"pb": "1.80", "date": days(10)[4].isoformat(), "price": "90000", "from": days(10)[0].isoformat()}
    assert out["rows"][1]["date"] == days(10)[4].isoformat() and out["rows"][1]["label"] == "Đáy nhịp 07/2020"


def test_a_deeper_earlier_correction_is_counted_against_each_milestone():
    prices = [100, 130, 65, 90, 110, 90]  # peak 130 → trough 65 (−50%), then 110 → 90 now
    out = price_milestones(RECORD, daily(prices), today=date(2020, 9, 1), threshold=Decimal("0.15"))
    assert out["corrections"][0]["depth"] == "-0.5000"
    current = out["rows"][0]
    assert current["kind"] == "current" and current["drop"] == "-0.1818" and current["deeper"] == 1


def test_without_prices_or_statements_there_is_a_reason():
    assert price_milestones(RECORD, [], today=date(2020, 9, 1), threshold=Decimal("0.15"))["reason"] == "Chưa có lịch sử giá"
    out = price_milestones(None, daily(PRICES), today=date(2020, 9, 1), threshold=Decimal("0.15"))
    assert out["reason"] is None and out["floor"] is None and all(r["pb"] is None for r in out["rows"])


def test_troughs_and_corrections_before_the_first_p_b_week_are_left_out_and_counted():
    # 2020 statements count from 1 April 2021: the 65 trough of March is older than the P/B series, the 85 one of April is not.
    record = {"years": {"2020": {"npat": "10000000000", "eps": "10000", "equity": "50000000000"}}, "quarters": {}, "issues": [], "dividends": []}
    start = date(2021, 3, 5)
    prices = [100, 130, 65, 90, 110, 90, 85, 100, 120, 100]
    out = price_milestones(record, daily(prices, start), today=date(2021, 6, 1), threshold=Decimal("0.15"))
    w = days(10, start)
    assert out["since"] == w[4].isoformat() and out["omitted_troughs"] == 1
    assert [r["kind"] for r in out["rows"]] == ["current", "trough", "pb_floor"] and out["rows"][1]["price"] == "85000"
    assert out["corrections"] == [{"peak": w[4].isoformat(), "trough": w[6].isoformat(), "depth": "-0.2273"}]
    assert out["peak"] == {"date": w[8].isoformat(), "price": "120000"}
