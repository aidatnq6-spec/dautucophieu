from datetime import date

from investment_agent.market.leading import MacroStore
from investment_agent.services.liquidity_alerts import check_liquidity


def seed(tmp_path, on: list[str], central="25000", vcb="26000"):
    store = MacroStore(tmp_path)
    store.upsert("vn_interbank_on", [(date(2026, 11, 2 + i), v) for i, v in enumerate(on)], entry="auto")
    store.upsert("usd_vnd_central", [(date(2026, 11, 10), central)], entry="auto")
    store.upsert("usd_vnd_vcb", [(date(2026, 11, 10), vcb)], entry="auto")


def run(tmp_path, sent, ok=True):
    return check_liquidity(tmp_path, send=lambda text: sent.append(text) or ok, today=date(2026, 11, 10))


def test_a_jump_and_a_rate_near_the_ceiling_are_each_sent_once_while_they_last(tmp_path):
    seed(tmp_path, ["4.0", "4.1", "4.2", "4.4", "4.8", "5.2"], vcb="26200")  # ceiling 26250: 0,19% left
    sent = []
    assert run(tmp_path, sent) == {"status": "ok", "new": 2, "sent": True}
    assert "qua đêm tăng 1,2 điểm %" in sent[0] and "5,2%" in sent[0] and "còn 0,19% tới trần 26.250" in sent[0]
    assert run(tmp_path, sent) == {"status": "ok", "new": 0, "sent": False} and len(sent) == 1  # still true: not again


def test_an_alert_comes_again_only_after_it_cleared(tmp_path):
    seed(tmp_path, ["4.0", "4.1", "4.2", "4.4", "4.8", "5.2"])
    sent = []
    run(tmp_path, sent)
    seed(tmp_path, ["4.0", "4.1", "4.2", "4.4", "4.8", "5.2", "4.5"])  # the jump is over
    assert run(tmp_path, sent)["new"] == 0
    seed(tmp_path, ["4.0", "4.1", "4.2", "4.4", "4.8", "5.2", "4.5", "6.5"])  # 6,5 against 4,2 five sessions before
    assert run(tmp_path, sent)["new"] == 1 and len(sent) == 2


def test_nothing_is_marked_when_telegram_did_not_take_the_note(tmp_path):
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0"], vcb="26200")
    sent = []
    assert run(tmp_path, sent, ok=False) == {"status": "ok", "new": 1, "sent": False}
    assert run(tmp_path, sent)["sent"] is True and len(sent) == 2
    assert run(tmp_path, [])["new"] == 0
