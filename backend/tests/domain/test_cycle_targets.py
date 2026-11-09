from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from investment_agent.domain.cycle_targets import CycleTargets, compare_mix

MIX = {"deposit": "20", "bond": "5", "gold": "15", "stocks": "55", "crypto": "5"}
M = 1_000_000


def layer(i, amount):
    return {"id": i, "amount": str(amount * M)}


LAYERS = [layer("reserve", 100), layer("cash", 50), layer("deposit", 150), layer("bond", 0), layer("gold", 100), layer("stocks", 600), layer("crypto", 0)]  # base 900 tr


def rows(mix=MIX, base=900 * M):
    return {r["id"]: r for r in compare_mix(LAYERS, base=D(base), mix=CycleTargets.model_validate({"down": mix}).down)}


def test_each_layer_is_set_against_its_target_on_the_towers_base_with_deposits_counted_with_cash():
    r = rows()
    assert list(r) == ["deposit", "bond", "gold", "stocks", "crypto"]
    assert (r["deposit"]["held"], r["deposit"]["share"], r["deposit"]["target"]) == ("200000000", "0.2222", "0.2000")
    assert r["deposit"]["gap"] == "-20000000"  # 180 tr wanted, 200 tr held
    assert (r["gold"]["gap"], r["stocks"]["gap"], r["bond"]["gap"], r["crypto"]["gap"]) == ("35000000", "-105000000", "45000000", "45000000")


def test_the_gaps_cancel_out():
    assert sum(D(x["gap"]) for x in rows().values()) == 0


def test_with_nothing_above_the_reserve_there_is_no_share_or_gap():
    r = rows(base=0)
    assert r["gold"]["share"] is None and r["gold"]["gap"] is None and r["gold"]["target"] == "0.1500"


@pytest.mark.parametrize("bad", [{**MIX, "stocks": "54"}, {**MIX, "stocks": "101"}, {**MIX, "stocks": "-1"}, {k: v for k, v in MIX.items() if k != "gold"}])
def test_a_mix_must_have_every_layer_and_come_to_exactly_100(bad):
    with pytest.raises(ValidationError):
        CycleTargets.model_validate({"up": bad})


def test_a_phase_may_be_left_unset_and_decimals_are_allowed():
    t = CycleTargets.model_validate({"flat": {**MIX, "deposit": "19.5", "bond": "5.5"}})
    assert t.up is None and t.down is None and t.flat.deposit == D("19.5")
