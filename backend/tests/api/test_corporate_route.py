from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.corporate_events import EventStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


EVENT = {"id": "FPT-1", "symbol": "FPT", "kind": "dividend_cash", "code": "DIV", "title": "Trả cổ tức bằng tiền mặt - FPT", "key_date": "2026-12-01",
         "exright": "2026-12-01", "record": "2026-12-02", "payout": "2026-12-20", "ratio": 0.1, "value_per_share": 1000.0}


def test_drafts_costs_and_dismissing(tmp_path):
    EventStore(tmp_path).save("FPT", [EVENT], fetched_at="2027-01-01T00:00:00+00:00")
    clock = Clock()  # 15/01/2027
    c = client(tmp_path, clock)
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "d1", "type": "deposit", "effective_at": "2026-02-02", "sequence": 0,
                                                                 "amount": "100000000"}, "expected_version": 0, "request_id": "l1"})
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "b1", "type": "buy", "effective_at": "2026-02-03", "sequence": 0,
                                                                 "security_id": "FPT", "quantity": 100, "price": "50000", "fee": "7500", "tax": "0"},
                                                       "expected_version": 1, "request_id": "l2"})
    view = call(c, clock, "GET", "/internal/ledger/corporate").json()
    s = view["suggestions"][0]
    assert s["status"] == "to_record" and s["draft"]["expected_gross"] == "100000" and s["draft"]["expected_tax"] == "5000"
    assert view["costs"] == [{"year": 2026, "sell_value": "0", "fees": "7500", "sell_tax": "0", "dividends": "0", "dividend_tax": "0", "total": "7500"}]
    gone = call(c, clock, "PUT", "/internal/ledger/corporate", {"action": "dismiss", "id": "FPT-1", "expected_version": 0, "request_id": "x1"}).json()
    assert gone["suggestions"] == [] and gone["dismissed"] == [{"id": "FPT-1", "symbol": "FPT", "title": "Trả cổ tức bằng tiền mặt - FPT",
                                                                 "exright": "2026-12-01"}]
    back = call(c, clock, "PUT", "/internal/ledger/corporate", {"action": "restore", "id": "FPT-1", "expected_version": 1, "request_id": "x2"}).json()
    assert back["suggestions"][0]["id"] == "FPT-1" and back["dismissed"] == []


def test_without_personal_store_it_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/ledger/corporate").status_code == 503
