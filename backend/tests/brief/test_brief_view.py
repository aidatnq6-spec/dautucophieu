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


def test_the_session_shape_and_hose_value_pass_through_and_older_snapshots_name_them_missing():
    shape = {"status": "ok", "range": {}, "streak": {}, "volume": {"status": "missing", "reason": "x"}}
    v = market_view({**SNAP, "index_session": shape, "hose_liquidity": {"status": "missing", "reason": "HOSE chưa công bố"}}, watched=[], held=set())
    assert v["index_session"] == shape and v["hose_liquidity"]["reason"] == "HOSE chưa công bố"
    old = market_view(SNAP, watched=[], held=set())  # snapshots stored before this feature
    assert old["index_session"]["status"] == "missing" and old["hose_liquidity"]["status"] == "missing"


def test_the_recovery_checklist_is_read_from_the_snapshot():
    v = market_view(SNAP, watched=[], held=set())
    assert v["recovery"]["status"] == "ok" and [c["id"] for c in v["recovery"]["checks"]] == ["ma20", "volume", "breadth", "spread"]


def test_the_index_impact_marks_held_stocks_and_passes_the_check():
    pull = {"status": "ok", "computed": "-0.83", "actual": "-0.83", "up": [{"symbol": "VIC", "points": "3.02"}], "down": [{"symbol": "VCB", "points": "-1.04"}],
            "without_top": None}
    v = market_view({**SNAP, "signals": {"status": "ok", "pull": pull}}, watched=[], held={"VCB"})
    assert v["impact"] == {"status": "ok", "computed": "-0.83", "actual": "-0.83", "up": [{"symbol": "VIC", "points": "3.02", "held": False}],
                           "down": [{"symbol": "VCB", "points": "-1.04", "held": True}]}
    assert market_view(SNAP, watched=[], held=set())["impact"]["status"] == "missing"


def test_the_heat_map_lists_traded_stocks_by_sector_with_their_matched_value():
    board = {**SNAP["board"], "symbols": {**SNAP["board"]["symbols"],
                                          "FPT": {**SNAP["board"]["symbols"]["FPT"], "value_mn": "572175.08"},
                                          "VCB": {**SNAP["board"]["symbols"]["VCB"], "value_mn": "500000.5"}}}
    v = market_view({**SNAP, "board": board}, watched=[], held={"FPT"})
    rows = v["heatmap"]["rows"]
    assert v["heatmap"]["status"] == "ok" and [r["symbol"] for r in rows] == ["FPT", "VCB"]  # untraded KDH, unvalued ACB left out
    assert rows[0] == {"symbol": "FPT", "sector": "Công nghệ Thông tin", "pct": "-0.0175", "value_mn": "572175.08", "held": True}
    older = market_view(SNAP, watched=[], held=set())["heatmap"]  # snapshots stored before 21/11/2026 have no matched value per stock
    assert older["status"] == "missing" and "giá trị giao dịch" in older["reason"]

def test_the_us_line_of_the_snapshot_is_shown_after_the_asian_one():
    us = {"rows": [{"id": "us_dow", "name": "Dow Jones", "date": "2026-10-23", "day_pct": "-0.0193", "stale": False}], "source": "FRED"}
    assert market_view({**SNAP, "us": us}, watched=[], held=set())["us_line"] == "Mỹ (FRED): Dow Jones −1,93% (phiên 23/10)"
    assert market_view(SNAP, watched=[], held=set())["us_line"] is None  # snapshots stored before 21/11/2026