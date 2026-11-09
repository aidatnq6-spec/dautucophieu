import json

from investment_agent.market.financial_ratios import FinancialRatioStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.services.quarter_alerts import quarter_alerts_run


def _setup(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nTCB\nHPG\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"FPT": "Công nghệ Thông tin", "TCB": "Ngân hàng", "HPG": "Tài nguyên Cơ bản"}}),
                                              encoding="utf-8")
    store = FundamentalsStore(tmp_path / "fundamentals")
    store.save({"symbol": "FPT", "fetched_at": "x", "source": "t", "years": {}, "dividends": [], "issues": [],
                "quarters": {"2025-Q3": {"npat": "2000000000000"}, "2026-Q2": {"npat": "2100000000000"}, "2026-Q3": {"npat": "2500000000000"}},
                "latest_quarter_seen": {"quarter": "2026-Q2", "on": "2026-07-28"}})
    store.save({"symbol": "TCB", "fetched_at": "x", "source": "t", "years": {}, "dividends": [], "issues": [],
                "quarters": {"2025-Q3": {"npat": "6000000000000"}, "2026-Q3": {"npat": "6371000000000"}},
                "latest_quarter_seen": {"quarter": "2026-Q2", "on": "2026-07-25"}})
    FinancialRatioStore(tmp_path / "financial-ratios").save({"symbol": "TCB", "kind": "bank", "fetched_at": "x", "source": "t", "quarters": {
        "2026-06-30": {"BAD_LOANS_RATIO_AQ": "0.0115"}, "2026-09-30": {"BAD_LOANS_RATIO_AQ": "0.0136"}}})
    return store


def test_the_first_run_records_what_is_there_without_sending_then_new_quarters_are_sent_once(tmp_path):
    store = _setup(tmp_path)
    sent_texts = []
    first = quarter_alerts_run(tmp_path, send=lambda t: sent_texts.append(t) or True)
    assert first == {"baseline": True, "alerts": 0, "sent": False} and sent_texts == []
    for sym in ("FPT", "TCB"):  # both report Q3 the next night
        r = store.read(sym)
        store.save({**r, "latest_quarter_seen": {"quarter": "2026-Q3", "on": "2026-10-31"}})
    out = quarter_alerts_run(tmp_path, send=lambda t: sent_texts.append(t) or True)
    assert out == {"baseline": False, "alerts": 2, "sent": True}
    text = sent_texts[0]
    assert "Báo cáo quý mới" in text
    assert "FPT · Q3/2026: LNST quý 2.500 tỷ (+25,0% so với cùng kỳ)" in text
    assert "TCB · Q3/2026: LNST quý 6.371 tỷ (+6,2% so với cùng kỳ) · NPL 1,36% (quý trước 1,15%)" in text
    assert "CAR quý" in text and "nhập nợ nhóm" not in text  # loan groups and CASA now come from Vietcap's notes by themselves
    assert quarter_alerts_run(tmp_path, send=lambda t: sent_texts.append(t) or True)["alerts"] == 0  # once only


def test_a_failed_send_is_retried_next_run_and_a_quarter_without_last_year_has_no_change(tmp_path):
    store = _setup(tmp_path)
    quarter_alerts_run(tmp_path, send=lambda t: True)
    r = store.read("FPT")
    store.save({**r, "quarters": {"2026-Q3": {"npat": "2500000000000"}}, "latest_quarter_seen": {"quarter": "2026-Q3", "on": "2026-10-31"}})
    assert quarter_alerts_run(tmp_path, send=lambda t: False) == {"baseline": False, "alerts": 1, "sent": False}
    texts = []
    assert quarter_alerts_run(tmp_path, send=lambda t: texts.append(t) or True)["sent"] is True
    assert "FPT · Q3/2026: LNST quý 2.500 tỷ (chưa có cùng kỳ năm trước)" in texts[0]


def _notes(group2: int, demand: int) -> dict:
    return {"loans": "1000", "group1": str(995 - group2), "group2": str(group2), "group3": "2", "group4": "1", "group5": "2",
            "deposits": "1000", "demand": str(demand), "term": str(980 - demand), "savings": "0", "margin": "20", "special": "0"}


def test_a_banks_note_scores_it_as_the_valuation_page_does_with_vietcaps_figures_and_entered_quarters(tmp_path):
    from investment_agent.api.auth import OwnerContext
    from investment_agent.market.bank_notes import BankNoteStore
    from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
    store = _setup(tmp_path)
    full = {"ROAA_TR_AVG4Q": "0.019", "BAD_LOANS_RATIO_AQ": "0.012", "OVERDUE_LOANS_RATIO_AQ": "0.02", "PROVISION_BAD_LOANS_AQ": "1.0",
            "NET_INTEREST_MARGIN_TR_AVG5Q": "0.037", "EQUITY_TO_ASSET_AQ": "0.09"}
    better = {"ROAA_TR_AVG4Q": "0.02", "BAD_LOANS_RATIO_AQ": "0.011", "OVERDUE_LOANS_RATIO_AQ": "0.019", "PROVISION_BAD_LOANS_AQ": "1.1",
              "NET_INTEREST_MARGIN_TR_AVG5Q": "0.038", "EQUITY_TO_ASSET_AQ": "0.095"}
    FinancialRatioStore(tmp_path / "financial-ratios").save({"symbol": "TCB", "kind": "bank", "fetched_at": "x", "source": "t",
                                                             "quarters": {"2025-09-30": full, "2026-09-30": better}})
    # Vietcap: CASA up, group 2 down, so all nine criteria are met.
    BankNoteStore(tmp_path / "bank-notes").save({"symbol": "TCB", "fetched_at": "2026-11-08T00:00:00+00:00", "source": "vietcap:iq", "car_years": {},
                                                 "quarters": {"2025-09-30": _notes(15, 300), "2026-09-30": _notes(12, 330)}})
    repo, owner = PersonalRepository("owner-1", MemoryDocumentStore()), OwnerContext("owner-1", "owner", "scheduler")
    quarter_alerts_run(tmp_path, send=lambda t: True, repo=repo, owner=owner)
    r = store.read("TCB")
    store.save({**r, "latest_quarter_seen": {"quarter": "2026-Q3", "on": "2026-10-31"}})
    texts = []

    def fail_once(t):
        texts.append(t)
        return False
    quarter_alerts_run(tmp_path, send=fail_once, repo=repo, owner=owner)
    assert "Điểm sức khỏe ngân hàng 9/9 (mạnh)" in texts[0]
    # A quarter the owner entered counts in place of Vietcap's, as on Định giá: CASA now falls.
    entered = {"group1": "950", "group2": "12", "group3": "2", "group4": "1", "group5": "2", "demand_deposits": "100", "margin_deposits": "10",
               "customer_deposits": "1000", "car": None}
    repo.write(owner, "settings", "bank_figures_TCB", {"symbol": "TCB", "quarters": {"2026-Q3": {"values": entered, "source": {"kind": "manual"}}}},
               expected_version=0, request_id="e1")
    quarter_alerts_run(tmp_path, send=fail_once, repo=repo, owner=owner)
    assert "Điểm sức khỏe ngân hàng 8/9" in texts[1]
