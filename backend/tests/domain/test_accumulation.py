from datetime import date
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from investment_agent.domain.accumulation import Accumulation, due_plans, plan_status

TODAY = date(2026, 11, 9)
GOLD = {"id": "g", "name": "Vàng nhẫn", "asset": "gold", "day": 10, "start": "2026-09", "chi": "1", "kind": "Nhẫn"}
FUND = {"id": "f", "name": "Quỹ VFF", "asset": "fund", "day": 5, "start": "2026-10", "amount": "13000000", "fund": "VFF"}
BUYS = [{"id": "1", "plan": "g", "on": "2026-09-12", "amount": "12000000", "quantity": "1"}, {"id": "2", "plan": "g", "on": "2026-10-11", "amount": "6500000", "quantity": "0.5"},
        {"id": "3", "plan": "f", "on": "2026-10-06", "amount": "13000000", "quantity": "500"}, {"id": "4", "plan": "f", "on": "2026-11-06", "amount": "13000000", "quantity": "400"}]
QUOTES = {"gold": {"kinds": {"Nhẫn": {"buy": "14000000"}}, "as_of": "2026-11-09T08:00:00+07:00"}, "funds": {"VFF": {"nav": "30000", "date": "2026-11-01"}}}


def data(plans=(GOLD, FUND), buys=BUYS):
    return Accumulation.model_validate({"plans": list(plans), "buys": list(buys)})


def status(i=0, quotes=QUOTES, today=TODAY, d=None):
    d = d or data()
    return plan_status(d.plans[i], d.buys, quotes, today=today)


def test_gold_is_followed_month_by_month_in_chi():
    s = status()
    assert [(m["month"], m["got"], m["status"], m["short_by"]) for m in s["months"]] == [("2026-09", "1", "met", None), ("2026-10", "0.5", "short", "0.5"), ("2026-11", "0", "pending", None)]
    assert s["streak"] == 0


def test_a_fund_is_followed_in_money_and_the_streak_counts_months_met():
    s = status(1)
    assert [m["status"] for m in s["months"]] == ["met", "met"] and s["streak"] == 2


def test_average_cost_and_value_come_from_what_was_bought_and_the_public_price():
    s = status()
    assert (s["cost"], s["quantity"], s["average"]) == ("18500000", "1.5", "12333333")
    assert (s["price"], s["value"], s["change"], s["price_reason"]) == ("14000000", "21000000", "2500000", None)
    f = status(1)
    assert (f["average"], f["value"], f["price_on"]) == ("28889", "27000000", "2026-11-01")  # 26 tr / 900 đơn vị; 900 × 30.000


@pytest.mark.parametrize("plan,reason", [({**GOLD, "kind": None}, "no_kind"), ({**GOLD, "kind": "Không có"}, "no_price")])
def test_without_a_public_price_no_value_is_given(plan, reason):
    s = status(d=data(plans=(plan,), buys=BUYS[:2]))
    assert s["price"] is None and s["value"] is None and s["change"] is None and s["price_reason"] == reason and s["average"] == "12333333"


def test_no_buys_means_no_average():
    s = status(d=data(plans=(GOLD,), buys=()))
    assert s["average"] is None and s["cost"] == "0" and s["value"] is None and s["price_reason"] == "no_buys"


def test_only_the_current_month_past_its_day_and_short_is_due():
    assert [p.id for p, _ in due_plans(data(), QUOTES, today=TODAY)] == []  # gold before day 10, the fund is met
    assert [p.id for p, _ in due_plans(data(), QUOTES, today=date(2026, 11, 10))] == ["g"]


@pytest.mark.parametrize("bad", [{"plans": [{**GOLD, "chi": None}], "buys": []}, {"plans": [{**FUND, "amount": None}], "buys": []}, {"plans": [{**GOLD, "amount": "1000"}], "buys": []},
                                 {"plans": [{**GOLD, "day": 29}], "buys": []}, {"plans": [GOLD], "buys": [{**BUYS[0], "plan": "x"}]}, {"plans": [GOLD], "buys": [{**BUYS[0], "quantity": "0"}]},
                                 {"plans": [GOLD, GOLD], "buys": []}])
def test_bad_plans_and_buys_are_refused(bad):
    with pytest.raises(ValidationError):
        Accumulation.model_validate(bad)


def test_a_buy_before_the_plan_starts_counts_in_the_cost_and_is_counted_apart():
    early = {"id": "9", "plan": "g", "on": "2026-08-20", "amount": "10000000", "quantity": "1"}
    s = status(d=data(plans=(GOLD,), buys=(*BUYS[:2], early)))
    assert s["before_start"] == 1 and s["quantity"] == "2.5" and [m["month"] for m in s["months"]][0] == "2026-09"
    assert status()["before_start"] == 0
