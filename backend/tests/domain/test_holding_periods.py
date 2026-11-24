from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.holding_periods import basket_view, holding_periods, pyramids
from investment_agent.domain.ledger import parse_events

TODAY = date(2025, 6, 1)


def _days(start, values):
    return [(start + timedelta(days=i), float(v)) for i, v in enumerate(values)]


def _ev(*rows, opening=None):
    out = [{"event_id": "o0", "type": "opening_balance", "effective_at": "2024-12-01", "sequence": 0, "cash": "1000000000", "positions": opening}] if opening \
        else [{"event_id": "d0", "type": "deposit", "effective_at": "2024-12-01", "sequence": 0, "amount": "1000000000"}]
    for i, (kind, day, symbol, qty, price) in enumerate(rows, 1):
        out.append({"event_id": f"e{i}", "type": kind, "effective_at": day, "sequence": i, "security_id": symbol, "quantity": qty,
                    "price": price, "fee": "1000" if kind == "buy" else "0", "tax": "0"})
    return parse_events(out)


def test_a_holding_period_runs_from_the_first_share_to_the_last_and_keeps_its_buys_and_sells():
    events = _ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-05", "FPT", 100, "60000"),
                 ("sell", "2025-01-10", "FPT", 200, "70000"), ("buy", "2025-02-01", "FPT", 100, "65000"))
    first, second = holding_periods(events)
    assert first["key"] == "FPT@2025-01-01" and first["end"] == "2025-01-10" and first["opening"] is False
    assert first["buys"] == [{"on": "2025-01-01", "outlay": "5001000"}, {"on": "2025-01-05", "outlay": "6001000"}]
    assert first["sells"] == [{"on": "2025-01-10", "proceeds": "14000000", "cost": "11002000"}]
    assert second["key"] == "FPT@2025-02-01" and second["end"] is None and second["shares"] == 100 and second["cost"] == "6501000"


def test_a_period_opened_by_the_opening_balance_is_marked():
    events = _ev(("sell", "2025-01-10", "HPG", 100, "30000"), opening=[{"security_id": "HPG", "quantity": 100, "total_cost": "2000000"}])
    (p,) = holding_periods(events)
    assert p["key"] == "HPG@2024-12-01" and p["opening"] is True and p["buys"] == [] and p["end"] == "2025-01-10"


def test_the_pyramid_compares_the_money_put_in_against_the_adjusted_price_of_the_first_buy():
    closes = {"FPT": _days(date(2025, 1, 1), [50, 50, 60, 60, 40])}
    rows = [("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-03", "FPT", 300, "60000"), ("buy", "2025-01-05", "FPT", 100, "40000")]
    out = pyramids(holding_periods(_ev(*rows)), closes=closes, today=TODAY)
    (r,) = out["rows"]
    assert r["label"] == "inverted" and r["reason"] is None  # the largest buy came at the highest level, above the first
    assert [b["level"] for b in r["buys"]] == ["0.0000", "0.2000", "-0.2000"]
    assert r["above_share"] == "0.6666"  # 18 001 000 of 27 003 000
    assert r["largest"] == {"on": "2025-01-03", "outlay": "18001000", "level": "0.2000"}
    assert r["mean_above"] == "18001000" and r["mean_below"] == "4501000"
    assert out["summary"] == {"counts": {"upright": 0, "inverted": 1, "mixed": 0}, "compared": 1, "mean_above_share": None, "enough": False}


def test_the_largest_buy_at_the_lowest_level_is_upright_and_anything_else_is_mixed():
    closes = {"FPT": _days(date(2025, 1, 1), [50, 50, 60, 60, 40])}
    upright = [("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-05", "FPT", 500, "40000")]
    assert pyramids(holding_periods(_ev(*upright)), closes=closes, today=TODAY)["rows"][0]["label"] == "upright"
    mixed = [("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-03", "FPT", 100, "60000"), ("buy", "2025-01-05", "FPT", 300, "50000")]
    closes_mixed = {"FPT": _days(date(2025, 1, 1), [50, 50, 60, 60, 55])}
    assert pyramids(holding_periods(_ev(*mixed)), closes=closes_mixed, today=TODAY)["rows"][0]["label"] == "mixed"


def test_one_buy_periods_are_left_out_and_a_buy_without_a_close_cannot_be_compared():
    closes = {"FPT": _days(date(2025, 1, 10), [50, 60])}
    rows = [("buy", "2025-01-10", "HPG", 100, "20000"), ("buy", "2025-01-01", "FPT", 100, "50000"), ("buy", "2025-01-11", "FPT", 100, "60000")]
    out = pyramids(holding_periods(_ev(*rows)), closes=closes, today=TODAY)
    (r,) = out["rows"]
    assert r["key"] == "FPT@2025-01-01" and r["label"] is None and r["reason"] == "Chưa có giá đã lưu tại ngày mua 01/01/2025"
    assert out["summary"]["compared"] == 0
    opened = _ev(("buy", "2025-01-11", "HPG", 100, "20000"), opening=[{"security_id": "HPG", "quantity": 100, "total_cost": "2000000"}])
    (o,) = pyramids(holding_periods(opened), closes={"HPG": _days(date(2024, 12, 1), [20] * 60)}, today=TODAY)["rows"]
    assert o["reason"] == "Đợt bắt đầu từ số dư đầu kỳ, không có lần mua đầu để so"


def test_five_compared_periods_give_the_mean_share_put_in_above_the_first_buy():
    closes = {"FPT": _days(date(2025, 1, 1), [50, 60] * 30)}
    rows = []
    for k in range(5):
        a, b = date(2025, 1, 1) + timedelta(days=4 * k), date(2025, 1, 2) + timedelta(days=4 * k)
        rows += [("buy", a.isoformat(), "FPT", 100, "50000"), ("buy", b.isoformat(), "FPT", 100, "60000"),
                 ("sell", (b + timedelta(days=1)).isoformat(), "FPT", 200, "60000")]
    out = pyramids(holding_periods(_ev(*rows)), closes=closes, today=TODAY)
    assert out["summary"]["compared"] == 5 and out["summary"]["enough"] is True
    assert out["summary"]["mean_above_share"] == "0.5454"  # 6 001 000 of 11 002 000 each time


BASKETS = {"baskets": [{"id": "b1", "name": "Ngắn hạn"}, {"id": "b2", "name": "Dài hạn"}], "tags": {}}


def test_each_basket_adds_the_realised_gain_of_its_periods_and_values_the_open_ones():
    events = _ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("sell", "2025-01-11", "FPT", 100, "60000"),
                 ("buy", "2025-02-01", "HPG", 100, "20000"), ("sell", "2025-02-05", "HPG", 50, "22000"),
                 ("buy", "2025-03-01", "VCB", 100, "90000"))
    tags = {"FPT@2025-01-01": "b1", "HPG@2025-02-01": "b1", "VCB@2025-03-01": "b2", "MWG@2024-01-01": "b2"}
    out = basket_view(holding_periods(events), {**BASKETS, "tags": tags}, prices={"HPG": Decimal("25000")})
    short, long_, untagged = out["rows"]
    assert short["id"] == "b1" and short["closed"] == 1 and short["open"] == 1
    assert short["realised"] == "1098500" and short["released"] == "6001500"  # FPT 999 000 + HPG 1 100 000 − 1 000 500
    assert short["realised_ratio"] == "0.1830"
    assert short["open_cost"] == "1000500" and short["unrealised"] == "249500" and short["missing"] == []
    assert short["win_rate"] is None and short["mean_days"] is None and short["enough"] is False  # one closed period only
    assert long_["open"] == 1 and long_["unrealised"] is None and long_["missing"] == ["VCB"]
    assert untagged["id"] is None and untagged["closed"] == 0 and untagged["open"] == 0
    assert out["stale"] == ["MWG@2024-01-01"]
    assert [p["basket"] for p in out["periods"]] == ["b1", "b1", "b2"]


def test_five_closed_periods_give_the_share_with_a_gain_and_the_mean_days_held():
    rows = []
    for k in range(5):
        a = date(2025, 1, 1) + timedelta(days=10 * k)
        rows += [("buy", a.isoformat(), "FPT", 100, "50000"), ("sell", (a + timedelta(days=4)).isoformat(), "FPT", 100, "60000" if k < 3 else "40000")]
    periods = holding_periods(_ev(*rows))
    out = basket_view(periods, {**BASKETS, "tags": {p["key"]: "b1" for p in periods}}, prices={})
    short = out["rows"][0]
    assert short["closed"] == 5 and short["enough"] is True and short["win_rate"] == "0.6000" and short["mean_days"] == "4.0"
