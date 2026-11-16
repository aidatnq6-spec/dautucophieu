from decimal import Decimal

from investment_agent.brief.signals import index_pull, session_signals

# a market of four stocks; the index's divisor makes 1 point = 10 (cap at reference / previous close)
SYMBOLS = {"VIC": {"ref": 100, "change": 10}, "TCB": {"ref": 50, "change": -2}, "AAA": {"ref": 10, "change": -1}, "BBB": {"ref": 20, "change": None}}
SHARES = {"VIC": Decimal(1000), "TCB": Decimal(1000), "AAA": Decimal(1000), "BBB": Decimal(1000)}
# cap at reference 180,000; previous close 1000 → divisor 180; VIC +10,000 → +55.56 points; TCB −2,000 → −11.11; AAA −1,000 → −5.56


def test_each_stock_pull_on_the_index_adds_up_to_its_move():
    pull = index_pull(SYMBOLS, SHARES, change=Decimal("38.89"), close=Decimal("1038.89"))
    assert pull["status"] == "ok" and pull["computed"] == "38.89" and pull["actual"] == "38.89"
    assert pull["up"] == [{"symbol": "VIC", "points": "55.56"}]
    assert pull["down"] == [{"symbol": "TCB", "points": "-11.11"}, {"symbol": "AAA", "points": "-5.56"}]
    assert pull["without_top"] == {"symbols": ["VIC"], "points": "-16.67"}  # without its biggest pull the index would have fallen


def test_a_sum_far_from_the_index_move_is_not_shown():
    pull = index_pull(SYMBOLS, SHARES, change=Decimal("5"), close=Decimal("1005"))
    assert pull == {"status": "mismatch", "computed": "38.89", "actual": "5.00",
                    "reason": "Tổng điểm tính theo vốn hóa lệch quá xa mức thay đổi của VN-Index"}
    assert index_pull(SYMBOLS, {}, change=Decimal("5"), close=Decimal("1005"))["status"] == "missing"


def test_signals_say_a_green_index_over_falling_stocks_and_thin_trading_with_its_run():
    out = session_signals(index_change=Decimal("1.96"), breadth={"up": 101, "down": 220, "flat": 50, "no_trade": 30},
                          volume={"status": "ok", "ratio20": "0.69", "change_pct": "-0.1050"}, earlier_ratios=[Decimal("0.85"), Decimal("1.2"),
                                                                                                                Decimal("0.9"), Decimal("0.95")])
    assert out["breadth_gap"] == {"kind": "green_over_red", "up": 101, "down": 220}
    assert out["liquidity"] == {"ratio20": "0.69", "change_pct": "-0.1050", "low": True, "below_avg_sessions": 3}
    calm = session_signals(index_change=Decimal("-3"), breadth={"up": 150, "down": 140, "flat": 0, "no_trade": 0},
                           volume={"status": "ok", "ratio20": "1.10", "change_pct": "0.2"}, earlier_ratios=[])
    assert calm["breadth_gap"] is None and calm["liquidity"] == {"ratio20": "1.10", "change_pct": "0.2", "low": False, "below_avg_sessions": 0}
    red = session_signals(index_change=Decimal("-3"), breadth={"up": 200, "down": 100, "flat": 0, "no_trade": 0}, volume=None, earlier_ratios=[])
    assert red["breadth_gap"] == {"kind": "red_over_green", "up": 200, "down": 100} and red["liquidity"] is None


def test_the_page_gets_the_same_signal_lines_as_the_telegram_brief():
    from investment_agent.brief.view import market_view
    snap = {"session_date": "2026-11-16", "board": {"status": "missing", "reason": "x"},
            "signals": {"status": "ok", "breadth_gap": {"kind": "green_over_red", "up": 101, "down": 220}, "pull": {"status": "missing"},
                        "liquidity": None}}
    assert market_view(snap, watched=[], held=set())["signal_lines"] == ["Xanh vỏ đỏ lòng: VN-Index tăng nhưng 220 mã giảm, chỉ 101 mã tăng"]
    assert market_view({"session_date": "2026-11-13", "board": {"status": "missing"}}, watched=[], held=set())["signal_lines"] == []
