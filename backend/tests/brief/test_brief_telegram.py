from investment_agent.notifications.render import render_report

REPORT = {"report_id": "r1", "session_date": "2026-10-26", "provenance": "vnstock_adjusted", "status": "published",
          "ledger_summary": {"cash": "1", "realized_gain": "0", "dividend_income": "0"},
          "decision": {"headline": "Giữ phân bổ hiện tại", "reasons": []}, "holdings": [], "narrative": {"text": "x"},
          "items": [{"entity_id": "HPG", "action": "hold", "reasons": ["outside_research_universe"]}],
          "verification_flags": ["universe_incomplete", "ai_not_configured"], "sources": [], "reminders": ["PMI Việt Nam quá hạn 35 ngày"]}
MARKET = {"session_date": "2026-10-26",
          "indices": {"status": "ok", "rows": [{"id": "VNINDEX", "status": "ok", "close": "1650.12", "change": "-8.40", "pct": "-0.0051"},
                                               {"id": "VN30", "status": "missing", "reason": "Chưa có giá chỉ số phiên này"}]},
          "board": {"status": "ok", "value_matched_bn": "13528.79", "volume_matched": 605225925,
                    "breadth": {"up": 107, "down": 205, "flat": 65, "no_trade": 30},
                    "foreign": {"buy_volume": 1, "sell_volume": 2, "buy_value_bn": "1200.50", "sell_value_bn": "2100.00", "net_value_bn": "-899.50",
                                "top_sell": [{"symbol": "VHM", "net_value_bn": "-210.50"}], "top_buy": [{"symbol": "FPT", "net_value_bn": "45.00"}]},
                    "sectors": [{"sector": "Ngân hàng", "pct": "0.0052", "count": 27}, {"sector": "Bất động sản", "pct": "-0.0210", "count": 60}]},
          "hose": {"status": "missing", "reason": "HOSE chưa công bố"},
          "proprietary": {"status": "missing", "reason": "Chưa có nguồn miễn phí"},
          "tickers": [{"symbol": "HPG", "price": 20900, "change": -300, "pct": "-0.0142", "held": True, "sector": "Tài nguyên Cơ bản"},
                      {"symbol": "FPT", "price": 56000, "change": -1000, "pct": "-0.0175", "held": False, "sector": "Công nghệ Thông tin"}],
          "news": {"status": "ok", "items": [{"title": f"Tin {i}", "url": f"https://x.vn/{i}", "source": "CafeF", "published": "x", "reason": "vĩ mô"}
                                             for i in range(8)]}}


def test_short_telegram_brief_follows_the_agreed_order():
    text = render_report(REPORT, market=MARKET)
    order = ["BẢN TIN SAU PHIÊN 26/10/2026", "VN-Index 1.650,12 (−8,40 điểm, −0,51%)", "VN30: chưa có số liệu (Chưa có giá chỉ số phiên này)",
             "Giá trị khớp lệnh HOSE: 13.528,79 tỷ đồng", "Độ rộng: 107 tăng · 205 giảm · 65 đứng giá · 30 không giao dịch",
             "Khối ngoại: mua 1.200,50 tỷ · bán 2.100,00 tỷ · ròng −899,50 tỷ", "Bán ròng mạnh: VHM −210,50 tỷ", "Mua ròng mạnh: FPT +45,00 tỷ",
             "Tự doanh: chưa có số liệu (Chưa có nguồn miễn phí)", "Ngân hàng +0,52% (27 mã)", "Bất động sản −2,10% (60 mã)",
             "HPG 20.900 (−1,42%)", "Tin 0 (CafeF)", "Danh mục: Giữ phân bổ hiện tại", "PMI Việt Nam quá hạn 35 ngày",
             "Xem bản đầy đủ trong ứng dụng, mục Bản tin sau phiên."]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)
    assert "Tin 5 (CafeF)" not in text  # at most 5 news items
    assert "FPT 56.000" not in text  # only held tickers in the short version
    for code in ("outside_research_universe", "universe_incomplete", "ai_not_configured"):
        assert code not in text


def test_without_a_snapshot_the_old_text_is_kept():
    assert render_report(REPORT).startswith("BẢN TIN SAU PHIÊN 2026-10-26")


SHAPE = {"status": "ok", "range": {"high": "1753.15", "low": "1733.02", "close": "1740.73", "from_high": "12.42", "from_low": "7.71"},
         "streak": {"direction": "up", "sessions": 2, "at_least": False, "change": "41.11", "pct": "0.0242"},
         "volume": {"status": "ok", "today": 673228995, "previous": 785061515, "change_pct": "-0.1425", "avg20": 609253076, "ratio20": "1.11"}}


def test_the_brief_gives_the_session_range_streak_and_liquidity_against_its_base():
    text = render_report(REPORT, market={**MARKET, "index_session": SHAPE,
                                         "hose": {"status": "ok", "total_value_bn": "15963.62", "total_volume": 1, "foreign": {}},
                                         "hose_liquidity": {"status": "ok", "today_bn": "15963.62", "previous_bn": "18051.57", "change_pct": "-0.1157",
                                                            "avg20_bn": "16500.00", "ratio20": "0.97"}})
    order = ["VN30: chưa có số liệu", "Trong phiên: cao 1.753,15 · thấp 1.733,02 · đóng cửa cách đỉnh 12,42 điểm, cách đáy 7,71 điểm",
             "Chuỗi: tăng 2 phiên liên tiếp, +41,11 điểm (+2,42%)",
             "Khối lượng khớp lệnh: 673.228.995 cp, −14,25% so với phiên trước, bằng 1,11 lần trung bình 20 phiên",
             "Giá trị khớp lệnh HOSE", "HOSE công bố tổng (gồm thỏa thuận): 15.963,62 tỷ đồng, −11,57% so với phiên trước, bằng 0,97 lần trung bình 20 phiên",
             "Độ rộng:", "Ngành tăng: 1/2"]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)


def test_a_short_or_unknown_streak_and_missing_bases_are_named():
    shape = {**SHAPE, "streak": {"direction": "down", "sessions": 3, "at_least": True, "change": None, "pct": None},
             "volume": {"status": "missing", "reason": "Thiếu nến 2 trong 20 phiên trước"}}
    text = render_report(REPORT, market={**MARKET, "index_session": shape, "hose_liquidity": {"status": "missing", "reason": "HOSE chưa công bố"}})
    assert "Chuỗi: giảm ít nhất 3 phiên liên tiếp" in text
    assert "Khối lượng khớp lệnh: chưa có số liệu (Thiếu nến 2 trong 20 phiên trước)" in text
    assert "HOSE công bố tổng" not in text  # nothing from HOSE yet: the existing line stays out, no comparison either
    flat = render_report(REPORT, market={**MARKET, "index_session": {**SHAPE, "streak": {"direction": "flat", "sessions": 1, "at_least": False,
                                                                                         "change": "0.00", "pct": "0.0000"}}})
    assert "Chuỗi: đứng giá so với phiên trước" in flat


def test_the_spread_sits_beside_the_index_and_an_opposite_direction_is_named():
    board = {**MARKET["board"], "spread": {"count": 358, "mean_pct": "0.0030", "median_pct": "0.0000"}}
    same = render_report(REPORT, market={**MARKET, "board": board})
    assert "Lan tỏa: trung bình cộng các mã +0,30%, trung vị 0,00% (358 mã có giao dịch); VN-Index −0,51%, ngược chiều" in same
    up = {**MARKET["indices"], "rows": [{**MARKET["indices"]["rows"][0], "pct": "0.0044"}]}
    text = render_report(REPORT, market={**MARKET, "indices": up, "board": board})
    assert "Lan tỏa: trung bình cộng các mã +0,30%, trung vị 0,00% (358 mã có giao dịch); VN-Index +0,44%\n" in text + "\n"
    assert text.index("Ngành tăng") < text.index("Lan tỏa") < text.index("Khối ngoại")
    old = render_report(REPORT, market=MARKET)  # snapshots before 06/11/2026 have no spread
    assert "Lan tỏa" not in old


def test_the_recovery_checklist_is_one_line_after_the_sectors_count():
    recovery = {"status": "ok", "met": 2, "known": 3, "total": 4, "checks": [
        {"id": "ma20", "met": True, "label": "VN-Index trên MA20", "figure": "MA20 1.712,40"},
        {"id": "volume", "met": None, "label": "Khối lượng khớp lệnh ≥ trung bình 20 phiên", "figure": "chưa có số (x)"},
        {"id": "breadth", "met": False, "label": "Số mã tăng > số mã giảm", "figure": "107 tăng · 205 giảm"},
        {"id": "spread", "met": True, "label": "Trung bình cộng các mã tăng", "figure": "+0,30%"}]}
    text = render_report(REPORT, market={**MARKET, "recovery": recovery})
    line = ("Bảng kiểm phục hồi: 2/4 đạt, 1 chưa có số — VN-Index trên MA20: đạt (MA20 1.712,40) · Khối lượng khớp lệnh ≥ trung bình 20 phiên: "
            "chưa có số (x) · Số mã tăng > số mã giảm: chưa (107 tăng · 205 giảm) · Trung bình cộng các mã tăng: đạt (+0,30%)")
    assert line in text and text.index("Ngành tăng") < text.index("Bảng kiểm phục hồi") < text.index("Khối ngoại")
    assert "Bảng kiểm phục hồi" not in render_report(REPORT, market=MARKET)


def test_the_session_signals_follow_the_index_lines():
    up = {**MARKET["indices"], "rows": [{"id": "VNINDEX", "status": "ok", "close": "1736.89", "change": "1.96", "pct": "0.0011"}]}
    signals = {"status": "ok", "breadth_gap": {"kind": "green_over_red", "up": 101, "down": 220},
               "pull": {"status": "ok", "computed": "1.93", "actual": "1.96",
                        "up": [{"symbol": "VIC", "points": "7.96"}, {"symbol": "MCH", "points": "1.76"}, {"symbol": "DMX", "points": "0.63"},
                               {"symbol": "LPB", "points": "0.56"}],
                        "down": [{"symbol": "TCB", "points": "-1.21"}, {"symbol": "VCB", "points": "-1.04"}, {"symbol": "VPB", "points": "-0.83"}],
                        "without_top": {"symbols": ["VIC", "MCH", "DMX"], "points": "-8.39"}},
               "liquidity": {"ratio20": "0.69", "change_pct": "-0.1050", "low": True, "below_avg_sessions": 3}}
    text = render_report(REPORT, market={**MARKET, "indices": up, "signals": signals})
    assert ("TÍN HIỆU PHIÊN\n"
            "- Xanh vỏ đỏ lòng: VN-Index tăng nhưng 220 mã giảm, chỉ 101 mã tăng\n"
            "- Mã kéo chỉ số (điểm): VIC +7,96; MCH +1,76; DMX +0,63 · Mã ghì: TCB −1,21; VCB −1,04; VPB −0,83\n"
            "- Trừ phần của VIC, MCH, DMX, VN-Index −8,39 điểm\n"
            "- Thanh khoản thấp: khối lượng khớp bằng 69% trung bình 20 phiên (−10,50% so với phiên trước), 3 phiên liền dưới trung bình") in text
    assert text.index("VN-Index 1.736,89") < text.index("TÍN HIỆU PHIÊN") < text.index("Giá trị khớp lệnh")
    odd = {**signals, "breadth_gap": None, "liquidity": {"ratio20": "1.05", "change_pct": "0.1", "low": False, "below_avg_sessions": 0},
           "pull": {"status": "mismatch", "computed": "3.10", "actual": "1.96", "reason": "x"}}
    text = render_report(REPORT, market={**MARKET, "indices": up, "signals": odd})
    assert "- Mã kéo chỉ số: chưa hiện vì tổng tính được (+3,10 điểm) lệch với VN-Index (+1,96 điểm)" in text and "Thanh khoản" not in text
    assert "TÍN HIỆU PHIÊN" not in render_report(REPORT, market=MARKET)


def test_the_asian_markets_line_follows_the_index_lines():
    asia = {"status": "ok", "read_at": "2026-11-16T15:32:00+07:00", "rows": [
        {"code": "KOSPI", "name": "KOSPI", "price": "5290.53", "change_pct": "-0.0098", "unchanged_since": None, "fred_date": None}]}
    text = render_report(REPORT, market={**MARKET, "asia": asia})
    assert "Châu Á (VNDirect, đọc 15:32 16/11): KOSPI −0,98%" in text
    assert text.index("VN-Index") < text.index("Châu Á") < text.index("Giá trị khớp lệnh")
    assert "Châu Á" not in render_report(REPORT, market=MARKET)


def test_the_us_markets_line_follows_the_asian_one():
    asia = {"status": "ok", "read_at": "2026-11-16T15:32:00+07:00", "rows": [
        {"code": "KOSPI", "name": "KOSPI", "price": "5290.53", "change_pct": "-0.0098", "unchanged_since": None, "fred_date": None}]}
    us = {"rows": [{"id": "us_dow", "name": "Dow Jones", "date": "2026-11-13", "day_pct": "-0.0193", "stale": False}], "source": "FRED"}
    text = render_report(REPORT, market={**MARKET, "asia": asia, "us": us})
    assert "Mỹ (FRED): Dow Jones −1,93% (phiên 13/11)" in text
    assert text.index("Châu Á") < text.index("Mỹ (FRED)") < text.index("Giá trị khớp lệnh")
    assert "Mỹ (FRED)" not in render_report(REPORT, market=MARKET)


def test_a_shock_of_the_session_gets_its_line_after_the_markets_abroad():
    us = {"rows": [{"id": "us_dow", "name": "Dow Jones", "date": "2026-11-13", "day_pct": "-0.0193", "stale": False}], "source": "FRED"}
    g = {"id": "drop3", "label": "VN-Index giảm từ 3% trong một phiên", "events": 199, "n": 199, "n_independent": 48, "enough": True,
         "mean": "-0.0305", "p10": "-0.3444", "dip_median": "-0.1058", "within": None}
    shocks = {"status": "ok", "h": 60, "today": [g], "all": {"mean": "0.0429"}, "from": "2000-07-28"}
    text = render_report(REPORT, market={**MARKET, "us": us, "shocks": shocks})
    assert "Cú sốc hôm nay: VN-Index giảm từ 3% trong một phiên. Trong quá khứ" in text
    assert text.index("Mỹ (FRED)") < text.index("Cú sốc hôm nay") < text.index("Giá trị khớp lệnh")
    assert "Cú sốc" not in render_report(REPORT, market=MARKET)
