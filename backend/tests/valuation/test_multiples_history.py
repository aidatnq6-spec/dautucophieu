from datetime import date, datetime
from decimal import Decimal

from investment_agent.valuation.history import monthly_multiples

# Shares 1,000,000 (npat 1e9 / eps 1000). Year Y figures apply from 1 April Y+1, when annual reports are out.
RECORD = {"years": {"2019": {"npat": "1000000000", "eps": "1000", "equity": "10000000000"},
                    "2020": {"npat": "-500000000", "eps": "-500", "equity": "8000000000"},
                    "2021": {"npat": "2000000000", "eps": "2000", "equity": "12000000000"}},
          "quarters": {}, "issues": [], "dividends": []}


def points(*pairs):
    return [(datetime.fromisoformat(d), v) for d, v in pairs]


def test_each_month_uses_its_last_close_and_the_latest_published_annual_figures():
    out = monthly_multiples(RECORD, points(("2020-03-02", 10.0), ("2020-03-31", 12.0), ("2020-04-30", 15.0),
                                           ("2021-04-30", 20.0), ("2022-05-31", 30.0)), today=date(2022, 6, 15))
    pe = {p["month"]: p["value"] for p in out["pe"]["points"]}
    pb = {p["month"]: p["value"] for p in out["pb"]["points"]}
    assert "2020-03" not in pe  # no annual report published yet for any year before April 2020
    assert pe["2020-04"] == "15.00"  # 15,000 đ × 1,000,000 / 1e9 (2019 profit)
    assert pe["2021-04"] is None  # 2020 loss: no P/E
    assert pb["2021-04"] == "2.50"  # 20,000 × 1e6 / 8e9
    assert pe["2022-05"] == "15.00" and pb["2022-05"] == "2.50"  # 30,000 × 1e6 / 2e9 ; / 12e9
    assert out["pe"]["latest"] == "15.00" and out["pe"]["median"] == "15.00" and out["pe"]["sd"] == "0.00"
    assert out["shares"] == 1000000 and out["from"] == "2020-04" and out["to"] == "2022-05"


def test_band_statistics_cover_the_whole_history():
    out = monthly_multiples(RECORD, points(("2020-04-30", 10.0), ("2020-05-29", 20.0), ("2020-06-30", 30.0)), today=date(2020, 7, 1))
    assert out["pe"]["median"] == "20.00" and out["pe"]["sd"] == "8.16" and out["pe"]["latest"] == "30.00"


def test_without_statements_or_prices_there_is_a_reason_not_a_chart():
    assert monthly_multiples({"years": {}, "quarters": {}}, [], today=date(2026, 1, 1))["reason"] == "Chưa có báo cáo tài chính"
    out = monthly_multiples(RECORD, [], today=date(2026, 1, 1))
    assert out["reason"] == "Chưa có lịch sử giá" and out["pe"]["points"] == []


def test_months_use_four_real_quarters_when_the_record_has_them_and_name_the_period():
    quarters = {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2021-Q2", "2021-Q3", "2021-Q4", "2022-Q1")}
    out = monthly_multiples({**RECORD, "quarters": quarters}, points(("2022-05-31", 30.0)), today=date(2022, 6, 15))
    p = out["pe"]["points"][0]
    assert (p["month"], p["value"], p["year"], p["basis"]) == ("2022-05", "30.00", "2022-Q1", "4 quý")  # 30,000 × 1 million / 1 tỷ


def test_a_publication_calendar_and_a_share_count_can_be_given():
    quarters = {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2021-Q2", "2021-Q3", "2021-Q4", "2022-Q1")}
    early = lambda p: date(2022, 4, 20) if p == "2022-Q1" else date(2099, 1, 1)  # noqa: E731
    out = monthly_multiples({"years": {}, "quarters": quarters}, points(("2022-04-29", 30.0)), today=date(2022, 6, 15), shares=2000000, published=early)
    assert out["pe"]["points"][0]["value"] == "60.00" and out["shares"] == 2000000
