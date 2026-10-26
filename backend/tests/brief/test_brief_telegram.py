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
