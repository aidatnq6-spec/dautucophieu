from datetime import date, datetime

from investment_agent.valuation.weekly import published_from, weekly_multiples

# Shares 1,000,000 (npat 1e9 / eps 1000). Year Y is out from 1 April Y+1; a quarter 45 days after it ends.
YEARS = {"2019": {"npat": "1000000000", "eps": "1000", "equity": "10000000000"},
         "2020": {"npat": "2000000000", "eps": "2000", "equity": "20000000000"}}
QUARTERS = {"2020-Q3": {"npat": "500000000", "equity": "21000000000"},
            "2020-Q4": {"npat": "500000000", "equity": "22000000000"},
            "2021-Q1": {"npat": "1000000000", "equity": "25000000000"},
            # 2021-Q2 missing at the source
            "2021-Q3": {"npat": "-4000000000", "equity": "20000000000"}}


def record(years=YEARS, quarters=QUARTERS):
    return {"years": years, "quarters": quarters, "issues": [], "dividends": []}


def points(*pairs):
    return [(datetime.fromisoformat(d), v) for d, v in pairs]


def by_date(series):
    return {p["date"]: p for p in series["points"]}


def test_a_year_is_out_from_1_april_and_a_quarter_45_days_after_it_ends():
    assert published_from("2025") == date(2026, 4, 1)
    assert published_from("2026-Q1") == date(2026, 5, 15)
    assert published_from("2026-Q2") == date(2026, 8, 14)
    assert published_from("2026-Q3") == date(2026, 11, 14)
    assert published_from("2025-Q4") == date(2026, 2, 14)


def test_each_week_takes_its_last_close():
    out = weekly_multiples(record(), points(("2020-06-01", 10.0), ("2020-06-05", 12.0), ("2020-06-08", 14.0)), today=date(2021, 12, 1))
    assert [p["date"] for p in out["pe"]["points"]] == ["2020-06-05", "2020-06-08"]
    assert out["from"] == "2020-06-05" and out["to"] == "2020-06-08" and out["shares"] == 1000000


def test_annual_figures_stand_in_while_the_four_quarters_are_missing_and_the_gap_is_named():
    out = weekly_multiples(record(), points(("2020-06-05", 12.0)), today=date(2021, 12, 1))
    pe, pb = by_date(out["pe"])["2020-06-05"], by_date(out["pb"])["2020-06-05"]
    # 5 June 2020: 2020-Q1 is the latest quarter due (out 15 May); none of its four quarters are stored, so 2019 stands in.
    assert pe == {"date": "2020-06-05", "close": "12000", "value": "12.00", "basis": "năm", "period": "2019",
                  "denominator": "1000000000", "missing": ["2019-Q2", "2019-Q3", "2019-Q4", "2020-Q1"]}
    assert pb == {"date": "2020-06-05", "close": "12000", "value": "1.20", "basis": "năm", "period": "2019",
                  "denominator": "10000000000", "missing": ["2020-Q1"]}


def test_four_stored_quarters_give_the_trailing_profit_and_a_stored_quarter_its_equity():
    # 21 May 2021: 2021-Q1 is out; 2020-Q2 is not stored, so the trailing four quarters fall back to the 2020 annual figures.
    out = weekly_multiples(record(), points(("2021-05-21", 30.0)), today=date(2021, 12, 1))
    pe, pb = by_date(out["pe"])["2021-05-21"], by_date(out["pb"])["2021-05-21"]
    assert (pe["basis"], pe["period"], pe["missing"], pe["value"]) == ("năm", "2020", ["2020-Q2"], "15.00")
    assert (pb["basis"], pb["period"], pb["missing"], pb["value"]) == ("quý", "2021-Q1", [], "1.20")
    full = dict(QUARTERS, **{"2020-Q2": {"npat": "1000000000", "equity": "20000000000"}})
    pe = by_date(weekly_multiples(record(quarters=full), points(("2021-05-21", 30.0)), today=date(2021, 12, 1))["pe"])["2021-05-21"]
    assert (pe["basis"], pe["period"], pe["missing"], pe["denominator"], pe["value"]) == ("4 quý", "2021-Q1", [], "3000000000", "10.00")


def test_a_quarter_is_not_used_before_it_is_out():
    # 14 May 2021: 2021-Q1 is due the next day, so 2020-Q4 is the latest; its four quarters lack 2020-Q1 and 2020-Q2.
    out = weekly_multiples(record(), points(("2021-05-14", 30.0)), today=date(2021, 12, 1))
    pe, pb = by_date(out["pe"])["2021-05-14"], by_date(out["pb"])["2021-05-14"]
    assert (pe["basis"], pe["period"], pe["missing"]) == ("năm", "2020", [])  # 2020 annual = the four quarters to 2020-Q4
    assert (pb["basis"], pb["period"], pb["value"]) == ("quý", "2020-Q4", "1.36")


def test_the_annual_report_ends_the_same_window_as_the_fourth_quarter():
    # 1 March 2021: 2020-Q4 is out (14 Feb) but the 2020 annual report is not (1 April); 2019 stands in, and the gap is named.
    pe = by_date(weekly_multiples(record(), points(("2021-03-01", 30.0)), today=date(2021, 12, 1))["pe"])["2021-03-01"]
    assert (pe["basis"], pe["period"], pe["missing"]) == ("năm", "2019", ["2020-Q1", "2020-Q2"])


def test_a_loss_gives_no_pe_and_no_figures_give_no_point():
    loss = dict(QUARTERS, **{"2020-Q4": {"npat": "500000000", "equity": "22000000000"}, "2021-Q2": {"npat": "500000000", "equity": "21000000000"}})
    out = weekly_multiples(record(quarters=loss), points(("2021-11-19", 30.0)), today=date(2021, 12, 1))
    pe = by_date(out["pe"])["2021-11-19"]
    assert (pe["basis"], pe["period"], pe["denominator"], pe["value"]) == ("4 quý", "2021-Q3", "-2000000000", None)
    early = weekly_multiples(record(), points(("2019-06-07", 30.0), ("2020-06-05", 12.0)), today=date(2021, 12, 1))
    assert [p["date"] for p in early["pe"]["points"]] == ["2020-06-05"]  # nothing was out yet in June 2019


def test_the_summary_lists_every_missing_quarter_once():
    out = weekly_multiples(record(), points(("2020-06-05", 12.0), ("2021-03-01", 30.0), ("2021-05-21", 30.0)), today=date(2021, 12, 1))
    assert out["missing_quarters"] == ["2019-Q2", "2019-Q3", "2019-Q4", "2020-Q1", "2020-Q2"]


def test_without_statements_or_prices_there_is_a_reason():
    assert weekly_multiples({"years": {}, "quarters": {}}, [], today=date(2026, 1, 1))["reason"] == "Chưa có báo cáo tài chính"
    assert weekly_multiples(None, [], today=date(2026, 1, 1))["reason"] == "Chưa có báo cáo tài chính"
    out = weekly_multiples(record(), [], today=date(2026, 1, 1))
    assert out["reason"] == "Chưa có lịch sử giá" and out["pe"]["points"] == [] and out["missing_quarters"] == []
