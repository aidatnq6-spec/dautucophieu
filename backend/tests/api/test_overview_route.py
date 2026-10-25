from datetime import date
from decimal import Decimal

import pytest

from investment_agent.market.view import EvidenceRef, PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client

PROFILE = {"as_of": "2027-01-15", "emergency_reserve": "0",
           "assets": [{"asset_id": "cash", "kind": "deposit", "amount": "1000000000", "liquidity": "liquid"}]}
SCENARIO = {"cash_flows": ["100000", "100000"], "discount_rate": "0.10", "terminal_growth": "0"}
DRAFT = {"entity_id": "FPT", "model": "fcfe_dcf", "valuation_date": "2027-01-14", "required_margin": "0.2", "tranche_fraction": "0.25",
         "scenarios": {"down": {**SCENARIO, "discount_rate": "0.12"}, "base": SCENARIO, "up": {**SCENARIO, "discount_rate": "0.09"}},
         "shares": 10, "sources": ["doc-fpt-1"]}
MARKET = SyntheticMarket(prices={"FPT": PricePoint(Decimal(60_000), date(2027, 1, 14))},
                         documents={"FPT": [EvidenceRef("doc-fpt-1", "BCTC quý IV/2026 (tổng hợp)", "financial_statement", "https://example.vn/fpt.pdf", "2027-01-10", "FPT")]},
                         industries={"FPT": "tech"})


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(clock):
    return make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()), market=MARKET)


def setup_owner(client, clock, answers="C"):
    preview = call(client, clock, "POST", "/internal/profile/assessment", {"profile": PROFILE, "ledger_value": None}).json()
    call(client, clock, "PUT", "/internal/profile", {"profile": PROFILE, "ledger_value": None, "reviewed_net": preview["net"], "expected_version": 0, "request_id": "p1"})
    call(client, clock, "PUT", "/internal/risk", {"answers": [{"question": n, "answer": answers} for n in range(1, 14)], "confirmed_conflicts": [],
                                                  "expected_version": 0, "request_id": "r1"})


def buy_fpt(client, clock):
    call(client, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "d1", "type": "deposit", "effective_at": "2027-01-04", "sequence": 0,
                                                                      "amount": "100000000"}, "expected_version": 0, "request_id": "l1"})
    call(client, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "b1", "type": "buy", "effective_at": "2027-01-05", "sequence": 0,
                                                                      "security_id": "FPT", "quantity": 100, "price": "50000", "fee": "0", "tax": "0"},
                                                            "expected_version": 1, "request_id": "l2"})


def test_setup_incomplete_gives_insufficient_basis_and_no_items(client, clock):
    body = call(client, clock, "GET", "/internal/overview").json()
    assert body["setup"] == {"fee_rate_configured": False, "profile": False, "risk": False, "ledger_version": 0, "universe_version": 0,
                             "universe_status": None}
    assert body["decision"]["action"] == "insufficient_basis" and "setup_incomplete" in body["decision"]["reasons"]
    assert body["provenance"] == "synthetic"


def test_holding_outside_universe_is_valued_and_kept(client, clock):
    setup_owner(client, clock)
    buy_fpt(client, clock)
    body = call(client, clock, "GET", "/internal/overview").json()
    row = body["holdings"][0]
    assert (row["security_id"], row["market_value"], row["unrealized_gain"], row["scope"]) == ("FPT", "6000000", "1000000", "held_outside_universe")
    assert row["price_date"] == "2027-01-14" and row["quality_status"] == "verified"
    item = body["items"][0]
    assert item["entity_id"] == "FPT" and item["action"] == "hold" and "outside_research_universe" in item["reasons"]


def test_recommendation_carries_valuation_sources_once_approved(client, clock):
    setup_owner(client, clock)
    buy_fpt(client, clock)
    call(client, clock, "PUT", "/internal/valuation/FPT/draft", {"assumptions": DRAFT, "expected_version": 0, "request_id": "v1"})
    call(client, clock, "POST", "/internal/valuation/FPT/approve", {"draft_version": 1, "request_id": "v2"})
    item = call(client, clock, "GET", "/internal/overview").json()["items"][0]
    assert item["source_ids"] == ["doc-fpt-1"] and item["assumption_version"] == 2


def test_missing_price_is_reported_not_zero(clock):
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))  # EmptyMarket
    setup_owner(client, clock)
    buy_fpt(client, clock)
    body = call(client, clock, "GET", "/internal/overview").json()
    assert body["provenance"] == "none"
    assert body["holdings"][0]["market_value"] is None and body["holdings"][0]["quality_status"] == "missing"
    assert "price_missing:FPT" in body["quality_notes"]


def test_research_detail_lists_evidence_and_valuation_status(client, clock):
    setup_owner(client, clock)
    call(client, clock, "PUT", "/internal/valuation/FPT/draft", {"assumptions": DRAFT, "expected_version": 0, "request_id": "v1"})
    body = call(client, clock, "GET", "/internal/research/FPT").json()
    assert body["evidence"][0]["evidence_id"] == "doc-fpt-1" and body["evidence"][0]["source_url"].startswith("https://")
    assert body["valuation"]["valuation"]["status"] == "draft" and body["valuation"]["valuation"]["buy_zone_active"] is False
    assert body["price"] == {"price": "60000", "session_date": "2027-01-14"}


def test_research_detail_for_unknown_entity_has_no_fake_values(client, clock):
    body = call(client, clock, "GET", "/internal/research/VNM").json()
    assert body["price"] is None and body["evidence"] == [] and body["valuation"] is None


def test_universe_proposals_are_listed_with_decisions(client, clock):
    cand = {"entity_id": "FPT", "ticker": "FPT", "exchange": "HOSE", "industry": "tech",
            "evidence": {"source": "verified_audit", "eligible": True, "live_eligible": True, "history_years": 10, "gaps": []}, "metrics": None}
    for pid in ("p1", "p2"):
        call(client, clock, "POST", "/internal/universe/proposals", {"proposal_id": pid, "as_of": "2027-01-15", "candidates": [cand], "request_id": f"rq-{pid}"})
    call(client, clock, "POST", "/internal/universe/proposals/p1/reject", {"request_id": "x1"})
    listed = call(client, clock, "GET", "/internal/universe/proposals").json()["proposals"]
    assert [(p["proposal"]["proposal_id"], p["decision"]) for p in listed] == [("p1", "rejected"), ("p2", "pending")]


def test_trading_settings_supply_the_owner_fee_rate(client, clock):
    setup_owner(client, clock)
    assert call(client, clock, "GET", "/internal/overview").json()["setup"]["fee_rate_configured"] is False
    bad = call(client, clock, "PUT", "/internal/settings/trading", {"settings": {"fee_rate": 0.0015}, "expected_version": 0, "request_id": "t0"})
    assert bad.status_code == 422
    saved = call(client, clock, "PUT", "/internal/settings/trading", {"settings": {"fee_rate": "0.0015"}, "expected_version": 0, "request_id": "t1"})
    assert saved.json()["settings"] == {"fee_rate": "0.0015"}
    assert call(client, clock, "GET", "/internal/settings/trading").json()["settings"]["fee_rate"] == "0.0015"
    assert call(client, clock, "GET", "/internal/overview").json()["setup"]["fee_rate_configured"] is True
