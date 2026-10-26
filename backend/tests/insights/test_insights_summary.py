from investment_agent.insights.summary import link, summarise


def rec(source, ref, now_view, sectors, published="2026-10-01"):
    return {"source": source, "ref_id": ref, "title": ref, "page_url": f"https://x/{ref}", "published": published, "status": "ok",
            "insight": {"macro_now": {"view": now_view, "reasons": [{"text": f"lý do {ref}", "quote": "q", "page": 1}]},
                        "macro_outlook": {"view": "neutral", "reasons": []}, "sectors": sectors}}


def s(sector, effect):
    return {"sector": sector, "effect": effect, "reason": f"{sector} {effect}", "quote": "q", "page": 2}


def test_summary_counts_views_and_keeps_disagreements_with_their_sources():
    out = summarise([rec("acbs", "a", "favourable", [s("Ngân hàng", "benefit"), s("Dầu khí", "harm")]),
                     rec("worldbank", "w", "unfavourable", [s("Ngân hàng", "harm")]),
                     {"source": "acbs", "ref_id": "z", "status": "no_reliable_claims", "insight": None, "published": "2026-10-02"}])
    assert out["macro_now"]["votes"] == {"favourable": 1, "neutral": 0, "unfavourable": 1} and out["macro_now"]["consensus"] == "mixed"
    assert out["macro_outlook"]["consensus"] == "neutral"
    assert {r["source"] for r in out["macro_now"]["reasons"]} == {"acbs", "worldbank"}
    bank = next(x for x in out["sectors"] if x["sector"] == "Ngân hàng")
    assert bank["benefit"] == 1 and bank["harm"] == 1 and bank["mixed"] is True and len(bank["claims"]) == 2
    assert out["reports"] == 2  # unreliable reports are not counted


def test_empty_summary_has_no_consensus():
    out = summarise([])
    assert out["reports"] == 0 and out["macro_now"]["consensus"] == "none" and out["sectors"] == []


def test_link_adds_watchlist_tickers_valuation_and_held_warnings():
    summary = summarise([rec("acbs", "a", "favourable", [s("Ngân hàng", "benefit"), s("Bất động sản", "harm")])])
    rows = [{"symbol": "BID", "verdict": "cheap"}, {"symbol": "MBB", "verdict": "fair"}, {"symbol": "KDH", "verdict": "cheap"}]
    out = link(summary, sectors={"BID": "Ngân hàng", "MBB": "Ngân hàng", "KDH": "Bất động sản"}, valuation_rows=rows, held={"MBB", "KDH"})
    bank = next(x for x in out["sectors"] if x["sector"] == "Ngân hàng")
    assert bank["tickers"] == [{"symbol": "BID", "verdict": "cheap", "held": False}, {"symbol": "MBB", "verdict": "fair", "held": True}]
    assert bank["held_warning"] == []
    estate = next(x for x in out["sectors"] if x["sector"] == "Bất động sản")
    assert estate["held_warning"] == ["KDH"]


def test_unverified_macro_views_are_not_votes():
    r = rec("acbs", "a", "favourable", [s("Ngân hàng", "benefit")])
    r["insight"]["macro_now"] = {"view": None, "reasons": []}
    out = summarise([r])
    assert out["macro_now"]["votes"] == {"favourable": 0, "neutral": 0, "unfavourable": 0} and out["macro_now"]["consensus"] == "none"


def test_linking_covers_watched_and_held_tickers_only():
    from investment_agent.insights.summary import linking_sectors
    all_sectors = {"BID": "Ngân hàng", "MBB": "Ngân hàng", "XYZ": "Ngân hàng", "KDH": "Bất động sản"}
    assert linking_sectors(all_sectors, watched={"BID"}, held={"KDH"}) == {"BID": "Ngân hàng", "KDH": "Bất động sản"}
