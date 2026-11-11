import json

from investment_agent.market.statements import StatementStore

from signed_client import call
from test_passive_income_route import client as base_client

B = 10**9


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("KDH\nNLG\nDXG\nFPT\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-11-11", "source": "t", "level": 2, "sectors": {
        "KDH": "Bất động sản", "NLG": "Bất động sản", "DXG": "Bất động sản", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    store = StatementStore(tmp_path / "statements")
    for s, now in (("KDH", 150), ("NLG", 50), ("DXG", -10)):
        store.save({"symbol": s, "quarters": {"2025-Q3": {"npat_parent": str(100 * B), "cfo": str(10 * B)},
                                              "2026-Q3": {"npat_parent": str(now * B), "cfo": str(20 * B)}}, "years": {}})
    return base_client(tmp_path)


def test_the_sectors_of_the_watched_tickers_are_listed_with_a_plain_key(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/sectors").json()
    assert {s["key"]: (s["name"], s["count"]) for s in body["sectors"]} == {"bat-dong-san": ("Bất động sản", 3), "cong-nghe-thong-tin": ("Công nghệ Thông tin", 1)}


def test_one_sector_has_its_heatmap_and_valuation(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/sectors/bat-dong-san").json()
    assert body["name"] == "Bất động sản" and body["members"] == ["DXG", "KDH", "NLG"]
    assert body["heatmap"]["quarters"] == ["2025-Q3", "2026-Q3"]
    dxg = next(r for r in body["heatmap"]["rows"] if r["symbol"] == "DXG")
    assert dxg["cells"][-1]["profit_turn"] == "to_loss"
    assert body["heatmap"]["total"][-1]["profit_yoy"] == "-0.3667" and body["heatmap"]["total"][-1]["profit_count"] == 3  # 190 against 300
    assert "median" in body["valuation"] and "tickers" in body["valuation"]
    assert call(c, clock, "GET", "/internal/sectors/khong-co").status_code == 404
