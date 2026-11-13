import json
from datetime import date

from investment_agent.market.corporate_events import normalise
from investment_agent.market.providers.vndirect_data import hose_listing, price_board


def fake_get(url: str) -> str:
    if "/stocks?" in url:
        return json.dumps({"data": [{"code": "FPT", "type": "STOCK", "floor": "HOSE"}, {"code": "HPG", "type": "STOCK", "floor": "HOSE"},
                                    {"code": "NEW", "type": "STOCK", "floor": "HOSE"}]})
    if "industry_classification" in url:
        return json.dumps({"data": [{"industryCode": "9500", "vietnameseName": "Công nghệ", "codeList": "FPT,CMG,ELC"},
                                    {"industryCode": "1700", "vietnameseName": "Tài nguyên", "codeList": "HPG,HSG"}]})
    if "stock_prices" in url:
        return json.dumps({"data": [
            {"code": "FPT", "date": "2026-11-13", "basicPrice": 49.55, "close": 50.1, "nmVolume": 14372200.0, "nmValue": 717446805000.0},
            {"code": "FPT", "date": "2026-11-12", "basicPrice": 50.9, "close": 49.55, "nmVolume": 1.0, "nmValue": 1.0},
            {"code": "HPG", "date": "2026-11-13", "basicPrice": 21.0, "close": 21.0, "nmVolume": 0.0, "nmValue": 0.0},
            {"code": "XXX", "date": "2026-11-13", "basicPrice": 10.0, "close": 11.0, "nmVolume": 5.0, "nmValue": 55000.0}]})
    if "foreigns" in url:
        return json.dumps({"data": [{"code": "FPT", "tradingDate": "2026-11-13", "buyVal": 101848080000.0, "sellVal": 323369810000.0,
                                     "buyVol": 2046980.0, "sellVol": 6489048.0}]})
    raise AssertionError(url)


def test_the_hose_listing_has_symbols_level_two_codes_and_keeps_known_sector_names():
    out = hose_listing(get=fake_get, known_names={"1700": "Tài nguyên Cơ bản"})
    assert out["symbols"] == ["FPT", "HPG", "NEW"]
    assert out["icb_codes"] == {"FPT": "9500", "HPG": "1700"}  # NEW has no sector yet
    assert out["icb_names"] == {"9500": "Công nghệ", "1700": "Tài nguyên Cơ bản"}


def test_the_board_is_the_latest_session_in_the_units_the_brief_reads():
    rows = {r["symbol"]: r for r in price_board(["FPT", "HPG"], get=fake_get, today=date(2026, 11, 13))}
    assert set(rows) == {"FPT", "HPG"}  # only the symbols asked for
    fpt = rows["FPT"]
    assert fpt["trading_date"] == "2026-11-13" and fpt["ref_price"] == 49550 and fpt["match_price"] == 50100
    assert fpt["accumulated_value"] == 717446.805 and fpt["accumulated_volume"] == 14372200  # million đồng, as Vnstock served it
    assert fpt["foreign_buy_value"] == 101848080000.0 and fpt["foreign_sell_volume"] == 6489048
    assert rows["HPG"]["match_price"] == 0 and rows["HPG"]["foreign_buy_value"] is None  # no trade, no foreign row


def test_vndirect_events_become_the_same_events_with_vietnamese_names():
    raw = [{"id": "a1", "code": "FPT", "group": "investorRight", "type": "DIVIDEND", "typeDesc": "Cổ tức bằng tiền", "note": "Trả cổ tức đợt 2/2025 (1000 đ/cp)",
            "dividend": 1000.0, "ratio": 10.0, "effectiveDate": "2026-05-28", "actualDate": "2026-06-10"},
           {"id": "a2", "code": "FPT", "group": "investorRight", "type": "KINDDIV", "typeDesc": "Bonus shares", "note": "Exercise rate 100:10",
            "ratio": 10.0, "effectiveDate": "2026-09-21"},
           {"id": "a3", "code": "FPT", "group": "investorRight", "type": "MEETING", "typeDesc": "Họp ĐHCĐ", "note": "ĐHĐCĐ thường niên năm 2026",
            "effectiveDate": "2026-03-26"},
           {"id": "a4", "code": "FPT", "group": "schedEvent", "type": "schedDiv", "typeDesc": "Dự kiến cổ tức", "note": "Dự kiến", "disclosureDate": "2025-04-15"}]
    out = {e["id"]: e for e in normalise(raw)}
    div = out["FPT-a1"]
    assert div["kind"] == "dividend_cash" and div["exright"] == "2026-05-28" and div["key_date"] == "2026-05-28" and div["payout"] == "2026-06-10"
    assert div["value_per_share"] == 1000.0 and div["title"].startswith("Cổ tức bằng tiền") and div["record"] is None
    assert out["FPT-a2"]["kind"] == "issue" and out["FPT-a2"]["title"].startswith("Thưởng cổ phiếu")
    assert out["FPT-a3"]["kind"] == "meeting" and out["FPT-a3"]["key_date"] == "2026-03-26"
    assert out["FPT-a4"]["kind"] == "other" and out["FPT-a4"]["key_date"] is None
