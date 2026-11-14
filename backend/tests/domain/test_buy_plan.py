from datetime import date
from decimal import Decimal

import pytest

from investment_agent.domain.buy_plan import PlanError, evaluate, plan_rows, validate

TODAY = date(2026, 11, 14)


def t(id, kind, value, status="waiting", symbol="FPT"):
    return {"id": id, "symbol": symbol, "amount": "20000000", "kind": kind, "value": value, "note": "", "status": status, "met_on": None, "met_value": None}


def test_a_tranche_needs_a_ticker_an_amount_and_a_condition_it_can_check():
    assert validate({"id": "a", "symbol": "fpt", "amount": "20000000", "kind": "price_le", "value": "90.5", "note": " đợt 1 "})["symbol"] == "FPT"
    for bad in ({"kind": "price_le", "value": "-1"}, {"kind": "report", "value": "2026-Q5"}, {"kind": "date", "value": "14/11/2026"}, {"kind": "guess", "value": "x"},
                {"amount": "0"}):
        with pytest.raises(PlanError):
            validate({"id": "a", "symbol": "FPT", "amount": "20000000", "kind": "price_le", "value": "90", **bad})


def test_conditions_are_checked_on_stored_data_and_each_is_met_once():
    plans = [t("p", "price_le", "90"), t("r", "report", "2026-Q3"), t("d", "date", "2026-11-20"), t("x", "price_le", "90", status="dropped"),
             t("n", "price_le", "90", symbol="HPG")]
    closes = {"FPT": (date(2026, 11, 13), Decimal("89.5"))}  # HPG has no stored close
    out, met = evaluate(plans, closes=closes, quarters={"FPT": {"2026-Q3"}}, today=TODAY)
    assert [m["id"] for m in met] == ["p", "r"]
    by = {p["id"]: p for p in out}
    assert by["p"]["status"] == "met" and by["p"]["met_on"] == "2026-11-14" and by["p"]["met_value"] == "89.5"
    assert by["r"]["met_value"] == "2026-Q3" and by["d"]["status"] == "waiting" and by["x"]["status"] == "dropped" and by["n"]["status"] == "waiting"
    again, met2 = evaluate(out, closes=closes, quarters={"FPT": {"2026-Q3"}}, today=TODAY)
    assert met2 == [] and again == out


def test_each_row_says_how_far_its_condition_is():
    rows = {r["id"]: r for r in plan_rows([t("p", "price_le", "90"), t("d", "date", "2026-11-20")], closes={"FPT": (date(2026, 11, 13), Decimal("100"))},
                                          today=TODAY)}
    assert rows["p"]["distance"] == "-0.1" and rows["p"]["close"] == "100" and rows["d"]["days_left"] == 6
