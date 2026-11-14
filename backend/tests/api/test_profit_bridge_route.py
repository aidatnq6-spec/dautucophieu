import json

from investment_agent.market.statements import StatementStore

from signed_client import call
from test_passive_income_route import client as base_client

LINES = {"revenue": "1000", "gross_profit": "400", "selling": "100", "admin": "80", "fin_income": "30", "fin_expense": "20", "tax": "46",
         "npat_parent": "184"}


def setup(tmp_path, sector="Bất động sản"):
    (tmp_path / "market-symbols.txt").write_text("KDH\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2, "sectors": {"KDH": sector}}), encoding="utf-8")
    StatementStore(tmp_path / "statements").save({"symbol": "KDH", "years": {}, "quarters": {
        "2025-Q3": LINES, "2026-Q2": {"npat_parent": "1"}, "2026-Q3": {**LINES, "revenue": "1100", "gross_profit": "440", "tax": "54", "npat_parent": "216"}}})
    return base_client(tmp_path)


def test_the_latest_quarter_with_last_year_s_is_bridged(tmp_path):
    c, clock = setup(tmp_path)
    body = call(c, clock, "GET", "/internal/stock/KDH/profit-bridge").json()
    assert body["quarters"] == ["2026-Q3"] and body["financial"] is False
    b = body["bridge"]
    assert b["status"] == "ok" and b["start"] == "184" and b["end"] == "216" and b["other"] == "0"
    assert {s["id"]: s["amount"] for s in b["steps"]}["revenue"] == "40" and {s["id"]: s["amount"] for s in b["steps"]}["tax"] == "-8"
    assert call(c, clock, "GET", "/internal/stock/KDH/profit-bridge/2026-5").status_code == 422
    assert call(c, clock, "GET", "/internal/stock/HPG/profit-bridge").status_code == 404


def test_a_bank_has_no_bridge(tmp_path):
    c, clock = setup(tmp_path, sector="Ngân hàng")
    assert call(c, clock, "GET", "/internal/stock/KDH/profit-bridge").json() == {"symbol": "KDH", "financial": True, "quarters": [], "bridge": None}
