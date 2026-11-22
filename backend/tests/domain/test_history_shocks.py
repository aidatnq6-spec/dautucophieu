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


# Cú sốc chồng cú sốc and Cú sốc hôm nay (owner, 21/11/2026): a 3% fall or five falls in a row, split by whether VN-Index was then
# under its 200-session average or 20% under its 52-week high; and one line, on the page, in the brief and on Telegram, when VN-Index
# had a shock on the latest session, read from its past.

from investment_agent.domain.history_stats import combo_days, shock_line, shocks_today  # noqa: E402


def test_a_shock_is_split_by_where_vn_index_stood_that_day():
    values = ["100"] * 210 + ["96"] + ["95", "94", "93", "92", "91"] + ["91"] * 10 + ["79"]
    combos = combo_days(closes_of(values))
    day = lambda i: date(2010, 1, 1) + timedelta(days=i)  # noqa: E731
    assert combos["drop3_under200"] == [day(210), day(226)] and combos["drop3_over200"] == []
    assert combos["down5_under200"] == [day(214)]
    assert combos["drop3_dd20"] == [day(226)] and combos["down5_dd20"] == []


def test_the_shock_of_the_latest_session_is_read_from_its_past():
    values = []
    for k in range(61):  # a rising market with a 4% fall every fourth session, the last one on the latest session
        base = D(100) * D("1.01") ** k
        values += [base, base, base, base * D("0.96")]
    closes = closes_of(values)
    out = shocks_today(closes, session=closes[-1][0], h=20)
    assert out["status"] == "ok" and [s["id"] for s in out["today"]] == ["drop3"]
    line = shock_line(out)
    assert line.startswith("Cú sốc hôm nay: VN-Index giảm từ 3% trong một phiên. ")
    assert "20 phiên sau trung bình" in line and "(mọi lúc " in line and "khoảng không chồng lấn" in line
    assert line.endswith("Chỉ mô tả quá khứ, không phải dự báo.")


def test_no_line_without_a_shock_or_without_the_session():
    closes = closes_of(["100"] * 300)
    assert shocks_today(closes, session=closes[-1][0], h=60)["today"] == [] and shock_line(shocks_today(closes, session=closes[-1][0], h=60)) is None
    assert shocks_today(closes, session=closes[-1][0] + timedelta(days=1), h=60)["status"] == "missing"  # the session's close is not stored yet
    assert shock_line(None) is None


def test_the_shock_line_says_whether_the_shock_differs_from_the_other_sessions_owner_22_11_2026():
    from investment_agent.domain.history_stats import _shock_past
    g = {"events": 40, "n_independent": 12, "mean": "0.05", "p10": "-0.08", "dip_median": "-0.04", "enough": True,
         "t_rest": "0.84", "t_need": "2.20", "differs": False, "halves": None}
    every = {"mean": "0.048"}
    past = _shock_past(g, every, 60, "2000-07-28")
    assert past.endswith("giảm sâu nhất trong kỳ trung vị −4,0%; chưa rõ khác các lúc còn lại (t = 0,84, cần 2,20)")
    clear = _shock_past({**g, "t_rest": "-3.1", "differs": True, "halves": "same"}, every, 60, "2000-07-28")
    assert clear.endswith("; khác các lúc còn lại (t = −3,1, cần 2,20), ổn định ở hai nửa lịch sử")
    old = {k: v for k, v in g.items() if k not in ("t_rest", "t_need", "differs", "halves")}  # a snapshot stored before 22/11/2026
    assert _shock_past(old, every, 60, "2000-07-28").endswith("giảm sâu nhất trong kỳ trung vị −4,0%")
