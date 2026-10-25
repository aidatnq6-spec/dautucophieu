"""Synthetic published report shared by notification tests."""

REPORT = {"report_id": "ab" * 16, "session_date": "2026-10-23", "status": "published", "provenance": "synthetic", "report_version": "1",
          "decision": {"action": "hold", "headline": "Giữ phân bổ hiện tại", "reasons": ["outside_research_universe"]},
          "ledger_summary": {"cash": "95000000", "realized_gain": "0", "dividend_income": "0", "dividend_receivable": "0", "net_contributions": "100000000"},
          "holdings": [{"security_id": "FPT", "quantity": 100, "market_value": "6000000", "unrealized_gain": "1000000", "weight_of_capital": "0.006",
                        "price_date": "2026-10-23"}],
          "items": [{"entity_id": "FPT", "action": "hold", "reasons": ["outside_research_universe"]}],
          "narrative": {"source": "no_ai", "text": "Thị trường đi ngang."}, "verification_flags": ["universe_incomplete"], "sources": ["doc-1"]}
