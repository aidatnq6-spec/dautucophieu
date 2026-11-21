import json
from datetime import date
from decimal import Decimal

from investment_agent.domain.asset_pyramid import asset_pyramid
from investment_agent.services.pyramid_alerts import pyramid_alerts_run

M = Decimal(1_000_000)
TODAY = date(2026, 11, 21)


def tower(**amounts):
    base = {"reserve": 100, "cash": 0, "deposit": 200, "bond": 50, "gold": 100, "stocks": 600, "crypto": 50}
    return asset_pyramid({k: Decimal(v) * M for k, v in {**base, **amounts}.items()}, deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))


def run(tmp_path, pyramid, ok=True):
    sent = []
    out = pyramid_alerts_run(tmp_path, pyramid=pyramid, send=lambda text: sent.append(text) or ok, today=TODAY)
    return out, sent


def test_the_first_run_only_records_the_layers(tmp_path):
    out, sent = run(tmp_path, tower())
    assert sent == [] and out == {"changes": 0, "sent": False}
    state = json.loads((tmp_path / "alerts" / "pyramid.json").read_text(encoding="utf-8"))
    assert state == {"bond": "ok", "crypto": "ok", "deposit": "ok", "gold": "ok", "stocks": "ok"}  # statuses only, no amounts


def test_a_layer_that_turns_short_or_over_or_back_is_said_once(tmp_path):
    run(tmp_path, tower())
    out, sent = run(tmp_path, tower(gold=50, deposit=250))  # gold 5% below 10–15%; deposits 25% still inside 10–30%
    assert out == {"changes": 1, "sent": True} and len(sent) == 1
    assert "Vàng: đủ → thiếu (5,0% phần sau dự phòng, mục tiêu 10–15%; thiếu 50.000.000 đ)" in sent[0]
    assert "không phải khuyến nghị" in sent[0].lower()
    assert run(tmp_path, tower(gold=50, deposit=250))[1] == []  # the same state again says nothing
    _, sent = run(tmp_path, tower())
    assert "Vàng: thiếu → đủ (10,0% phần sau dự phòng, mục tiêu 10–15%)" in sent[0]


def test_a_failed_send_is_tried_again_next_run(tmp_path):
    run(tmp_path, tower())
    out, _ = run(tmp_path, tower(gold=50, deposit=250), ok=False)
    assert out["sent"] is False
    _, sent = run(tmp_path, tower(gold=50, deposit=250))
    assert len(sent) == 1 and "Vàng: đủ → thiếu" in sent[0]


def test_no_tower_says_nothing_and_keeps_the_last_state(tmp_path):
    run(tmp_path, tower())
    out, sent = run(tmp_path, None)
    assert sent == [] and out == {"changes": 0, "sent": False}
    assert json.loads((tmp_path / "alerts" / "pyramid.json").read_text(encoding="utf-8"))["gold"] == "ok"
