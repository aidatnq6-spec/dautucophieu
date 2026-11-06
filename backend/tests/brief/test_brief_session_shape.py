import json
from datetime import date, timedelta
from decimal import Decimal

from investment_agent.brief.session_shape import hose_liquidity, index_session


def sessions(end: date, n: int) -> list[date]:
    """n weekdays before end, ascending (a synthetic calendar without holidays)."""
    out, d = [], end
    while len(out) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            out.append(d)
    return out[::-1]


S = date(2026, 11, 5)
EARLIER = sessions(S, 60)


def bar(close, high=None, low=None, volume=500_000_000):
    c = Decimal(close)
    return {"high": Decimal(high) if high else c, "low": Decimal(low) if low else c, "close": c, "volume": volume}


def bars(closes: list[str], **today):
    """The last len(closes) earlier sessions closing at these values, then the session itself."""
    out = {d: bar(c) for d, c in zip(EARLIER[-len(closes):], closes)}
    out[S] = bar(**today)
    return out


def test_range_streak_and_volume_of_the_session():
    b = bars(["1720", "1710.72", "1699.62", "1733.02"], close="1740.73", high="1753.15", low="1733.02", volume=673_228_995)
    for d in EARLIER[-20:-1]:
        b.setdefault(d, bar("1700"))["volume"] = 600_000_000
    b[EARLIER[-1]]["volume"] = 785_061_515
    out = index_session(b, session_date=S, earlier=EARLIER)
    assert out["status"] == "ok"
    assert out["range"] == {"high": "1753.15", "low": "1733.02", "close": "1740.73", "from_high": "12.42", "from_low": "7.71"}
    assert out["streak"] == {"direction": "up", "sessions": 2, "at_least": False, "change": "41.11", "pct": "0.0242"}  # from 1.699,62
    assert out["volume"] == {"status": "ok", "today": 673228995, "previous": 785061515, "change_pct": "-0.1425",
                             "avg20": 609253076, "ratio20": "1.11"}  # 19 × 600 tr + 785 tr over 20


def test_a_down_or_flat_session_and_a_streak_that_runs_past_the_data():
    down = index_session(bars(["1710", "1705"], close="1700"), session_date=S, earlier=EARLIER)
    assert down["streak"] == {"direction": "down", "sessions": 2, "at_least": True, "change": None, "pct": None}  # no close before 1710
    flat = index_session(bars(["1710", "1700"], close="1700"), session_date=S, earlier=EARLIER)
    assert flat["streak"] == {"direction": "flat", "sessions": 1, "at_least": False, "change": "0.00", "pct": "0.0000"}
    assert down["volume"] == {"status": "missing", "reason": "Thiếu nến 18 trong 20 phiên trước"}


def test_no_bar_for_the_session_is_missing_not_guessed():
    assert index_session(bars(["1700"], close="1700") | {S: None}, session_date=S, earlier=EARLIER) == {
        "status": "missing", "reason": "Chưa có nến VN-Index phiên này"}
    assert index_session({}, session_date=S, earlier=EARLIER)["status"] == "missing"


def value(million: str) -> str:
    return json.dumps({"data": [{"trading_type_name": "Mua", "market_value": million, "foreign_trading_value": "1"}], "success": True})


def test_hose_value_against_the_previous_session_and_the_20_session_total():
    asked = []

    def get(url):
        asked.append(url)
        return value("15,000,000.00") if "fromDate=2026-11-04&toDate=2026-11-04" in url else value("330,000,000.00")
    out = hose_liquidity({"status": "ok", "total_value_bn": "15963.62"}, earlier=EARLIER, hose_get=get)
    assert out == {"status": "ok", "today_bn": "15963.62", "previous_bn": "15000.00", "change_pct": "0.0642", "avg20_bn": "16500.00",
                   "ratio20": "0.97"}
    assert any(f"fromDate={EARLIER[-20].isoformat()}&toDate={EARLIER[-1].isoformat()}" in u for u in asked) and len(asked) == 2


def test_hose_value_is_missing_until_hose_publishes_the_session_and_its_history():
    assert hose_liquidity({"status": "missing", "reason": "HOSE chưa công bố"}, earlier=EARLIER, hose_get=lambda u: value("1")) == {
        "status": "missing", "reason": "HOSE chưa công bố"}
    empty = json.dumps({"data": [], "success": True})
    assert hose_liquidity({"status": "ok", "total_value_bn": "1"}, earlier=EARLIER, hose_get=lambda u: empty) == {
        "status": "missing", "reason": "HOSE chưa có số các phiên trước"}
    assert hose_liquidity({"status": "ok", "total_value_bn": "1"}, earlier=EARLIER[-5:], hose_get=lambda u: value("1"))["status"] == "missing"


def test_ma20_is_the_mean_close_of_the_session_and_the_19_before_and_missing_when_a_bar_is():
    b = {d: bar("1700") for d in EARLIER[-19:]}
    b[S] = bar("1720")
    out = index_session(b, session_date=S, earlier=EARLIER)
    assert out["ma20"] == {"status": "ok", "value": "1701.00", "above": True}  # (19 × 1700 + 1720) / 20
    del b[EARLIER[-7]]
    assert index_session(b, session_date=S, earlier=EARLIER)["ma20"] == {"status": "missing", "reason": "Thiếu nến 1 trong 20 phiên"}
