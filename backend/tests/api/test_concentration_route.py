from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client
from test_overview_route import MARKET, buy_fpt, setup_owner


def client_with_holding():
    clock = Clock()
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()), market=MARKET)
    setup_owner(client, clock)
    buy_fpt(client, clock)
    return client, clock


def test_concentration_uses_cost_on_investable_capital_and_the_owners_limit():
    client, clock = client_with_holding()
    body = call(client, clock, "GET", "/internal/concentration").json()
    assert body["status"] == "ok" and body["limit"] == "0.25"
    fpt = body["tickers"][0]
    assert fpt["symbol"] == "FPT" and fpt["value"] == "5000000" and fpt["over"] is False  # cost 100 × 50,000 (market 60,000) on 1 tỷ
    assert body["cash"]["value"] == "995000000" and body["valued_at"] == "cost"
    saved = call(client, clock, "PUT", "/internal/settings/portfolio",
                 {"settings": {"concentration_limit": "0.004"}, "expected_version": 0, "request_id": "pf1"})
    assert saved.status_code == 200
    again = call(client, clock, "GET", "/internal/concentration").json()
    assert again["limit"] == "0.004" and again["tickers"][0]["over"] is True


def test_what_if_is_computed_without_recording_anything():
    client, clock = client_with_holding()
    sim = call(client, clock, "GET", "/internal/concentration/whatif/fpt/294000000").json()
    assert sim["tickers"][0]["value"] == "299000000" and sim["tickers"][0]["over"] is True
    assert call(client, clock, "GET", "/internal/concentration").json()["tickers"][0]["value"] == "5000000"


def test_limit_must_be_a_sensible_ratio():
    client, clock = client_with_holding()
    bad = call(client, clock, "PUT", "/internal/settings/portfolio", {"settings": {"concentration_limit": "1.5"}, "expected_version": 0, "request_id": "pf2"})
    assert bad.status_code == 422
