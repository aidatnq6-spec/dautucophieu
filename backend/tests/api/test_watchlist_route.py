import json
from datetime import date
from decimal import Decimal

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from fastapi.testclient import TestClient

OWNER_EVENTS = [{"event_id": "d1", "type": "deposit", "effective_at": "2026-10-01", "sequence": 0, "amount": "100000000"},
                {"event_id": "b1", "type": "buy", "effective_at": "2026-10-02", "sequence": 0, "security_id": "MBB", "quantity": 100,
                 "price": "20000", "fee": "0", "tax": "0"}]


def client(tmp_path, repo, clock):
    (tmp_path / "market-symbols.txt").write_text("MBB\nFPT\n", encoding="utf-8")
    (tmp_path / "index-groups.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "groups": {"VN30": ["FPT", "MBB"]}}),
                                                encoding="utf-8")
    market = SyntheticMarket(prices={"FPT": PricePoint(Decimal(57_000), date(2026, 10, 23))})
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=repo, market=market, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_watchlist_lists_prices_groups_and_held_flags(tmp_path):
    clock, repo = Clock(), PersonalRepository("owner-1", MemoryDocumentStore())
    from investment_agent.api.auth import OwnerContext
    repo.write(OwnerContext("owner-1", "owner", "t"), "ledger_events", "main",
               {"schema_version": "2", "events": OWNER_EVENTS, "amendments": [], "changes": []}, expected_version=0, request_id="l1")
    body = call(client(tmp_path, repo, clock), clock, "GET", "/internal/watchlist").json()
    assert body["groups_as_of"] == "2026-10-25" and body["provenance"] == "synthetic"
    assert [(r["ticker"], r["held"], r["close"]) for r in body["rows"]] == [("MBB", True, None), ("FPT", False, "57000")]


def test_watchlist_without_personal_store_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, None, clock), clock, "GET", "/internal/watchlist").status_code == 503
