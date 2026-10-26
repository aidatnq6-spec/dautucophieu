from datetime import date

from investment_agent.brief.board import summarise_board

D = date(2026, 10, 26)
ICB = {"8300": "Ngân hàng", "9500": "Công nghệ Thông tin"}


def rec(symbol, ref, match, *, value=0.0, volume=0, fbv=0, fsv=0, fbval=0, fsval=0, icb="8300", day="2026-10-26"):
    return {"symbol": symbol, "trading_date": day, "ref_price": ref, "match_price": match, "accumulated_value": value,
            "accumulated_volume": volume, "foreign_buy_volume": fbv, "foreign_sell_volume": fsv, "foreign_buy_value": fbval,
            "foreign_sell_value": fsval, "icb_code2": icb}


RECORDS = [
    rec("VCB", 60000, 61200, value=500000.5, volume=8_000_000, fbv=100, fsv=50, fbval=30_000_000_000, fsval=10_000_000_000),
    rec("MBB", 20000, 19600, value=300000.0, volume=15_000_000, fbv=10, fsv=900, fbval=1_000_000_000, fsval=91_000_000_000),
    rec("ACB", 25000, 25000, value=100000.0, volume=4_000_000),
    rec("FPT", 57000, 56000, value=572175.08, volume=10_104_800, fbv=1_618_830, fsv=3_000_000, fbval=91_862_366_500,
        fsval=170_000_000_000, icb="9500"),
    rec("XYZ", 10000, 0, icb="9999"),  # no trade today
]


def test_breadth_totals_foreign_and_sectors():
    out = summarise_board(RECORDS, session_date=D, icb_names=ICB)
    assert out["status"] == "ok" and out["trading_date"] == "2026-10-26"
    assert out["breadth"] == {"up": 1, "down": 2, "flat": 1, "no_trade": 1}
    assert out["value_matched_bn"] == "1472.18"  # Σ million đồng / 1000
    assert out["volume_matched"] == 37_104_800
    f = out["foreign"]
    assert (f["buy_volume"], f["sell_volume"]) == (1_618_940, 3_000_950)
    assert (f["buy_value_bn"], f["sell_value_bn"], f["net_value_bn"]) == ("122.86", "271.00", "-148.14")
    assert [x["symbol"] for x in f["top_sell"]] == ["MBB", "FPT"] and f["top_sell"][0]["net_value_bn"] == "-90.00"
    assert [x["symbol"] for x in f["top_buy"]] == ["VCB"]  # zero-net ACB skipped
    assert [(s["sector"], s["pct"], s["count"]) for s in out["sectors"]] == [("Ngân hàng", "0.0000", 3), ("Công nghệ Thông tin", "-0.0175", 1)]
    assert out["symbols"]["FPT"] == {"price": 56000, "ref": 57000, "change": -1000, "pct": "-0.0175", "sector": "Công nghệ Thông tin"}
    assert out["symbols"]["XYZ"]["pct"] is None and out["symbols"]["XYZ"]["sector"] == "Khác"


def test_board_of_another_day_is_not_used():
    out = summarise_board([rec("VCB", 1, 2, day="2026-10-23")], session_date=D, icb_names=ICB)
    assert out == {"status": "missing", "reason": "Bảng giá chưa phải phiên này"}
