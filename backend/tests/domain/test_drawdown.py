from datetime import datetime

from investment_agent.domain.drawdown import current_drawdown, max_drawdown, threshold_alerts


def pts(*pairs):
    return [(datetime(2008, 1, d), float(v)) for d, v in pairs]


def test_the_deepest_fall_from_a_peak_with_its_dates_and_recovery():
    series = pts((1, 100), (2, 120), (3, 90), (4, 60), (5, 80), (6, 125), (7, 110))
    dd = max_drawdown(series)
    assert dd == {"depth": "-0.5000", "peak": "2008-01-02", "trough": "2008-01-04", "recovered": "2008-01-06"}


def test_a_fall_not_yet_recovered_has_no_recovery_date():
    assert max_drawdown(pts((1, 100), (2, 70), (3, 80)))["recovered"] is None


def test_no_fall_or_no_data():
    assert max_drawdown(pts((1, 100), (2, 110)))["depth"] == "0.0000"
    assert max_drawdown([]) is None and current_drawdown([]) is None


def test_current_fall_from_the_highest_close_so_far():
    assert current_drawdown(pts((1, 100), (2, 120), (3, 90))) == {"depth": "-0.2500", "peak": "2008-01-02"}


def test_a_ticker_crossing_the_threshold_alerts_once_and_rearms_after_recovering():
    holdings = {"KDH": {"price": "14750", "cost": "23413"}, "SSI": {"price": "19800", "cost": "24710"}}  # −37%, −19.9%
    alerts, alerted = threshold_alerts(holdings, threshold="0.30", alerted=set())
    assert [(a["symbol"], a["change"]) for a in alerts] == [("KDH", "-0.3700")] and alerted == {"KDH"}
    again, alerted = threshold_alerts(holdings, threshold="0.30", alerted=alerted)
    assert again == [] and alerted == {"KDH"}
    recovered = {**holdings, "KDH": {"price": "17000", "cost": "23413"}}  # −27%: back above the threshold
    _, alerted = threshold_alerts(recovered, threshold="0.30", alerted=alerted)
    assert alerted == set()
    alerts, _ = threshold_alerts(holdings, threshold="0.30", alerted=alerted)
    assert [a["symbol"] for a in alerts] == ["KDH"]


def test_tickers_without_a_price_or_cost_are_left_alone():
    alerts, alerted = threshold_alerts({"MBB": {"price": None, "cost": "20456"}}, threshold="0.30", alerted={"MBB"})
    assert alerts == [] and alerted == {"MBB"}
