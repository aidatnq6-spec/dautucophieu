from datetime import date

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.statements import StatementStore
from investment_agent.valuation.sources import publication_dates, valuation_record

FUND = {"symbol": "HPG", "fetched_at": "2026-11-01T00:00:00+00:00", "source": "t",
        "years": {"2025": {"npat": "1000000000", "eps": "1000", "equity": "10000000000"}},
        "quarters": {"2026-Q2": {"npat": "250000000", "equity": "11000000000"}}, "dividends": [], "issues": []}
STATEMENTS = {"symbol": "HPG", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo",
              "quarters": {"2015-Q1": {"npat_parent": "100", "equity": "1000", "minority_equity": "10"},
                           "2026-Q2": {"npat_parent": "300", "npat": "320", "equity": "2000", "minority_equity": "50"},
                           "2026-Q3": {"npat": "330"}},  # no parent profit or equity: left out, not filled
              "years": {"2025": {"npat_parent": "1200", "equity": "1900", "minority_equity_outside": "40"}},
              "quarters_created": {"2015-Q1": "2019-12-01", "2026-Q2": "2026-07-18", "2026-Q3": "2026-10-29"},
              "years_created": {"2025": "2026-01-30"}}


def test_vndirect_parent_profit_and_parent_equity_feed_the_series_when_the_ticker_has_them(tmp_path):
    FundamentalsStore(tmp_path / "fundamentals").save(FUND)
    StatementStore(tmp_path / "statements").save(STATEMENTS)
    out = valuation_record(tmp_path, "HPG", today=date(2026, 11, 7))
    assert out["source"] == "vndirect" and out["shares"] == 1000000  # today's share count still from the reference valuation
    assert out["record"]["quarters"] == {"2015-Q1": {"npat": "100", "equity": "990"}, "2026-Q2": {"npat": "300", "equity": "1950"}}
    assert out["record"]["years"] == {"2025": {"npat": "1200", "equity": "1900"}}  # before 2015 minorities sat outside equity


def test_without_vndirect_statements_the_free_vnstock_figures_and_the_fixed_rule_stay(tmp_path):
    FundamentalsStore(tmp_path / "fundamentals").save(FUND)
    out = valuation_record(tmp_path, "HPG", today=date(2026, 11, 7))
    assert out["source"] == "vnstock" and out["record"]["quarters"] == FUND["quarters"] and out["published"] is None
    assert valuation_record(tmp_path, "ZZZ", today=date(2026, 11, 7))["record"] is None


def test_a_period_counts_as_out_from_the_day_vndirect_listed_it_when_that_is_within_120_days_of_its_end():
    pub = publication_dates(STATEMENTS)
    assert pub("2026-Q2") == date(2026, 7, 18)  # earlier than the 45-day rule (14 August)
    assert pub("2026-Q3") == date(2026, 10, 29)
    assert pub("2025") == date(2026, 1, 30)
    assert pub("2015-Q1") == date(2015, 5, 15)  # 2019-12-01 is VNDirect's loading day for old figures: the 45-day rule stays
    assert pub("2024-Q4") == date(2025, 2, 14)  # no day listed: the rule


def test_a_listed_day_after_the_rule_is_kept_so_a_late_report_is_not_used_early():
    pub = publication_dates({"quarters_created": {"2026-Q1": "2026-06-20"}, "years_created": {}})
    assert pub("2026-Q1") == date(2026, 6, 20)  # the rule would say 15 May
