from datetime import date, datetime, timedelta

from investment_agent.domain.report_reaction import reaction

B = 10**9


def sessions(start: date, values: list[float]) -> list[tuple[datetime, float]]:
    out, d = [], start
    for v in values:
        while d.weekday() >= 5:
            d += timedelta(days=1)
        out.append((datetime(d.year, d.month, d.day), v))
        d += timedelta(days=1)
    return out


def test_the_price_five_and_twenty_sessions_after_the_report_against_vn_index():
    quarters = {"2025-Q3": {"npat_parent": str(100 * B)}, "2026-Q3": {"npat_parent": str(150 * B)}}
    created = {"2025-Q3": "2025-10-29", "2026-Q3": "2026-10-30"}  # Friday 30/10/2026
    closes = sessions(date(2026, 10, 26), [10, 10, 10, 10, 20] + [21] * 4 + [22] + [23] * 14 + [30])  # 30/10 is the 5th session
    index = sessions(date(2026, 10, 26), [100] * 4 + [100] + [101] * 5 + [110] * 15 + [120])
    view = reaction(quarters, created, closes, index, n=2)
    last = view["rows"][-1]
    assert last["quarter"] == "2026-Q3" and last["report_day"] == "2026-10-30" and last["base_day"] == "2026-10-29"
    assert last["profit_yoy"] == "0.5000"
    assert last["after_5"] == "1.1000" and last["after_20"] == "1.3000"  # 10 → 21 five sessions on, → 23 twenty sessions on
    assert last["index_20"] == "0.1000" and last["excess_20"] == "1.2000"
    assert view["rows"][0]["after_5"] is None  # no prices around 2025-Q3 here


def test_a_report_day_far_from_the_quarter_is_not_a_report_day():
    view = reaction({"2010-Q1": {"npat_parent": "1"}}, {"2010-Q1": "2019-12-01"}, [], [], n=1)
    assert view["rows"][0]["report_day"] is None and view["rows"][0]["reason"] == "no_report_day"


def test_the_summary_counts_good_news_sold_and_bad_news_bought_after_twenty_sessions():
    rows = [{"profit_yoy": "0.3", "profit_turn": None, "after_20": "-0.05"}, {"profit_yoy": "-0.4", "profit_turn": None, "after_20": "0.08"},
            {"profit_yoy": "0.2", "profit_turn": None, "after_20": "0.1"}, {"profit_yoy": None, "profit_turn": None, "after_20": "0.1"}]
    from investment_agent.domain.report_reaction import summary
    assert summary(rows) == {"compared": 3, "good_sold": 1, "bad_bought": 1, "same_way": 1}
