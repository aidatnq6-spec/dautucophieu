import random
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest
from pydantic import ValidationError

from investment_agent.domain.ledger import LedgerError, parse_events, replay
from investment_agent.domain.positions import value_positions

DAY = "2026-01-05"


def ev(event_id, kind, day=DAY, seq=0, **fields):
    return {"event_id": event_id, "type": kind, "effective_at": day, "sequence": seq, **fields}


def deposit(event_id, amount, day=DAY, seq=0):
    return ev(event_id, "deposit", day, seq, amount=str(amount))


def trade(event_id, kind, qty, price, day=DAY, seq=0, fee=0, tax=0, security="ent-fpt"):
    return ev(event_id, kind, day, seq, security_id=security, quantity=qty, price=str(price), fee=str(fee), tax=str(tax))


def run(*events):
    return replay(parse_events(list(events)))


def holding(state, security="ent-fpt"):
    return next(h for h in state.positions if h.security_id == security)


def test_moving_average_oracle_without_fees():
    state = run(deposit("d1", 10_000_000), trade("b1", "buy", 100, 20_000, seq=1),
                trade("b2", "buy", 100, 30_000, seq=2), trade("s1", "sell", 100, 28_000, seq=3))
    assert state.realized_gain == Decimal(300_000)
    h = holding(state)
    assert (h.quantity, h.total_cost, h.average_cost) == (100, Decimal(2_500_000), Decimal(25_000))
    assert state.cash == Decimal(10_000_000 - 2_000_000 - 3_000_000 + 2_800_000)


def test_buy_fee_enters_cost_and_sell_fee_tax_reduce_proceeds():
    state = run(deposit("d1", 10_000_000), trade("b1", "buy", 100, 20_000, seq=1, fee=3_000),
                trade("s1", "sell", 40, 25_000, seq=2, fee=1_500, tax=1_000))
    h = holding(state)
    assert h.total_cost == Decimal(2_003_000) * 60 / 100
    assert state.realized_gain == Decimal(1_000_000 - 1_500 - 1_000) - Decimal(2_003_000) * 40 / 100
    assert state.cash == Decimal(10_000_000 - 2_003_000 + 1_000_000 - 2_500)
    assert (state.fees_paid, state.taxes_paid) == (Decimal(4_500), Decimal(1_000))


def test_selling_does_not_change_unit_cost_of_remaining_shares():
    state = run(deposit("d1", 10_000_000), trade("b1", "buy", 300, 10_000, seq=1, fee=900),
                trade("s1", "sell", 100, 50_000, seq=2))
    assert holding(state).average_cost == Decimal(3_000_900) / 300


def test_full_sale_releases_exact_remaining_cost():
    state = run(deposit("d1", 1_000_000), trade("b1", "buy", 3, 100_000, seq=1, fee=1),
                trade("s1", "sell", 1, 100_000, seq=2), trade("s2", "sell", 2, 100_000, seq=3))
    assert state.positions == ()
    assert state.realized_gain == Decimal(-1)


def test_full_sale_after_rounded_partial_sale_leaves_no_residual_cost():
    # 600001 / 6 does not terminate; proportional release of the last 5 shares would round differently.
    state = run(deposit("d1", 1_000_000), trade("b1", "buy", 6, 100_000, seq=1, fee=1),
                trade("s1", "sell", 1, 100_000, seq=2), trade("s2", "sell", 5, 100_000, seq=3))
    assert state.positions == () and state.realized_gain == Decimal(-1)


def test_deposits_and_withdrawals_are_contributions_not_gains():
    state = run(deposit("d1", 5_000_000), ev("w1", "withdrawal", seq=1, amount="1000000"))
    assert (state.cash, state.realized_gain, state.net_contributions) == (Decimal(4_000_000), 0, Decimal(4_000_000))


def test_opening_balance_starts_tracking_without_inventing_history():
    opening = ev("open", "opening_balance", "2026-01-01", cash="1000000",
                 positions=[{"security_id": "ent-fpt", "quantity": 200, "total_cost": "4000000"}])
    state = run(opening, trade("s1", "sell", 100, 30_000, day="2026-01-02"))
    assert state.started_on.isoformat() == "2026-01-01" and state.realized_before_start_unknown is True
    assert state.realized_gain == Decimal(1_000_000) and state.cash == Decimal(4_000_000)
    assert state.net_contributions == Decimal(0)


@pytest.mark.parametrize("events, code", [
    ([trade("s1", "sell", 1, 10_000)], "oversell"),
    ([deposit("d1", 1_000_000), trade("b1", "buy", 10, 10_000, seq=1), trade("s1", "sell", 11, 10_000, seq=2)], "oversell"),
    ([deposit("d1", 100), trade("b1", "buy", 1, 10_000, seq=1)], "cash_negative"),
    ([deposit("d1", 100), ev("w1", "withdrawal", seq=1, amount="101")], "cash_negative"),
    ([deposit("d1", 100), deposit("d1", 100, seq=1)], "duplicate_event"),
    ([deposit("d1", 100), deposit("d2", 100)], "ambiguous_order"),
    ([deposit("d1", 100, day="2025-12-31"), ev("open", "opening_balance", "2026-01-01", cash="0", positions=[])], "before_opening_balance"),
    ([ev("o1", "opening_balance", cash="0", positions=[]), ev("o2", "opening_balance", seq=1, cash="0", positions=[])], "multiple_opening_balances"),
])
def test_impossible_or_ambiguous_ledgers_are_rejected(events, code):
    with pytest.raises(LedgerError) as error:
        run(*events)
    assert error.value.code == code


@pytest.mark.parametrize("bad", [
    trade("b1", "buy", -1, 10_000), trade("b1", "buy", 0, 10_000), trade("b1", "buy", 1.5, 10_000),
    trade("b1", "buy", 1, 0), trade("b1", "buy", 1, 10_000, fee=-1), ev("d1", "deposit", amount=100.0),
    ev("d1", "deposit", amount="0"), ev("d1", "dividend", amount="1"), {**deposit("d1", 1), "sequence": -1},
])
def test_invalid_event_fields_are_rejected(bad):
    with pytest.raises(ValidationError):
        parse_events([bad])


def test_input_order_does_not_matter_only_effective_order():
    events = [deposit("d1", 10_000_000), trade("b1", "buy", 100, 20_000, seq=1), trade("s1", "sell", 50, 21_000, day="2026-01-06")]
    assert run(*events) == run(*reversed(events))


def test_long_random_chain_matches_independent_fraction_oracle():
    rng = random.Random(20261025)
    events, cash, qty, cost, realized = [deposit("d0", 10**12)], Fraction(10**12), 0, Fraction(0), Fraction(0)
    for i in range(1, 400):
        day = (date(2026, 1, 5) + timedelta(days=i // 3)).isoformat()
        price, fee = rng.randint(1_000, 150_000), rng.randint(0, 50_000)
        if qty and rng.random() < 0.45:
            n = rng.randint(1, qty)
            tax = rng.randint(0, 9_999)
            out = cost if n == qty else cost * n / qty
            realized += n * price - fee - tax - out
            cost, qty, cash = cost - out, qty - n, cash + n * price - fee - tax
            events.append(trade(f"s{i}", "sell", n, price, day=day, seq=i, fee=fee, tax=tax))
        else:
            n = rng.randint(1, 5_000)
            cost, qty, cash = cost + n * price + fee, qty + n, cash - n * price - fee
            events.append(trade(f"b{i}", "buy", n, price, day=day, seq=i, fee=fee))
    state = run(*events)
    assert state.cash == Decimal(cash.numerator) / cash.denominator  # cash is whole VND, exact
    assert abs(state.realized_gain - Decimal(realized.numerator) / realized.denominator) < Decimal("0.000001")
    remaining = holding(state).total_cost if qty else Decimal(0)
    bought = sum(Decimal(e["quantity"]) * Decimal(e["price"]) + Decimal(e["fee"]) for e in events if e["type"] == "buy")
    proceeds = sum(Decimal(e["quantity"]) * Decimal(e["price"]) - Decimal(e["fee"]) - Decimal(e["tax"]) for e in events if e["type"] == "sell")
    # Division rounding stays inside the ledger: cost bought = cost remaining + cost released by sales.
    assert remaining + (proceeds - state.realized_gain) == bought


def test_valuation_marks_missing_price_instead_of_zero():
    state = run(deposit("d1", 10_000_000), trade("b1", "buy", 100, 20_000, seq=1), trade("b2", "buy", 10, 50_000, seq=2, security="ent-vnm"))
    rows = {r.security_id: r for r in value_positions(state, {"ent-fpt": Decimal(25_000)})}
    assert (rows["ent-fpt"].market_value, rows["ent-fpt"].unrealized_gain, rows["ent-fpt"].quality_status) == (Decimal(2_500_000), Decimal(500_000), "verified")
    assert (rows["ent-vnm"].market_value, rows["ent-vnm"].unrealized_gain, rows["ent-vnm"].quality_status) == (None, None, "missing")
