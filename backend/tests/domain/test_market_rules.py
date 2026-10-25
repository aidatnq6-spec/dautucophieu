import json
from datetime import date
from decimal import Decimal

import pytest

from investment_agent.cli import load_calendar
from investment_agent.domain.market_rules import RULES_PATH, load_market_rules
from investment_agent.domain.pinned import CONFIG_DIR, InvalidPolicy

RULES = load_market_rules()


@pytest.mark.parametrize("price, tick", [("9990", "10"), ("10000", "50"), ("49950", "50"), ("50000", "100"), ("123400", "100")])
def test_tick_size_by_price_band(price, tick):
    assert RULES.tick_size(Decimal(price)) == Decimal(tick)


@pytest.mark.parametrize("price, valid", [("9995", False), ("10050", True), ("10020", False), ("50100", True), ("50150", False)])
def test_price_must_sit_on_a_tick(price, valid):
    assert RULES.is_valid_price(Decimal(price)) is valid


def test_ceiling_and_floor_round_inward_to_ticks():
    # 25,400 × 1.07 = 27,178 → down to 27,150; 25,400 × 0.93 = 23,622 → up to 23,650
    assert RULES.price_limits(Decimal(25_400)) == (Decimal(27_150), Decimal(23_650))


def test_round_lot_quantity_fits_amount_with_fees():
    # 10,000,000 VND at 25,000 with 0.15% fee: 398.8 shares affordable → 300 in round lots
    assert RULES.round_lot_shares(Decimal(10_000_000), Decimal(25_000), fee_rate=Decimal("0.0015")) == 300
    assert RULES.round_lot_shares(Decimal(2_000_000), Decimal(25_000), fee_rate=Decimal("0.0015")) == 0


def test_round_lot_order_is_capped():
    assert RULES.round_lot_shares(Decimal(10**13), Decimal(10_000), fee_rate=Decimal(0)) == 500_000


def test_sell_tax_is_on_sale_value():
    assert RULES.sell_tax(Decimal(28_000), 100) == Decimal("2800.000")


def test_every_figure_names_its_basis_and_status():
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    for key in ("round_lot", "tick_sizes", "daily_price_band", "settlement_cycle_days", "sell_tax_rate", "dividend_tax_rate"):
        assert data["sources"][key]["status"] and data["sources"][key]["basis"]
    assert RULES.statuses["settlement_cycle_days"] == "secondary_only"


def test_rules_file_is_pinned(tmp_path):
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    data["round_lot"] = 10
    path = tmp_path / "r.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidPolicy):
        load_market_rules(path)


def test_2026_calendar_matches_hose_notice():
    cal = load_calendar(CONFIG_DIR / "trading-calendar-hose-2026.json")
    closed = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 2, 16), date(2026, 2, 20), date(2026, 4, 27), date(2026, 4, 30),
              date(2026, 5, 1), date(2026, 8, 31), date(2026, 9, 2), date(2026, 1, 10), date(2026, 8, 22)]  # incl. make-up Saturdays
    assert not any(cal.is_session(d) for d in closed)
    assert all(cal.is_session(d) for d in (date(2026, 1, 5), date(2026, 2, 23), date(2026, 5, 4), date(2026, 9, 3)))
    holidays_on_weekdays = [d for d in cal.holidays if d.weekday() < 5]
    assert len(holidays_on_weekdays) == 13
