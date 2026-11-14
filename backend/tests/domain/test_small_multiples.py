from datetime import date, datetime, timedelta

from investment_agent.domain.small_multiples import small_multiples

TODAY = date(2026, 11, 14)


def daily(start_value, step, days=400):
    first = TODAY - timedelta(days=days)
    return [(datetime.combine(first + timedelta(days=i), datetime.min.time()), start_value + step * i) for i in range(days + 1)]


def test_each_held_ticker_is_rebased_to_100_a_year_ago_beside_the_index_once_a_week():
    out = small_multiples({"FPT": daily(100.0, 0.1), "NEW": daily(10.0, 0.0, days=30)}, index=daily(1000.0, 0.0), today=TODAY)
    fpt = next(c for c in out["charts"] if c["symbol"] == "FPT")
    assert fpt["points"][0]["value"] == "100" and fpt["points"][0]["index"] == "100"
    assert 50 <= len(fpt["points"]) <= 54  # weekly over a year
    assert fpt["change"] == fpt["points"][-1]["value"] and fpt["index_change"] == "100"
    assert float(fpt["change"]) > 100 and fpt["ahead"] is True
    assert out["short"] == {"NEW": "chưa đủ 12 tháng giá"}
