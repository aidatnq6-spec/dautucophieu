from datetime import date, datetime, timedelta
from decimal import Decimal

from investment_agent.valuation.index_reference import value_index
from investment_agent.valuation.reference import Settings

TODAY = date(2026, 10, 31)


def _daily(start: date, end: date, value) -> list[tuple[datetime, float]]:
    days = (end - start).days
    return [(datetime.combine(start + timedelta(days=i), datetime.min.time()), value(i) if callable(value) else value)
            for i in range(days + 1) if (start + timedelta(days=i)).weekday() < 5]


def test_fair_level_is_the_close_scaled_by_median_over_current_multiple():
    # Five years at P/E 15 then today 12; P/B 2 throughout then today 2. Close 1,800 points on the last day.
    pe = _daily(date(2021, 10, 1), date(2026, 10, 29), 15.0) + [(datetime(2026, 10, 30), 12.0)]
    pb = _daily(date(2021, 10, 1), date(2026, 10, 29), 2.0) + [(datetime(2026, 10, 30), 2.0)]
    closes = [(datetime(2026, 10, 29), 1810.0), (datetime(2026, 10, 30), 1800.0)]
    row = value_index("VNINDEX", pe=pe, pb=pb, closes=closes, settings=Settings(threshold=Decimal("0.2")), today=TODAY)
    methods = {m["method"]: m for m in row["methods"]}
    assert methods["pe_history"]["value"] == "2250.00"  # 1,800 × 15 / 12
    assert methods["pe_history"]["inputs"] == {"now": "12.00", "median": "15.00", "since": "2021-10-30", "points": len(
        [p for p in pe if p[0].date() > date(2021, 10, 30)])}
    assert methods["pb_history"]["value"] == "1800.00"
    assert row["close"] == "1800.00" and row["as_of"] == "2026-10-30"
    assert row["fair"] == "2025.00" and row["low"] == "1800.00" and row["high"] == "2250.00"
    assert row["gap"] == "-0.1111" and row["verdict"] == "fair"


def test_cheap_and_expensive_follow_the_owner_threshold():
    pe = _daily(date(2021, 1, 4), date(2026, 10, 29), 10.0) + [(datetime(2026, 10, 30), 15.0)]
    pb = _daily(date(2021, 1, 4), date(2026, 10, 29), 1.0) + [(datetime(2026, 10, 30), 1.5)]
    closes = [(datetime(2026, 10, 30), 1500.0)]
    row = value_index("VN30", pe=pe, pb=pb, closes=closes, settings=Settings(threshold=Decimal("0.3")), today=TODAY)
    assert row["fair"] == "1000.00" and row["gap"] == "0.5000" and row["verdict"] == "expensive"


def test_short_history_old_data_or_a_missing_close_give_reasons_not_numbers():
    recent = _daily(date(2024, 1, 2), date(2026, 10, 30), 12.0)
    closes = [(datetime(2026, 10, 30), 1800.0)]
    row = value_index("VNINDEX", pe=recent, pb=recent, closes=closes, settings=Settings(), today=TODAY)
    assert row["verdict"] == "insufficient" and row["fair"] is None
    assert {m["reason"] for m in row["methods"]} == {"Cần lịch sử ít nhất 4 năm"}
    assert row["reason"] == "Ít hơn 2 phương án đủ dữ liệu"

    old = _daily(date(2020, 1, 2), date(2026, 10, 9), 12.0)
    row = value_index("VNINDEX", pe=old, pb=old, closes=[(datetime(2026, 10, 9), 1700.0)], settings=Settings(), today=TODAY)
    assert {m["reason"] for m in row["methods"]} == {"Số liệu mới nhất ngày 09/10/2026, cũ hơn 10 ngày"}

    full = _daily(date(2020, 1, 2), date(2026, 10, 30), 12.0)
    row = value_index("VNINDEX", pe=full, pb=full, closes=[(datetime(2026, 10, 29), 1800.0)], settings=Settings(), today=TODAY)
    assert {m["reason"] for m in row["methods"]} == {"Chưa có điểm chỉ số ngày 30/10/2026"}

    row = value_index("VN30", pe=[], pb=[], closes=[], settings=Settings(), today=TODAY)
    assert row["verdict"] == "insufficient" and {m["reason"] for m in row["methods"]} == {"Chưa có số liệu"}


def test_monthly_chart_covers_five_years_with_the_daily_median_and_spread():
    from investment_agent.valuation.index_reference import index_monthly_multiples
    pe = _daily(date(2019, 1, 1), date(2026, 10, 29), lambda i: 10.0 + (i % 2) * 10) + [(datetime(2026, 10, 30), 12.0)]
    out = index_monthly_multiples("VNINDEX", pe=pe, pb=pe)
    assert out["kind"] == "index" and out["reason"] is None
    assert out["from"] == "2021-11" and out["to"] == "2026-10"  # months after 30/10/2021
    assert out["pe"]["points"][-1] == {"month": "2026-10", "value": "12.00", "year": None}
    assert out["pe"]["latest"] == "12.00" and out["pe"]["median"] is not None and out["pe"]["sd"] is not None
    assert index_monthly_multiples("VN30", pe=[], pb=[])["reason"] == "Chưa có số liệu P/E, P/B"
