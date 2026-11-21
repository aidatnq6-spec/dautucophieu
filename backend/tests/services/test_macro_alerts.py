"""Nhắc vĩ mô (owner, 21/11/2026): Đèn tín hiệu rủi ro vĩ mô and Nhắc thanh khoản và tỷ giá often speak of the same overnight rate on
the same run; one Telegram message carries both, each part keeping its own state."""

from datetime import date

from investment_agent.market.leading import MacroStore
from investment_agent.services.macro_alerts import macro_alerts_run

TODAY = date(2026, 11, 10)


def seed(tmp_path, on: list[str], vcb="25500"):  # 25.500 is 2,9% under the 26.250 ceiling
    store = MacroStore(tmp_path)
    store.upsert("vn_interbank_on", [(date(2026, 11, 2 + i), v) for i, v in enumerate(on)], entry="auto")
    store.upsert("usd_vnd_central", [(date(2026, 11, 10), "25000")], entry="auto")
    store.upsert("usd_vnd_vcb", [(date(2026, 11, 10), vcb)], entry="auto")


def run(tmp_path, sent, ok=True):
    return macro_alerts_run(tmp_path, send=lambda text: sent.append(text) or ok, today=TODAY)


def test_a_light_change_and_a_liquidity_alert_of_the_same_run_go_in_one_message(tmp_path):
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0"])
    sent = []
    first = run(tmp_path, sent)  # the lights' first run only records the levels; nothing is new
    assert first["sent"] is False and sent == []
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0", "4.1", "7.2"])  # +3,2 points in 5 sessions, and red at 7%
    out = run(tmp_path, sent)
    assert out["sent"] is True and out["parts"] == ["signals", "liquidity"] and len(sent) == 1
    assert "ĐÈN TÍN HIỆU RỦI RO VĨ MÔ" in sent[0] and "Lãi suất liên ngân hàng qua đêm: xanh → đỏ" in sent[0]
    assert "Thanh khoản và tỷ giá" in sent[0] and "qua đêm tăng 3,2 điểm %" in sent[0]
    assert sent[0].count("không phải khuyến nghị") == 1
    assert run(tmp_path, sent)["sent"] is False and len(sent) == 1  # both parts remember they were sent


def test_one_part_alone_is_sent_alone(tmp_path):
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0"])
    run(tmp_path, [])
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0"], vcb="26200")  # near the ceiling; no light moved
    sent = []
    assert run(tmp_path, sent)["parts"] == ["liquidity"] and len(sent) == 1 and "ĐÈN TÍN HIỆU" not in sent[0]


def test_a_message_telegram_did_not_take_is_sent_again_whole(tmp_path):
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0"])
    run(tmp_path, [])
    seed(tmp_path, ["4.0", "4.0", "4.0", "4.0", "4.0", "4.0", "4.1", "7.2"])
    assert run(tmp_path, [], ok=False)["sent"] is False
    sent = []
    assert run(tmp_path, sent)["parts"] == ["signals", "liquidity"] and len(sent) == 1
