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


def test_the_board_also_carries_the_day_band_and_range_for_the_trend_page():
    def get(url):
        if "stock_prices" in url:
            return json.dumps({"data": [{"code": "FPT", "date": "2026-11-13", "basicPrice": 49.55, "close": 50.1, "nmVolume": 10.0, "nmValue": 1.0,
                                         "ceilingPrice": 53.0, "floorPrice": 46.1, "high": 51.0, "low": 49.1}]})
        return json.dumps({"data": []})
    row = price_board(["FPT"], get=get, today=date(2026, 11, 13))[0]
    assert (row["ceiling"], row["floor"], row["highest"], row["lowest"]) == (53000, 46100, 51000, 49100)


def test_index_levels_are_the_last_two_closes_at_the_close_of_their_day():
    from investment_agent.market.providers.vndirect_data import index_levels
    get = lambda url: json.dumps({"data": [{"code": "VN30", "date": "2026-11-13", "close": 1844.91}, {"code": "VN30", "date": "2026-11-12", "close": 1839.43},
                                           {"code": "VN30", "date": "2026-11-11", "close": 1855.27}]})  # noqa: E731
    points = index_levels("VN30", get=get, today=date(2026, 11, 13))
    assert [(t.date().isoformat(), t.hour, v) for t, v in points] == [("2026-11-12", 15, "1839.43"), ("2026-11-13", 15, "1844.91")]


def test_company_people_holders_officers_and_the_foreign_stake():
    from investment_agent.market.providers.vndirect_data import company_people

    def get(url):
        if "shareholders?" in url:
            return json.dumps({"data": [
                {"shareholderName": "Trương Gia Bình", "shareholderType": "PERSON", "roleType": "Chủ tịch HĐQT", "numberOfShares": 88731923.0,
                 "ownershipPct": 4.7054474220659035, "effectiveDate": "2023-07-05"},
                {"shareholderName": "SCIC", "shareholderType": "COMPANY", "roleType": "Cổ đông lớn", "numberOfShares": 73032619.0, "ownershipPct": 3.87,
                 "effectiveDate": "2023-07-05"},
                {"shareholderName": "Nguyễn Văn A", "shareholderType": "PERSON", "roleType": "Con của Thành viên HĐQT", "numberOfShares": 10.0,
                 "ownershipPct": 0.0001, "effectiveDate": "2024-01-01"}]})
        if "foreigns?" in url:
            return json.dumps({"data": [{"code": "FPT", "tradingDate": "2026-11-13", "totalRoom": 924006547.0, "currentRoom": 425534401.0}]})
        raise AssertionError(url)
    out = company_people("FPT", get=get, shares="1885727648")
    assert [h["name"] for h in out["shareholders"]] == ["Trương Gia Bình", "SCIC", "Nguyễn Văn A"]
    assert out["shareholders"][0] == {"name": "Trương Gia Bình", "type": "Individual", "quantity": 88731923, "percent": 0.047054474220659035,
                                      "updated": "2023-07-05"}
    assert out["officers"] == [{"name": "Trương Gia Bình", "position": "Chủ tịch HĐQT", "percent": 0.047054474220659035, "quantity": 88731923}]
    own = out["ownership"]
    assert own["foreign"] == "0.2643" and own["foreign_max"] == "0.49" and own["state"] is None and own["free_float"] is None
    assert out["structure"] is None
