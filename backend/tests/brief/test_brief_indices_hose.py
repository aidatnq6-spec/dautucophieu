import json
from datetime import date, datetime

from investment_agent.brief.hose import parse_hose
from investment_agent.brief.indices import index_rows

D = date(2026, 10, 26)


def pts(*pairs):
    return [(datetime.fromisoformat(d), v) for d, v in pairs]


def test_index_points_and_percent_against_the_previous_close():
    out = index_rows({"VNINDEX": pts(("2026-10-22", 1640.0), ("2026-10-23", 1658.52), ("2026-10-26", 1650.12)),
                      "VN30": pts(("2026-10-23", 1800.0))}, session_date=D)
    assert out["status"] == "ok"
    vni, vn30 = out["rows"]
    assert vni == {"id": "VNINDEX", "status": "ok", "close": "1650.12", "change": "-8.40", "pct": "-0.0051"}
    assert vn30 == {"id": "VN30", "status": "missing", "reason": "Chưa có giá chỉ số phiên này"}


def test_no_index_for_the_session_is_missing():
    out = index_rows({"VNINDEX": pts(("2026-10-26", 1650.0))}, session_date=D)  # no previous close either
    assert out["status"] == "missing" and out["rows"][0]["status"] == "missing"


VALUE = json.dumps({"data": [
    {"trading_type_name": "Mua", "foreign_trading_value": "1,896,838.66", "market_value": "17,010,236.60"},
    {"trading_type_name": "Bán", "foreign_trading_value": "2,374,562.09", "market_value": ""},
    {"trading_type_name": "Mua - Bán", "foreign_trading_value": "-477,723.43", "market_value": ""}], "success": True})
VOLUME = json.dumps({"data": [
    {"trading_type_name": "Mua", "foreign_trading_volumn": "707,544.22", "market_volumn": "8,438,955.55"},
    {"trading_type_name": "Bán", "foreign_trading_volumn": "903,951.66", "market_volumn": ""},
    {"trading_type_name": "Mua - Bán", "foreign_trading_volumn": "-196,407.44", "market_volumn": ""}], "success": True})


def test_hose_report_in_billions_and_shares():
    out = parse_hose(VALUE, VOLUME)
    # Volumes are in lots of 100 shares: on 26/10 HOSE's 367,186.06 matched the board's 34.2 million foreign shares bought.
    assert out == {"status": "ok", "total_value_bn": "17010.24", "total_volume": 843_895_555,
                   "foreign": {"buy_value_bn": "1896.84", "sell_value_bn": "2374.56", "net_value_bn": "-477.72",
                               "buy_volume": 70_754_422, "sell_volume": 90_395_166}}


def test_hose_not_yet_published_or_changed():
    empty = json.dumps({"data": [], "success": True})
    assert parse_hose(empty, empty) == {"status": "missing", "reason": "HOSE chưa công bố"}
    assert parse_hose("<html>", VOLUME) == {"status": "missing", "reason": "HOSE đổi định dạng"}
