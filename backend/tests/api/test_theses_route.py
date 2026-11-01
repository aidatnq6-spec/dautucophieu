from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def _held(c, clock, symbol="FPT", price="50000"):
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "d1", "type": "deposit", "effective_at": "2026-02-02", "sequence": 0,
                                                                 "amount": "100000000"}, "expected_version": 0, "request_id": "l1"})
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "b1", "type": "buy", "effective_at": "2026-02-03", "sequence": 0,
                                                                 "security_id": symbol, "quantity": 100, "price": price, "fee": "0", "tax": "0"},
                                                       "expected_version": 1, "request_id": "l2"})


FOMO = {"reasons": ["fomo"], "note": "Ai cũng mua", "conditions": [{"kind": "loss_vs_cost", "params": {"pct": "10"}}]}


def test_theses_are_listed_with_held_tickers_missing_one_and_the_condition_catalogue(tmp_path):
    clock = Clock()
    c = client(tmp_path, clock)
    _held(c, clock)
    view = call(c, clock, "GET", "/internal/theses").json()
    assert view["version"] == 0 and view["theses"] == [] and view["missing"] == ["FPT"]
    assert view["companies"] == {"FPT": None}  # sector unknown here: the form offers every condition, the server checks
    assert view["kinds"]["loss_vs_cost"] == {"label": "Lỗ so với giá vốn", "params": ["pct"], "applies": None}
    assert view["reasons"]["fomo"] == "Sợ bỏ lỡ"


def test_a_thesis_is_saved_shown_with_live_states_and_refused_when_invalid(tmp_path):
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2026, 10, 28) + timedelta(days=i), v) for i, v in enumerate(["50", "44"])])
    clock = Clock()
    c = client(tmp_path, clock)
    _held(c, clock)
    refused = call(c, clock, "PUT", "/internal/theses", {"action": "save", "symbol": "FPT", "reasons": ["fomo"], "note": "",
                                                          "conditions": [{"kind": "macd_weekly", "params": {}}], "expected_version": 0, "request_id": "t0"})
    assert refused.status_code == 422 and refused.json()["code"] == "loss_limit_required"
    saved = call(c, clock, "PUT", "/internal/theses", {"action": "save", "symbol": "FPT", **FOMO, "expected_version": 0, "request_id": "t1"}).json()
    assert saved["version"] == 1 and saved["missing"] == []
    cond = saved["theses"][0]["conditions"][0]
    assert cond["view"] == {"state": "broken", "reading": "giá 44,00 so với giá vốn 50,00 (−12,0%)", "reason": None}  # broken at once
    assert cond["label"] == "Lỗ so với giá vốn (10%)"
    stale = call(c, clock, "PUT", "/internal/theses", {"action": "save", "symbol": "FPT", **FOMO, "expected_version": 0, "request_id": "t2"})
    assert stale.status_code in (409, 422)
    journal = call(c, clock, "GET", "/internal/journal").json()
    assert any(e["kind"] == "buy" and "Ai cũng mua" in e["reason"] for e in journal["entries"])
    held_on = call(c, clock, "PUT", "/internal/theses", {"action": "hold", "thesis_id": saved["theses"][0]["id"], "cond_id": cond["id"],
                                                          "reason": "Chờ kết quả quý 4", "emotion": "anxious", "until": "2027-02-15",
                                                          "expected_version": 1, "request_id": "h1"}).json()
    assert held_on["theses"][0]["conditions"][0]["hold"]["until"] == "2027-02-15"
    journal = call(c, clock, "GET", "/internal/journal").json()
    assert any(e["kind"] == "hold" and "Chờ kết quả quý 4" in e["reason"] for e in journal["entries"])


def test_without_personal_store_theses_are_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/theses").status_code == 503
