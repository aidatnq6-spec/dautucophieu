from decimal import Decimal

from signed_client import call
from test_deposit_book_route import client, save_layers

HOME = {"id": "a", "name": "Nhà A", "kind": "home", "purpose": "rent", "value": "1000000000", "valued_on": "2027-01-01", "legal": "certificate", "rent_monthly": "5000000"}
LOAN = {"id": "l", "name": "Vay nhà", "balance": "120000000", "rate": "12", "months_left": 12, "method": "declining", "collateral": "a"}


def save(c, clock, version=0, rid="pb1", **more):
    return call(c, clock, "PUT", "/internal/property-book", {"properties": [HOME], "loans": [LOAN], "expected_version": version, "request_id": rid, **more})


def test_an_empty_book_says_why_the_financial_side_is_not_known_yet(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/property-book").json()
    assert body["version"] == 0 and body["book"]["properties"] == [] and body["book"]["ceiling"] == "70"
    assert body["picture"]["financial"] is None and body["financial_reason"] and body["unpriced"] == []


def test_financial_assets_are_the_towers_layers_with_stocks_at_market_price(tmp_path):
    c, clock = client(tmp_path)
    assert save_layers(c, clock).status_code == 200  # reserve 120 tr, deposits 300 tr, gold 100 tr; the ledger holds 95 tr cash
    market_value = Decimal(call(c, clock, "GET", "/internal/glance").json()["kpis"]["market_value"])
    r = save(c, clock)
    assert r.status_code == 200
    p = r.json()["picture"]
    financial = Decimal(615_000_000) + market_value
    assert Decimal(p["financial"]) == financial
    assert Decimal(p["net_worth"]) == financial + 1_000_000_000 - 120_000_000
    assert p["payments"] == "11200000"  # 120 tr / 12 + 120 tr × 12% / 12
    assert r.json()["version"] == 1 and r.json()["book"]["loans"][0]["name"] == "Vay nhà"


def test_saving_this_book_leaves_the_tower_as_it_was(tmp_path):
    c, clock = client(tmp_path)
    save_layers(c, clock)
    before = call(c, clock, "GET", "/internal/equity-budget").json()
    save(c, clock)
    assert call(c, clock, "GET", "/internal/equity-budget").json() == before


def test_a_stale_version_and_a_bad_book_are_refused(tmp_path):
    c, clock = client(tmp_path)
    assert save(c, clock).status_code == 200
    assert save(c, clock, version=0, rid="pb2").status_code == 409
    assert save(c, clock, version=1, rid="pb3", ceiling="0").status_code == 422
