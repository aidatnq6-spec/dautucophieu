from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.beta import BetaStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_holdings_values_betas_and_the_owners_answer_ten(tmp_path):
    prices = SeriesStore(tmp_path / "trend-sources")
    prices.upsert("FPT-1d", [(datetime(2026, 1, 1) + timedelta(days=i), "60") for i in range(10)])
    prices.upsert("VNINDEX-1d", [(datetime(2026, 1, 1) + timedelta(days=i), v) for i, v in enumerate(["1000", "1200", "900"])])
    BetaStore(tmp_path).save({"values": {"FPT": {"beta": "1.2", "date": "2026-10-30"}}})
    clock = Clock()
    c = client(tmp_path, clock)
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "d1", "type": "deposit", "effective_at": "2026-02-02", "sequence": 0,
                                                                 "amount": "100000000"}, "expected_version": 0, "request_id": "l1"})
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "b1", "type": "buy", "effective_at": "2026-02-03", "sequence": 0,
                                                                 "security_id": "FPT", "quantity": 100, "price": "50000", "fee": "0", "tax": "0"},
                                                       "expected_version": 1, "request_id": "l2"})
    answers = [{"question": i, "answer": "B" if i == 10 else "C"} for i in range(1, 14)]
    call(c, clock, "PUT", "/internal/risk", {"answers": answers, "confirmed_conflicts": [], "expected_version": 0, "request_id": "r1"})
    out = call(c, clock, "GET", "/internal/stress").json()
    assert out["rows"][0] | {"oil_note": None, "usd_note": None} == {
        "symbol": "FPT", "shares": 100, "price": "60000", "value": "6000000", "cost": "50000", "beta": "1.2", "beta_note": None, "oil": None, "usd": None,
        "oil_note": None, "usd_note": None}
    assert out["tolerance"]["answer"] == "B" and out["worst"]["depth"] == "-0.2500" and out["threshold"] == "0.30"


def test_without_personal_store_it_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/stress").status_code == 503
