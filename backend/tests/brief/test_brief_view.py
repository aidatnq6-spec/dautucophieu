from investment_agent.brief.view import market_view

SNAP = {"session_date": "2026-10-26", "updated_at": "x",
        "indices": {"status": "ok", "rows": []}, "hose": {"status": "missing", "reason": "HOSE chưa công bố"},
        "proprietary": {"status": "missing", "reason": "Chưa có nguồn miễn phí"},
        "board": {"status": "ok", "breadth": {}, "foreign": {}, "sectors": [], "value_matched_bn": "1", "volume_matched": 1,
                  "symbols": {"FPT": {"price": 56000, "ref": 57000, "change": -1000, "pct": "-0.0175", "sector": "Công nghệ Thông tin"},
                              "VCB": {"price": 61200, "ref": 60000, "change": 1200, "pct": "0.0200", "sector": "Ngân hàng"},
                              "ACB": {"price": 25000, "ref": 25000, "change": 0, "pct": "0.0000", "sector": "Ngân hàng"},
                              "KDH": {"price": None, "ref": 30000, "change": None, "pct": None, "sector": "Bất động sản"},
                              "XYZ": {"price": 1, "ref": 1, "change": 0, "pct": "0.0000", "sector": "Khác"}}},
        "news": {"status": "ok", "items": [{"title": f"FPT tin {i}", "url": f"https://x.vn/{i}", "source": "CafeF",
                                            "published": f"2026-10-26T10:{i:02d}:00+07:00"} for i in range(12)]
                 + [{"title": "Bất động sản ấm lên", "url": "https://x.vn/bds", "source": "CafeF", "published": "2026-10-26T09:00:00+07:00"}]}}


def test_held_first_even_outside_watchlist_then_biggest_moves():
    v = market_view(SNAP, watched=["ACB", "VCB", "FPT"], held={"KDH"})
    assert [t["symbol"] for t in v["tickers"]] == ["KDH", "VCB", "FPT", "ACB"]
    assert v["tickers"][0] == {"symbol": "KDH", "price": None, "change": None, "pct": None, "held": True, "sector": "Bất động sản",
                               "state": "no_trade"}
    assert "XYZ" not in [t["symbol"] for t in v["tickers"]]


def test_news_is_picked_locally_and_capped():
    v = market_view(SNAP, watched=["FPT"], held={"KDH"})
    assert len(v["news"]["items"]) == 8 and v["news"]["items"][0]["reason"] == "FPT"


def test_sections_pass_through_and_no_snapshot_gives_none():
    v = market_view(SNAP, watched=[], held=set())
    assert v["proprietary"]["reason"] == "Chưa có nguồn miễn phí" and v["hose"]["status"] == "missing" and v["session_date"] == "2026-10-26"
    assert market_view(None, watched=[], held=set()) is None
