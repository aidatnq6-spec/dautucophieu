from datetime import date

from investment_agent.market.leading import MacroStore
from investment_agent.services.macro_signals import load_series, signals_run


def seed(tmp_path, oil_now="107.89"):
    store = MacroStore(tmp_path)
    store.upsert("factor_oil", [(date(2026, 9, 18), "100"), (date(2026, 10, 20), oil_now)], entry="auto")
    store.upsert("usd_vnd_free", [(date(2026, 10, 27), "26500")], entry="auto")
    store.upsert("usd_vnd_vcb", [(date(2026, 10, 27), "26020")], entry="auto")


def test_the_first_run_only_records_the_levels_then_a_change_is_sent_once(tmp_path):
    seed(tmp_path)
    sent = []
    first = signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: sent.append(text) or True)
    assert first["first_run"] is True and first["changes"] == 0 and sent == []
    assert first["levels"] == {"oil": "green", "usd": "missing", "fx_gap": "yellow", "foreign": "missing", "interbank": "missing"}
    assert signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: sent.append(text) or True)["changes"] == 0 and sent == []
    seed(tmp_path, oil_now="125")  # +25% in 30 days
    out = signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: sent.append(text) or True)
    assert out == {**out, "changes": 1, "sent": True, "first_run": False}
    assert len(sent) == 1 and "Giá dầu WTI: bình thường → nguy hiểm (+25,0% trong 30 ngày)" in sent[0] and "không phải khuyến nghị" in sent[0]
    assert signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: sent.append(text) or True)["changes"] == 0 and len(sent) == 1


def test_load_series_reads_the_six_stored_series(tmp_path):
    seed(tmp_path)
    series = load_series(tmp_path)
    assert set(series) == {"factor_oil", "factor_usd", "usd_vnd_free", "usd_vnd_vcb", "foreign_net", "vn_interbank_on"}
    assert str(series["factor_oil"][-1][1]) == "107.89"


def test_a_change_that_could_not_be_sent_is_tried_again(tmp_path):
    seed(tmp_path)
    signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: True)
    seed(tmp_path, oil_now="125")
    assert signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: False)["sent"] is False
    sent = []
    assert signals_run(tmp_path, today=date(2026, 10, 28), send=lambda text: sent.append(text) or True)["changes"] == 1 and len(sent) == 1
