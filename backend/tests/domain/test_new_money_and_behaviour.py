from datetime import date
from decimal import Decimal as D

from investment_agent.domain.asset_pyramid import new_money
from investment_agent.domain.trade_behaviour import merge_files, trade_behaviour

M = 1_000_000
BASE = {"reserve": D(100 * M), "cash": D(0), "deposit": D(400 * M), "bond": D(0), "gold": D(0), "stocks": D(500 * M), "crypto": D(0)}  # base 900 tr; stocks 50%


def plan(amount, amounts=BASE, short=D(0)):
    return new_money(amounts, deductions=D(100 * M), stock_ratio=D("0.5"), amount=D(amount * M), reserve_short=short)


def steps(p):
    return [(s["id"], int(D(s["amount"])) // M, s["why"]) for s in p["steps"]]


def test_the_money_goes_to_the_lowest_short_layer_first():
    assert steps(plan(100)) == [("gold", 100, "short")]  # base 1.000 tr: gold needs 100 tr to reach 10%, and takes it all


def test_after_the_minimums_stocks_fill_to_their_ceiling_and_deposits_take_the_rest():
    p = plan(300)  # base 1.200 tr: gold 120 to 10%; stocks 40 to 45%, then 60 to 50%; the last 80 to deposits
    assert steps(p) == [("gold", 120, "short"), ("stocks", 40, "short"), ("stocks", 60, "room"), ("deposit", 80, "rest")]
    assert p["allocated"] == format(D(300 * M), "f")


def test_a_lower_layer_short_stops_the_money_reaching_those_above():
    thin = {**BASE, "deposit": D(0), "stocks": D(900 * M)}  # base 900 tr; deposits need 20%
    assert steps(plan(100, thin)) == [("deposit", 100, "short")]


def test_a_reserve_that_cannot_be_withdrawn_now_comes_before_every_layer():
    assert steps(plan(100, short=D(30 * M))) == [("reserve", 30, "reserve"), ("gold", 70, "short")]


def test_a_stock_layer_past_its_ceiling_gets_nothing_more():
    heavy = {**BASE, "gold": D(200 * M), "deposit": D(300 * M), "stocks": D(900 * M)}  # base with the new money 1.500 tr: stocks ceiling 750 tr, already 900 tr
    result = steps(plan(100, heavy))
    assert all(i != "stocks" for i, _, _ in result) and sum(a for _, a, _ in result) == 100


def test_every_dong_is_placed_and_the_layers_after_are_shown():
    p = plan(300)
    assert sum(D(s["amount"]) for s in p["steps"]) == D(300 * M)
    after = {l["id"]: l for l in p["after"]}
    assert after["gold"]["status"] == "ok" and after["stocks"]["amount"] == format(D(600 * M), "f")


def o(symbol, day, kind, qty, price, fee="0", tax="0", order="1", line=1):
    return {"symbol": symbol, "date": day, "type": kind, "quantity": qty, "price": price, "fee": fee, "tax": tax, "order_no": order, "line": line}


ORDERS = [o("AAA", date(2025, 1, 1), "buy", 100, "10000", fee="15", order="1"), o("AAA", date(2025, 3, 1), "buy", 100, "20000", fee="30", order="2"),
          o("AAA", date(2025, 4, 1), "sell", 150, "30000", fee="67", tax="450", order="3")]


def test_each_year_counts_orders_money_and_costs():
    y = trade_behaviour(ORDERS)["years"][0]
    assert (y["year"], y["orders"], y["buys"], y["sells"], y["symbols"]) == (2025, 3, 2, 1, 1)
    assert (y["buy_value"], y["sell_value"], y["fee"], y["tax"], y["costs"]) == ("3000000", "4500000", "112", "450", "562")
    assert y["cost_share"] == "0.0001"  # 562 / 7.500.000


def test_holding_time_is_first_in_first_out_weighted_by_shares():
    y = trade_behaviour(ORDERS)["years"][0]
    assert y["avg_hold_days"] == "70.3"  # 100 shares for 90 days, 50 for 31
    assert (y["held_short"], y["held_mid"], y["held_long"]) == ("0.0000", "1.0000", "0.0000")


def test_the_holding_bands_split_at_30_and_180_days():
    orders = [o("AAA", date(2025, 1, 1), "buy", 300, "1"), o("AAA", date(2025, 1, 31), "sell", 100, "1"), o("AAA", date(2025, 6, 30), "sell", 100, "1"), o("AAA", date(2025, 7, 1), "sell", 100, "1")]
    y = trade_behaviour(orders)["years"][0]  # 30, 180 and 181 days
    assert (y["held_short"], y["held_mid"], y["held_long"]) == ("0.3333", "0.3333", "0.3333")


def test_a_ticker_sold_beyond_its_bought_shares_is_named_and_left_out_of_holding_time_only():
    r = trade_behaviour([*ORDERS, o("BBB", date(2025, 5, 1), "sell", 10, "1000", order="9")])
    assert r["no_holding_time"] == ["BBB"]
    y = r["years"][0]
    assert y["orders"] == 4 and y["sell_value"] == "4510000" and y["avg_hold_days"] == "70.3"


def test_shares_bought_on_the_day_of_a_sale_are_not_the_ones_sold():
    orders = [o("AAA", date(2025, 1, 1), "buy", 10, "1"), o("AAA", date(2025, 2, 1), "buy", 10, "1", line=1), o("AAA", date(2025, 2, 1), "sell", 10, "1", line=2)]
    assert trade_behaviour(orders)["years"][0]["avg_hold_days"] == "31.0"


def test_the_total_runs_across_years_and_a_year_without_sales_has_no_holding_time():
    r = trade_behaviour([*ORDERS, o("CCC", date(2026, 1, 5), "buy", 10, "1000", order="7")])
    assert [y["year"] for y in r["years"]] == [2025, 2026] and r["years"][1]["avg_hold_days"] is None
    assert r["total"]["orders"] == 4 and r["total"]["symbols"] == 2 and r["total"]["buy_value"] == "3010000" and r["total"]["avg_hold_days"] == "70.3"


def test_nothing_has_no_ratios():
    assert trade_behaviour([]) == {"years": [], "total": None, "no_holding_time": []}


def test_the_same_order_in_two_files_counts_once_but_two_fills_in_one_file_stay():
    a = o("AAA", date(2025, 1, 1), "buy", 10, "1", line=5)
    twin = {**a, "line": 6}  # the same price and size filled twice within one order
    orders, dropped = merge_files([[a, twin], [{**a, "line": 90}]])
    assert len(orders) == 2 and dropped == 1
