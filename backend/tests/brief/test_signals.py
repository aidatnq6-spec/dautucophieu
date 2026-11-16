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


def test_vn30_pull_uses_its_free_float_and_capped_weights():
    from investment_agent.brief.signals import vn30_multipliers
    weights = {"VIC": {"shares": "1000", "free_float": "0.50", "cap": "1.0000"}, "TCB": {"shares": "1000", "free_float": "1.00", "cap": "0.5000"}}
    m = vn30_multipliers(weights)
    assert m == {"VIC": Decimal("500.0000"), "TCB": Decimal("500.0000")}
    symbols = {"VIC": {"ref": 100, "change": 10}, "TCB": {"ref": 100, "change": -2}, "AAA": {"ref": 10, "change": 1}}
    pull = index_pull(symbols, m, change=Decimal("40"), close=Decimal("1040"))  # AAA is not in VN30: left out
    assert pull["status"] == "ok" and pull["up"] == [{"symbol": "VIC", "points": "50.00"}] and pull["down"] == [{"symbol": "TCB", "points": "-10.00"}]


def test_the_brief_line_for_vn30():
    from investment_agent.notifications.render import signal_lines
    s = {"status": "ok", "breadth_gap": None, "liquidity": None, "pull": {"status": "missing"},
         "pull_vn30": {"status": "ok", "computed": "-0.65", "actual": "-0.66", "up": [{"symbol": "VIC", "points": "3.85"}],
                       "down": [{"symbol": "TCB", "points": "-2.30"}, {"symbol": "FPT", "points": "-1.80"}], "without_top": None}}
    assert signal_lines(s) == ["Mã kéo VN30 (điểm): VIC +3,85 · Mã ghì: TCB −2,30; FPT −1,80"]


def asia_rows(*moves, stale=()):
    names = ["Nikkei 225", "KOSPI", "Thượng Hải", "Hang Seng"]
    return {"status": "ok", "read_at": "2026-11-16T15:32:00+07:00", "rows": [
        {"code": n, "name": n, "price": "1", "change_pct": m, "unchanged_since": "2026-11-13" if n in stale else None, "fred_date": None}
        for n, m in zip(names, moves)]}


def test_vn_index_against_the_asian_markets_of_the_same_session():
    from investment_agent.brief.signals import asia_vs_index
    out = asia_vs_index(Decimal("1.96"), asia_rows("0.0053", "-0.0098", "-0.0059", "-0.0155", stale=("Nikkei 225",)))
    assert out == {"index": "up", "up": 0, "down": 3, "counted": 3, "left_out": ["Nikkei 225"]}
    assert asia_vs_index(Decimal("1.96"), {"status": "missing"}) is None
    assert asia_vs_index(Decimal("0"), asia_rows("0.01", "0.01", "0.01", "0.01")) is None  # the index flat: nothing to compare


def test_the_asia_line_says_with_or_against_and_what_was_left_out():
    from investment_agent.notifications.render import signal_lines
    base = {"status": "ok", "breadth_gap": None, "liquidity": None, "pull": {"status": "missing"}}
    against = {**base, "asia": {"index": "up", "up": 0, "down": 3, "counted": 3, "left_out": ["Nikkei 225"]}}
    assert signal_lines(against) == ["VN-Index tăng trong khi 3/3 thị trường châu Á giảm (không tính Nikkei 225: chưa có số phiên này)"]
    same = {**base, "asia": {"index": "down", "up": 1, "down": 3, "counted": 4, "left_out": []}}
    assert signal_lines(same) == ["VN-Index giảm cùng chiều 3/4 thị trường châu Á"]
    split = {**base, "asia": {"index": "up", "up": 2, "down": 2, "counted": 4, "left_out": []}}
    assert signal_lines(split) == ["VN-Index tăng; châu Á chia đôi (2 tăng, 2 giảm)"]


def test_the_week_counts_the_sessions_of_each_signal():
    from investment_agent.brief.signals import week_signals
    def snap(gap=None, low=False, asia=None):
        return {"signals": {"status": "ok", "breadth_gap": gap and {"kind": gap, "up": 1, "down": 2},
                            "liquidity": {"ratio20": "0.7", "change_pct": None, "low": low, "below_avg_sessions": 1}, "asia": asia}}
    against = {"index": "up", "up": 0, "down": 3, "counted": 3, "left_out": []}
    along = {"index": "up", "up": 3, "down": 1, "counted": 4, "left_out": []}
    week = [snap("green_over_red", True, against), snap(None, True, along), snap("green_over_red"), {"board": {}}, snap("red_over_green")]
    assert week_signals(week) == {"sessions": 4, "green_over_red": 2, "red_over_green": 1, "low_liquidity": 2, "asia_sessions": 2, "asia_against": 1}
    assert week_signals([{"board": {}}]) is None
