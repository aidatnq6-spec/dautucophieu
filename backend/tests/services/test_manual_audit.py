from datetime import date

from investment_agent.market.leading import MacroStore
from investment_agent.services.manual_audit import audit_manual

SPECS = [{"id": "vn_pmi", "label": "PMI sản xuất Việt Nam", "period": "month"},
         {"id": "vn10y", "label": "Lợi suất TPCP 10 năm", "period": "session"},
         {"id": "deposit_12m", "label": "Lãi suất huy động 12 tháng"}]


def test_hand_entries_that_break_the_rules_are_listed_with_why(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("vn_pmi", [(date(2026, 9, 30), "51.9")], entry="auto")
    store.upsert("vn_pmi", [(date(2026, 10, 25), "51.9")], entry="manual")   # a typing day, and the same as September's figure
    store.upsert("vn_pmi", [(date(2026, 8, 31), "53.3")], entry="manual")    # month end: fine
    store.upsert("vn10y", [(date(2026, 10, 23), "4.49")], entry="auto")
    store.upsert("vn10y", [(date(2026, 10, 25), "4.58")], entry="manual")    # a Sunday
    store.upsert("vn10y", [(date(2026, 10, 22), "4.48")], entry="manual")    # a session: fine
    store.upsert("deposit_12m", [(date(2026, 10, 1), "5.6")], entry="auto")
    store.upsert("deposit_12m", [(date(2026, 10, 2), "5.7")], entry="manual")  # a day of its own: fine
    found = audit_manual(tmp_path, SPECS)
    assert found == [
        {"indicator": "vn_pmi", "label": "PMI sản xuất Việt Nam", "date": "2026-10-25", "value": "51.9",
         "reasons": ["không ghi vào ngày cuối tháng", "trùng giá trị với số tự động ngày 30/09/2026"]},
        {"indicator": "vn10y", "label": "Lợi suất TPCP 10 năm", "date": "2026-10-25", "value": "4.58", "reasons": ["ngày không có phiên giao dịch"]},
    ]


def test_a_hand_entry_beside_an_automatic_figure_of_the_same_period_is_listed(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("vn_pmi", [(date(2026, 10, 31), "52.3")], entry="auto")
    store.upsert("deposit_12m", [(date(2026, 10, 1), "5.6")], entry="auto")
    # a hand figure later replaced by the source's on the same day is fine: the store keeps one figure a day
    assert audit_manual(tmp_path, SPECS) == []
    MacroStore(tmp_path).upsert("vn_pmi", [(date(2026, 10, 30), "52.0")], entry="manual")
    found = audit_manual(tmp_path, SPECS)
    assert found[0]["reasons"] == ["không ghi vào ngày cuối tháng", "cùng tháng đã có số tự động 52,3 (31/10/2026)"]
