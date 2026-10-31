from decimal import Decimal

from investment_agent.valuation.dividend_history import dividend_history

RECORD = {"years": {"2023": {"eps": "4000"}, "2024": {"eps": "5000"}, "2025": {"eps": "4500"}},
          "dividends": [{"date": "2024-05-31", "cash": "1000"}, {"date": "2025-05-23", "cash": "500"}, {"date": "2025-11-20", "cash": "500"},
                        {"date": "2026-06-15", "cash": "700"}],
          "share_issues": [{"date": "2024-05-31", "kind": "bonus", "ratio": "0.15"}, {"date": "2025-05-23", "kind": "bonus", "ratio": "0.1"},
                           {"date": "2025-06-05", "kind": "raise", "ratio": None}, {"date": "2026-06-15", "kind": "bonus", "ratio": None}]}


def test_each_year_sums_cash_and_stock_dividends_with_payout_against_the_previous_year_eps():
    from datetime import date
    out = dividend_history(RECORD, price=Decimal(20000), today=date(2026, 10, 31))
    years = {y["year"]: y for y in out["years"]}
    assert years["2025"] == {"year": "2025", "cash": "1000", "stock": "0.1", "eps_prev": "5000", "payout": "0.2000", "stock_note": None}
    assert years["2024"]["payout"] == "0.2500" and years["2024"]["stock"] == "0.15"
    assert years["2026"]["stock"] is None and years["2026"]["stock_note"] == "Có đợt thưởng hoặc cổ tức cổ phiếu chưa rõ tỷ lệ"
    assert years["2026"]["payout"] == "0.1556"  # 700 / EPS 2025 4.500
    assert [y["year"] for y in out["years"]] == ["2026", "2025", "2024"]  # newest first
    assert out["ttm"] == {"cash": "1200", "yield": "0.0600", "price": "20000", "since": "2025-10-31"}  # 500 (20/11/2025) + 700
    assert out["avg3"] == {"cash": "667", "years": ["2023", "2024", "2025"]}  # (0 + 1.000 + 1.000) / 3 full calendar years before 2026


def test_no_dividends_or_no_price_say_so():
    from datetime import date
    out = dividend_history({"years": {}, "dividends": [], "share_issues": []}, price=None, today=date(2026, 10, 31))
    assert out["years"] == [] and out["ttm"]["yield"] is None and out["reason"] == "Chưa có dữ liệu cổ tức"
