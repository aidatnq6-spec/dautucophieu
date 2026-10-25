import random
from datetime import date
from decimal import Decimal

import pytest

from investment_agent.domain.ledger import LedgerError, parse_events, replay
from investment_agent.domain.performance import performance
from investment_agent.domain.reconciliation import Change, apply_amendments, parse_amendments, snapshot_invalidated


def ev(event_id, event_type, day, seq=0, **fields):
    return {"event_id": event_id, "type": event_type, "effective_at": day, "sequence": seq, **fields}


def buy(event_id, qty, price, day, seq=0, security="ent-fpt", fee="0"):
    return ev(event_id, "buy", day, seq, security_id=security, quantity=qty, price=str(price), fee=fee, tax="0")


def sell(event_id, qty, price, day, seq=0, security="ent-fpt"):
    return ev(event_id, "sell", day, seq, security_id=security, quantity=qty, price=str(price), fee="0", tax="0")


EVENTS = [ev("d1", "deposit", "2026-01-02", amount="10000000"), buy("b1", 100, 20_000, "2026-01-05"),
          buy("b2", 100, 30_000, "2026-01-06"), sell("s1", 100, 28_000, "2026-01-07")]


def amend(amendment_id, action, target, replacement=None):
    return {"amendment_id": amendment_id, "action": action, "target_event_id": target, "replacement": replacement,
            "reason": "Sửa theo sao kê"}


def effective(events, amendments):
    return apply_amendments(parse_events(events), parse_amendments(amendments))


def test_backdated_correction_replays_from_affected_point():
    fixed = buy("b1", 100, 22_000, "2026-01-05")
    result = effective(EVENTS, [amend("a1", "replace", "b1", fixed)])
    state = replay(result.events)
    assert state.realized_gain == Decimal(28_000 * 100 - (22_000 * 100 + 30_000 * 100) / 2)
    assert result.audit[0].before["price"] == "20000" and result.audit[0].after["price"] == "22000"
    assert result.audit[0].affected_from == date(2026, 1, 5)


def test_moving_correction_earlier_marks_earlier_date_affected():
    moved = buy("b2", 100, 30_000, "2026-01-03")
    assert effective(EVENTS, [amend("a1", "replace", "b2", moved)]).audit[0].affected_from == date(2026, 1, 3)


def test_correction_equals_ledger_entered_correctly_first_time():
    fixed = buy("b1", 100, 22_000, "2026-01-05")
    corrected = replay(effective(EVENTS, [amend("a1", "replace", "b1", fixed)]).events)
    direct = replay(parse_events([EVENTS[0], fixed, *EVENTS[2:]]))
    assert corrected == direct


def test_cancel_is_restorable_and_history_kept():
    cancelled = effective(EVENTS[:3], [amend("a1", "cancel", "b2")])
    assert [e.event_id for e in cancelled.events] == ["d1", "b1"]
    restored = effective(EVENTS[:3], [amend("a1", "cancel", "b2"), amend("a2", "restore", "b2")])
    assert replay(restored.events) == replay(parse_events(EVENTS[:3]))
    assert [a.action for a in restored.audit] == ["cancel", "restore"]


def test_restore_after_replacement_restores_latest_replacement():
    fixed = buy("b2", 50, 30_000, "2026-01-06")
    result = effective(EVENTS[:3], [amend("a1", "replace", "b2", fixed), amend("a2", "cancel", "b2"), amend("a3", "restore", "b2")])
    assert result.events[-1].quantity == 50


@pytest.mark.parametrize("amendments, code", [
    ([amend("a1", "replace", "nope", buy("nope", 1, 1, "2026-01-05"))], "unknown_target"),
    ([amend("a1", "cancel", "b1"), amend("a1", "restore", "b1")], "duplicate_amendment"),
    ([amend("a1", "restore", "b1")], "not_cancelled"),
    ([amend("a1", "cancel", "b1"), amend("a2", "cancel", "b1")], "already_cancelled"),
    ([amend("a1", "cancel", "b1"), amend("a2", "replace", "b1", buy("b1", 1, 1, "2026-01-05"))], "already_cancelled"),
])
def test_invalid_amendment_sequences_rejected(amendments, code):
    with pytest.raises(LedgerError) as error:
        effective(EVENTS, amendments)
    assert error.value.code == code


@pytest.mark.parametrize("amendment", [
    amend("a1", "replace", "b1", buy("other", 1, 1, "2026-01-05")),
    amend("a1", "replace", "b1"),
    amend("a1", "cancel", "b1", buy("b1", 1, 1, "2026-01-05")),
])
def test_malformed_amendments_rejected(amendment):
    with pytest.raises(ValueError):
        parse_amendments([amendment])


def test_correction_creating_oversell_is_rejected_on_replay():
    smaller = buy("b1", 50, 20_000, "2026-01-05")  # with b2 cancelled, 50 held < 100 sold
    with pytest.raises(LedgerError) as error:
        replay(effective(EVENTS, [amend("a1", "cancel", "b2"), amend("a2", "replace", "b1", smaller)]).events)
    assert error.value.code == "oversell"


def test_snapshot_invalidation_by_later_change_affecting_its_date():
    changes = [Change(ledger_version=3, affected_from=date(2026, 1, 5))]
    assert snapshot_invalidated(as_of=date(2026, 1, 10), built_on_version=2, changes=changes)
    assert not snapshot_invalidated(as_of=date(2026, 1, 4), built_on_version=2, changes=changes)
    assert not snapshot_invalidated(as_of=date(2026, 1, 10), built_on_version=3, changes=changes)


# --- performance --------------------------------------------------------------

def test_deposits_are_not_profit():
    result = performance(parse_events([ev("d1", "deposit", "2026-01-02", amount="5000000")]), end_prices={})
    assert result.status == "complete" and result.total_gain == 0 and result.reconciliation_difference == 0


def test_reconciliation_oracle_with_dividend_receivable():
    events = parse_events([*EVENTS, ev("e1", "cash_dividend_entitlement", "2026-02-02", action_id="div", security_id="ent-fpt",
                                       record_date="2026-02-03", payment_date=None, eligible_quantity=100,
                                       expected_gross="100000", expected_tax="5000")])
    result = performance(events, end_prices={"ent-fpt": Decimal(26_000)})
    assert (result.realized_gain, result.unrealized_gain, result.dividend_income) == (Decimal(300_000), Decimal(100_000), Decimal(95_000))
    assert result.end_assets - result.start_assets - result.net_contributions == result.total_gain == Decimal(495_000)
    assert result.reconciliation_difference == 0
    assert result.return_measures == "not_calculated"


def test_opening_balance_separates_gain_before_tracking():
    events = parse_events([ev("o", "opening_balance", "2026-01-01", cash="1000000",
                              positions=[{"security_id": "ent-fpt", "quantity": 100, "total_cost": "2000000"}])])
    result = performance(events, start_prices={"ent-fpt": Decimal(25_000)}, end_prices={"ent-fpt": Decimal(27_000)})
    assert result.start_assets == Decimal(3_500_000) and result.end_assets == Decimal(3_700_000)
    assert result.unrealized_gain == Decimal(700_000) and result.unrealized_before_start == Decimal(500_000)
    assert result.total_gain == Decimal(200_000) and result.reconciliation_difference == 0


def test_missing_price_makes_performance_incomplete_not_zero():
    result = performance(parse_events(EVENTS), end_prices={})
    assert result.status == "incomplete" and result.unrealized_gain is None and result.end_assets is None
    assert result.missing_prices == ("ent-fpt",)


def test_blocked_security_makes_performance_blocked():
    events = parse_events([*EVENTS, ev("u", "unsupported_action", "2026-02-01", action_id="r", security_id="ent-fpt", kind="rights_issue")])
    assert performance(events, end_prices={"ent-fpt": Decimal(1)}).status == "blocked"


def test_random_chains_reconcile_and_corrections_match_direct_entry():
    rng = random.Random(7)
    for _ in range(25):
        events = [ev("d0", "deposit", "2026-01-01", amount=str(10**10))]
        held = 0
        for i in range(1, 30):
            day = date(2026, 1, 2 + i // 2).isoformat()
            if held and rng.random() < 0.4:
                n = rng.randint(1, held)
                events.append(sell(f"s{i}", n, rng.randint(1_000, 90_000), day, seq=i))
                held -= n
            else:
                n = rng.randint(1, 1_000)
                events.append(buy(f"b{i}", n, rng.randint(1_000, 90_000), day, seq=i, fee=str(rng.randint(0, 9_999))))
                held += n
        result = performance(parse_events(events), end_prices={"ent-fpt": Decimal(rng.randint(1_000, 90_000))})
        assert result.status == "complete" and abs(result.reconciliation_difference) < Decimal("0.000001")
        target = next(e for e in events if e["type"] == "buy")
        fixed = {**target, "fee": str(int(target["fee"]) + 1)}
        corrected = replay(effective(events, [amend("a", "replace", target["event_id"], fixed)]).events)
        direct = replay(parse_events([fixed if e is target else e for e in events]))
        assert corrected == direct
