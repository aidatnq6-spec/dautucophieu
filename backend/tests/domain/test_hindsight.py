from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.hindsight import hindsight
from investment_agent.domain.ledger import parse_events

TODAY = date(2026, 11, 2)


def _days(start, values):
    return [(start + timedelta(days=i), float(v)) for i, v in enumerate(values)]


def _ev(*rows):
    out = [{"event_id": "d0", "type": "deposit", "effective_at": "2025-01-01", "sequence": 0, "amount": "1000000000"}]
    for i, (kind, day, symbol, qty, price) in enumerate(rows, 1):
        out.append({"event_id": f"e{i}", "type": kind, "effective_at": day, "sequence": i, "security_id": symbol, "quantity": qty,
                    "price": price, "fee": "0", "tax": "0"})
    return parse_events(out)


def _flat_index(start=date(2025, 1, 1), n=700, v=1000):
    return _days(start, [v] * n)


def test_buys_and_sells_are_followed_three_six_and_twelve_months_against_vn_index():
    closes = {"FPT": _days(date(2025, 1, 1), [50] * 120 + [60] * 580)}  # 50 thousand đồng, then 60 from 1 May 2025
    out = hindsight(_ev(("buy", "2025-02-01", "FPT", 100, "50000"), ("sell", "2025-03-01", "FPT", 100, "50000")), closes=closes,
                    index=_flat_index(), journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    buy, sell = out["trades"]
    assert buy["type"] == "buy" and buy["date"] == "2025-02-01" and buy["price"] == "50000"
    assert buy["horizons"]["3"] == {"status": "ok", "on": "2025-05-01", "change": "0.2000", "index": "0.0000", "diff": "0.2000", "reason": None}
    assert sell["horizons"]["3"]["change"] == "0.2000"  # the price went on up 20% after the sale: sold early
    assert out["trades"][0]["horizons"]["12"]["status"] == "ok"
    late = hindsight(_ev(("buy", "2026-09-01", "FPT", 100, "60000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                     threshold=Decimal("0.3"), today=TODAY)
    assert late["trades"][0]["horizons"]["3"] == {"status": "not_yet", "on": "2026-12-01", "change": None, "index": None, "diff": None, "reason": None}
    missing = hindsight(_ev(("buy", "2025-02-01", "HPG", 100, "20000")), closes={}, index=_flat_index(), journal=[], theses=[],
                        threshold=Decimal("0.3"), today=TODAY)
    assert missing["trades"][0]["horizons"]["3"]["status"] == "missing"


def test_opening_positions_are_counted_apart():
    events = parse_events([{"event_id": "o1", "type": "opening_balance", "effective_at": "2025-01-01", "sequence": 0, "cash": "0",
                            "positions": [{"security_id": "FPT", "quantity": 100, "total_cost": "5000000"}]}])
    out = hindsight(events, closes={}, index=[], journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert out["trades"] == [] and out["opening_skipped"] == 1


def test_holding_through_a_loss_past_the_threshold_is_measured_until_it_ends():
    closes = {"HPG": _days(date(2025, 1, 1), [20] * 30 + [13] * 30 + [21] * 40)}
    out = hindsight(_ev(("buy", "2025-01-01", "HPG", 100, "20000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                    threshold=Decimal("0.3"), today=TODAY)
    assert out["loss_holds"] == [{"symbol": "HPG", "start": "2025-01-31", "end": "2025-03-02", "days": 30, "deepest": "-0.3500",
                                  "outcome": "recovered"}]
    sold = hindsight(_ev(("buy", "2025-01-01", "HPG", 100, "20000"), ("sell", "2025-02-15", "HPG", 100, "13000")), closes=closes,
                     index=_flat_index(), journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert sold["loss_holds"][0]["outcome"] == "sold_at_loss" and sold["loss_holds"][0]["end"] == "2025-02-15"
    still = hindsight(_ev(("buy", "2025-01-01", "HPG", 100, "20000")), closes={"HPG": closes["HPG"][:60]}, index=_flat_index(), journal=[],
                      theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert still["loss_holds"][0]["outcome"] == "holding" and still["loss_holds"][0]["end"] is None


def test_a_broken_condition_compares_holding_with_selling_on_the_first_report():
    closes = {"FPT": _days(date(2025, 1, 1), [50] * 100 + [40] * 600)}
    thesis = {"symbol": "FPT", "closed_on": None, "conditions": [{"kind": "loss_vs_cost", "status": "broken", "broken_on": "2025-03-01",
                                                                  "broken_price": "45000", "hold": None, "params": {"pct": "10"}}],
              "history": [{"type": "hold", "kind": "f_score", "broken_on": "2025-02-01", "broken_price": "50000", "on": "2025-02-02"}]}
    out = hindsight(_ev(("buy", "2025-01-01", "FPT", 100, "50000")), closes=closes, index=_flat_index(), journal=[], theses=[thesis],
                    threshold=Decimal("0.3"), today=TODAY)
    assert out["breaks"] == [
        {"symbol": "FPT", "kind": "f_score", "label": "F-Score thấp", "broken_on": "2025-02-01", "broken_price": "50000", "held_on": True, "then": "40000",
         "then_on": TODAY.isoformat(), "how": "holding", "change": "-0.2000"},
        {"symbol": "FPT", "kind": "loss_vs_cost", "label": "Lỗ so với giá vốn", "broken_on": "2025-03-01", "broken_price": "45000", "held_on": False, "then": "40000",
         "then_on": TODAY.isoformat(), "how": "holding", "change": "-0.1111"}]


def test_biases_need_five_observations():
    closes = {"AAA": _days(date(2025, 1, 1), [8] * 30 + [10] * 670), "BBB": _days(date(2025, 1, 1), [12] * 30 + [10] * 670)}
    few = hindsight(_ev(("buy", "2025-01-01", "AAA", 100, "10000"), ("sell", "2025-02-01", "AAA", 100, "12000")), closes=closes,
                    index=_flat_index(), journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert few["biases"]["disposition"] == {"days": 1, "pgr": None, "plr": None, "enough": False}
    rows = [("buy", "2025-01-01", "AAA", 1000, "8000"), ("buy", "2025-01-01", "BBB", 1000, "12000")]
    for i in range(5):  # five days selling a little of the winner while the loser is kept
        rows.append(("sell", f"2025-0{i + 2}-01", "AAA", 100, "10000"))
    out = hindsight(_ev(*rows), closes=closes, index=_flat_index(), journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert out["biases"]["disposition"] == {"days": 5, "pgr": "1.0000", "plr": "0.0000", "enough": True}


def test_results_by_emotion_and_reason_and_chasing_buys():
    rising = [10 + i * 0.01 for i in range(700)]  # slow rise: about 2% over 20 sessions, never a chase
    closes = {"AAA": _days(date(2025, 1, 1), rising)}
    rows = [("buy", (date(2025, 1, 1) + timedelta(days=30 * i)).isoformat(), "AAA", 10, "10000") for i in range(1, 7)]  # 20 sessions before each
    journal = [{"ledger_event_id": f"e{i}", "emotion": "fomo"} for i in range(1, 7)]
    thesis = {"symbol": "AAA", "created_on": "2025-01-01", "closed_on": None, "reasons": ["fomo", "trend"], "conditions": [], "history": []}
    out = hindsight(_ev(*rows), closes=closes, index=_flat_index(), journal=journal, theses=[thesis], threshold=Decimal("0.3"), today=TODAY)
    fomo = next(r for r in out["biases"]["by_emotion"] if r["key"] == "fomo")
    assert fomo["count"] == 6 and fomo["enough"] is True and fomo["mean"] is not None
    assert {r["key"] for r in out["biases"]["by_reason"]} == {"fomo", "trend"}
    assert out["biases"]["chasing"]["chasing"]["count"] == 0 and out["biases"]["chasing"]["other"]["count"] == 6


def test_a_close_far_before_the_horizon_is_missing_with_the_last_date_not_a_price():
    closes = {"FPT": _days(date(2025, 1, 1), [50] * 70)}  # the series stops on 11/03/2025 (dropped from the watchlist)
    out = hindsight(_ev(("buy", "2025-02-01", "FPT", 100, "50000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                    threshold=Decimal("0.3"), today=TODAY)
    h = out["trades"][0]["horizons"]["6"]
    assert h["status"] == "missing" and h["reason"] == "Giá đã lưu chỉ tới 11/03/2025"
    none = hindsight(_ev(("buy", "2025-02-01", "HPG", 100, "20000")), closes={}, index=_flat_index(), journal=[], theses=[],
                     threshold=Decimal("0.3"), today=TODAY)
    assert none["trades"][0]["horizons"]["3"]["reason"] == "Chưa có giá đã lưu của mã"


def test_adjusted_closes_are_compared_with_adjusted_closes_not_with_the_trade_price():
    # A later 20% stock dividend scaled every earlier close to 41,67 (raw 50); the price did not move.
    closes = {"FPT": _days(date(2025, 1, 1), [41.67] * 700)}
    out = hindsight(_ev(("buy", "2025-02-01", "FPT", 100, "50000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                    threshold=Decimal("0.1"), today=TODAY)
    assert out["trades"][0]["horizons"]["3"]["change"] == "0.0000"
    assert out["loss_holds"] == []  # no loss that never happened


def test_buying_more_inside_a_loss_period_ends_it_as_averaging_down():
    closes = {"HPG": _days(date(2025, 1, 1), [20] * 30 + [13] * 30 + [14] * 40)}
    out = hindsight(_ev(("buy", "2025-01-01", "HPG", 100, "20000"), ("buy", "2025-02-10", "HPG", 1000, "13000")), closes=closes,
                    index=_flat_index(), journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert out["loss_holds"][0]["outcome"] == "averaged_down" and out["loss_holds"][0]["end"] == "2025-02-10"


def test_two_sells_on_one_day_are_judged_on_their_weighted_price():
    closes = {"HPG": _days(date(2025, 1, 1), [20] * 30 + [13] * 70)}
    out = hindsight(_ev(("buy", "2025-01-01", "HPG", 200, "20000"), ("sell", "2025-02-15", "HPG", 100, "12000"),
                        ("sell", "2025-02-15", "HPG", 100, "21000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                    threshold=Decimal("0.3"), today=TODAY)
    assert out["loss_holds"][0]["outcome"] == "sold_at_loss"  # (12 000 + 21 000) / 2 = 16 500 below the cost of 20 000


def test_groups_count_every_buy_and_say_how_many_have_six_months():
    closes = {"AAA": _days(date(2025, 1, 1), [10 + i * 0.01 for i in range(700)])}
    rows = [("buy", (date(2026, 9, 1) + timedelta(days=i)).isoformat(), "AAA", 10, "10000") for i in range(6)]
    journal = [{"ledger_event_id": f"e{i}", "emotion": "fomo"} for i in range(1, 7)]
    out = hindsight(_ev(*rows), closes=closes, index=_flat_index(), journal=journal, theses=[], threshold=Decimal("0.3"), today=TODAY)
    fomo = out["biases"]["by_emotion"][0]
    assert fomo["count"] == 6 and fomo["matured"] == 0 and fomo["enough"] is False and fomo["mean"] is None
    assert out["biases"]["chasing"]["other"]["count"] == 6


def test_chasing_looks_at_the_twenty_sessions_before_the_buy_day():
    values = [10.0] * 40 + [12.0]  # the jump is on the buy day itself: not a chase
    closes = {"AAA": _days(date(2025, 1, 1), values + [12.0] * 600)}
    out = hindsight(_ev(("buy", "2025-02-10", "AAA", 10, "12000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                    threshold=Decimal("0.3"), today=TODAY)
    assert out["biases"]["chasing"]["chasing"]["count"] == 0 and out["biases"]["chasing"]["other"]["count"] == 1


def test_a_break_is_not_credited_with_a_sale_after_its_thesis_closed():
    closes = {"FPT": _days(date(2025, 1, 1), [50] * 700)}
    thesis = {"symbol": "FPT", "closed_on": "2025-03-01", "history": [], "conditions": [
        {"id": "c", "kind": "loss_vs_cost", "status": "broken", "broken_on": "2025-02-01", "broken_price": "45000", "hold": None}]}
    out = hindsight(_ev(("buy", "2025-01-01", "FPT", 100, "50000"), ("sell", "2025-03-01", "FPT", 100, "44000"),
                        ("buy", "2025-04-01", "FPT", 100, "50000"), ("sell", "2025-06-01", "FPT", 100, "60000")), closes=closes,
                    index=_flat_index(), journal=[], theses=[thesis], threshold=Decimal("0.3"), today=TODAY)
    assert out["breaks"][0]["then"] == "44000" and out["breaks"][0]["label"] == "Lỗ so với giá vốn"


def test_a_horizon_dated_today_waits_for_todays_close():
    closes = {"FPT": _days(date(2026, 7, 1), [50] * 124)}  # up to 01/11, the day before today
    out = hindsight(_ev(("buy", "2026-08-02", "FPT", 100, "50000")), closes=closes, index=_flat_index(), journal=[], theses=[],
                    threshold=Decimal("0.3"), today=TODAY)
    assert out["trades"][0]["horizons"]["3"]["status"] == "not_yet"


def test_breaks_without_a_condition_id_are_kept_apart_by_kind():
    closes = {"FPT": _days(date(2025, 1, 1), [50] * 700)}
    thesis = {"symbol": "FPT", "closed_on": None, "conditions": [], "history": [
        {"type": "hold", "kind": "f_score", "broken_on": "2025-02-01", "broken_price": "50000"},
        {"type": "hold", "kind": "loss_vs_cost", "broken_on": "2025-02-01", "broken_price": "50000"}]}
    out = hindsight(_ev(("buy", "2025-01-01", "FPT", 100, "50000")), closes=closes, index=_flat_index(), journal=[], theses=[thesis],
                    threshold=Decimal("0.3"), today=TODAY)
    assert [b["kind"] for b in out["breaks"]] == ["f_score", "loss_vs_cost"]


def test_hindsight_replays_the_ledger_once(monkeypatch):
    import investment_agent.domain.hindsight as hs
    calls = []
    real = hs.snapshots
    monkeypatch.setattr(hs, "snapshots", lambda events: calls.append(1) or real(events))
    monkeypatch.setattr(hs, "replay", lambda *a, **k: (_ for _ in ()).throw(AssertionError("replay per prefix")), raising=False)
    closes = {"AAA": _days(date(2025, 1, 1), [10] * 700)}
    rows = [("buy", (date(2025, 1, 2) + timedelta(days=i)).isoformat(), "AAA", 10, "10000") for i in range(30)]
    hindsight(_ev(*rows), closes=closes, index=_flat_index(), journal=[], theses=[], threshold=Decimal("0.3"), today=TODAY)
    assert calls == [1]
