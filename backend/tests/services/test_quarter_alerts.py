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
    assert "nhập nợ nhóm 1–5, CASA, CAR trên trang mã TCB" in text
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
