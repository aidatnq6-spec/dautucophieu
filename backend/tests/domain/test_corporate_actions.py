from datetime import date
from decimal import Decimal

import pytest

from investment_agent.domain.ledger import LedgerError, parse_events, replay
from investment_agent.domain.positions import value_positions
from investment_agent.domain.settlement import OwnerAvailability, availability


def ev(event_id, event_type, day, seq=0, **fields):
    return {"event_id": event_id, "type": event_type, "effective_at": day, "sequence": seq, **fields}


BASE = [ev("d1", "deposit", "2026-03-02", amount="10000000"),
        {**ev("b1", "buy", "2026-03-03", security_id="ent-fpt", quantity=1000, price="5000", fee="0", tax="0"), "settlement_date": "2026-03-05"}]


def cash_entitlement(event_id="e1", day="2026-04-01", qty=1000, gross="1000000", tax="50000", action="act-div-1"):
    return ev(event_id, "cash_dividend_entitlement", day, action_id=action, security_id="ent-fpt", record_date="2026-04-02",
              payment_date="2026-04-20", eligible_quantity=qty, expected_gross=gross, expected_tax=tax)


def cash_payment(event_id="p1", day="2026-04-20", net="950000", tax="50000", action="act-div-1", seq=0):
    return ev(event_id, "cash_dividend_payment", day, seq, action_id=action, received_net=net, tax_withheld=tax)


def run(*events):
    return replay(parse_events([*BASE, *events]))


def holding(state):
    return next(h for h in state.positions if h.security_id == "ent-fpt")


def test_expected_cash_dividend_becomes_receivable_then_cash_without_double_income():
    accrued = run(cash_entitlement())
    assert (accrued.dividend_receivable, accrued.dividend_income, accrued.cash) == (Decimal(950_000), Decimal(950_000), Decimal(5_000_000))
    paid = run(cash_entitlement(), cash_payment())
    assert (paid.dividend_receivable, paid.dividend_income, paid.cash) == (Decimal(0), Decimal(950_000), Decimal(5_950_000))
    assert holding(paid).total_cost == Decimal(5_000_000)  # cash dividends never reduce cost


def test_actual_tax_differs_from_expected_and_adjustment_is_traced():
    paid = run(cash_entitlement(), cash_payment(net="900000", tax="100000"))
    assert paid.dividend_income == Decimal(900_000) and paid.dividend_receivable == 0
    assert [(a.action_id, a.amount) for a in paid.dividend_adjustments] == [("act-div-1", Decimal(-50_000))]


def test_ex_date_price_drop_is_not_a_loss_of_total_assets():
    before, after = run(), run(cash_entitlement())
    value_before = before.cash + value_positions(before, {"ent-fpt": Decimal(6_000)})[0].market_value
    # Price falls by the 1,000 VND gross dividend; the net amount is now a receivable.
    value_after = after.cash + after.dividend_receivable + value_positions(after, {"ent-fpt": Decimal(5_000)})[0].market_value
    assert value_before - value_after == Decimal(50_000)  # only the withheld tax


@pytest.mark.parametrize("events, code", [
    ([cash_payment()], "unknown_action"),
    ([cash_entitlement(), cash_payment(), cash_payment("p2", seq=1)], "action_already_settled"),
    ([cash_entitlement(), cash_entitlement("e2", day="2026-04-02")], "duplicate_action"),
    ([cash_entitlement(qty=1001)], "eligible_exceeds_holding"),
])
def test_inconsistent_dividend_events_rejected(events, code):
    with pytest.raises(LedgerError) as error:
        run(*events)
    assert error.value.code == code


def stock_entitlement(shares=200, day="2026-05-04"):
    return ev("se1", "stock_dividend_entitlement", day, action_id="act-bonus-1", security_id="ent-fpt",
              record_date="2026-05-05", eligible_quantity=1000, shares_entitled=shares)


def stock_credit(shares=200, cash_in_lieu="0", day="2026-06-10"):
    return ev("sc1", "stock_dividend_credit", day, action_id="act-bonus-1", shares_credited=shares, cash_in_lieu=cash_in_lieu)


def test_bonus_shares_keep_total_cost_and_are_not_cash_income():
    state = run(stock_entitlement())
    h = holding(state)
    assert (h.quantity, h.pending_quantity, h.total_cost, h.average_cost) == (1000, 200, Decimal(5_000_000), Decimal(5_000_000) / 1200)
    assert state.dividend_income == 0 and state.realized_gain == 0


def test_bonus_share_ex_date_dilution_is_not_a_loss():
    before, after = run(), run(stock_entitlement())
    value_before = value_positions(before, {"ent-fpt": Decimal(6_000)})[0].market_value
    value_after = value_positions(after, {"ent-fpt": Decimal(5_000)})[0].market_value  # 1,000 → 1,200 shares
    assert value_before == value_after == Decimal(6_000_000)


def test_pending_shares_cannot_be_sold_until_credited():
    with pytest.raises(LedgerError) as error:
        run(stock_entitlement(), ev("s1", "sell", "2026-05-20", security_id="ent-fpt", quantity=1100, price="6000", fee="0", tax="0"))
    assert error.value.code == "oversell"
    state = run(stock_entitlement(), stock_credit(), ev("s1", "sell", "2026-06-11", security_id="ent-fpt", quantity=1100, price="6000", fee="0", tax="0"))
    assert holding(state).quantity == 100 and holding(state).pending_quantity == 0


def test_credited_shares_replace_estimate_and_cash_in_lieu_is_recorded():
    state = run(stock_entitlement(shares=200), stock_credit(shares=199, cash_in_lieu="4500"))
    h = holding(state)
    assert (h.quantity, h.pending_quantity, h.total_cost) == (1199, 0, Decimal(5_000_000))
    assert state.cash == Decimal(5_004_500) and state.dividend_income == Decimal(4_500)


def test_selling_with_pending_shares_releases_cost_over_all_shares():
    state = run(stock_entitlement(), ev("s1", "sell", "2026-05-20", security_id="ent-fpt", quantity=600, price="6000", fee="0", tax="0"))
    assert holding(state).total_cost == Decimal(5_000_000) * 600 / 1200


def test_split_is_explicit_and_must_produce_whole_shares():
    state = run(ev("sp1", "share_split", "2026-07-01", action_id="act-split", security_id="ent-fpt", ratio_from=1, ratio_to=2))
    assert (holding(state).quantity, holding(state).total_cost) == (2000, Decimal(5_000_000))
    with pytest.raises(LedgerError) as error:
        run(ev("sp1", "share_split", "2026-07-01", action_id="act-split", security_id="ent-fpt", ratio_from=3, ratio_to=1))
    assert error.value.code == "fractional_split"


def test_unsupported_action_blocks_affected_security():
    state = run(ev("u1", "unsupported_action", "2026-07-01", action_id="act-rights", security_id="ent-fpt", kind="rights_issue"))
    assert holding(state).blocked_by == ("rights_issue",)


# --- settlement -------------------------------------------------------------

SALE = {**ev("s1", "sell", "2026-03-10", security_id="ent-fpt", quantity=400, price="6000", fee="2400", tax="2400"), "settlement_date": "2026-03-12"}


def test_sale_proceeds_are_not_buying_power_until_settled():
    events = parse_events([*BASE, SALE])
    pending = availability(events, as_of=date(2026, 3, 11))
    assert pending.accounting_cash == Decimal(7_395_200)
    assert pending.pending_sale_proceeds == Decimal(2_395_200)
    assert (pending.buying_power, pending.buying_power_basis) == (Decimal(5_000_000), "ledger_settlement_dates")
    settled = availability(events, as_of=date(2026, 3, 12))
    assert settled.buying_power == Decimal(7_395_200) and settled.pending_sale_proceeds == 0


def test_missing_settlement_date_leaves_buying_power_unknown():
    events = parse_events([*BASE, {**SALE, "settlement_date": None}])
    result = availability(events, as_of=date(2026, 3, 20))
    assert result.buying_power is None and result.buying_power_basis == "unknown"


def test_unsettled_buy_is_not_tradable_and_pending_stock_dividend_excluded():
    events = parse_events([*BASE, stock_entitlement(day="2026-03-04")])
    early = availability(events, as_of=date(2026, 3, 4))
    assert early.tradable["ent-fpt"] == 0
    later = availability(events, as_of=date(2026, 3, 5))
    assert later.tradable["ent-fpt"] == 1000


def test_owner_confirmed_availability_takes_precedence_for_the_same_day():
    events = parse_events([*BASE, {**SALE, "settlement_date": None}])
    confirmed = OwnerAvailability(as_of="2026-03-20", buying_power="7000000", tradable={"ent-fpt": 600})
    result = availability(events, as_of=date(2026, 3, 20), confirmed=confirmed)
    assert (result.buying_power, result.buying_power_basis, result.tradable["ent-fpt"]) == (Decimal(7_000_000), "owner_confirmed", 600)
    stale = availability(events, as_of=date(2026, 3, 21), confirmed=confirmed)
    assert stale.buying_power_basis == "unknown"


def test_owner_confirmation_cannot_exceed_ledger():
    events = parse_events(BASE)
    confirmed = OwnerAvailability(as_of="2026-03-20", buying_power="6000000", tradable={"ent-fpt": 1001})
    result = availability(events, as_of=date(2026, 3, 20), confirmed=confirmed)
    assert result.buying_power == Decimal(5_000_000) and result.tradable["ent-fpt"] == 1000
    assert set(result.warnings) == {"confirmed_cash_exceeds_ledger", "confirmed_quantity_exceeds_ledger"}
