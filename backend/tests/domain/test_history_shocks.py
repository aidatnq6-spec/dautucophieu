"""Thống kê lịch sử, rủi ro trong kỳ và cú sốc (owner, 21/11/2026): besides the average, each group says how deep VN-Index fell at
worst within the H sessions after (its median and its worst), and the ordinary bad and good outcomes (10th and 90th percentiles).
"Sau một cú sốc thì sao?": the days VN-Index fell 3% in a session, fell five sessions running, crossed below its 200-session average,
or first stood 20% under its peak."""

from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.history_stats import forward_dips, group_summary, shock_days

D = Decimal


def closes_of(values, start=date(2010, 1, 1)):
    return [(start + timedelta(days=i), D(v)) for i, v in enumerate(values)]


def test_the_deepest_fall_within_the_h_sessions_after_each_day():
    closes = closes_of(["100", "90", "120", "80", "130"])
    dips = forward_dips(closes, 2)
    assert dips[date(2010, 1, 1)] == D("-0.1")        # 90 within the next two sessions
    assert dips[date(2010, 1, 2)] == D("80") / D("90") - 1
    assert dips[date(2010, 1, 3)] == D("80") / D("120") - 1
    assert date(2010, 1, 4) not in dips                # not two sessions left
    assert forward_dips(closes_of(["100", "110", "120"]), 2)[date(2010, 1, 1)] == D(0)  # never under the entry: no fall


def test_a_group_adds_its_falls_and_its_ordinary_bad_and_good_outcomes():
    days = [date(2010, 1, 1) + timedelta(days=i) for i in range(100)]
    index = {d: i for i, d in enumerate(days)}
    returns = {d: D(i - 50) / 100 for i, d in enumerate(days)}
    dips = {d: D(-i) / 1000 for i, d in enumerate(days)}
    out = group_summary(days, returns, index, h=10, dips=dips)
    assert out["p10"] == "-0.4010" and out["p90"] == "0.3910"  # inclusive quantiles over −0.50 … 0.49
    assert out["dip_median"] == "-0.0495" and out["dip_worst"] == "-0.0990"


def test_too_few_independent_windows_hide_the_figures():
    days = [date(2010, 1, 1) + timedelta(days=i) for i in range(30)]
    index = {d: i for i, d in enumerate(days)}
    out = group_summary(days, {d: D("0.1") for d in days}, index, h=10)
    assert out["n_independent"] == 3 and out["enough"] is False


def test_the_four_shocks_on_vn_index():
    values = ["100"] * 210 + ["96"] + ["95", "94", "93", "92", "91"] + ["91"] * 10 + ["79"]
    shocks = shock_days(closes_of(values))
    assert shocks["drop3"] == [date(2010, 1, 1) + timedelta(days=210), date(2010, 1, 1) + timedelta(days=226)]   # −4% and −13%
    assert shocks["down5"] == [date(2010, 1, 1) + timedelta(days=214)]                                         # the fifth fall in a row (210 … 214)
    assert shocks["below200"] == [date(2010, 1, 1) + timedelta(days=210)]                                      # first close under the average
    assert shocks["dd20"] == [date(2010, 1, 1) + timedelta(days=226)]                                          # 79 is 21% under 100
