from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # FPT bought 100 × 50,000 on 05/01/2027; MARKET prices FPT at 60,000


def client(repo=True):
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, market=MARKET)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    if repo:
        setup_owner(c, clock)
        buy_fpt(c, clock)
    return c, clock


def test_baskets_start_empty_with_every_period_untagged():
    c, clock = client()
    body = call(c, clock, "GET", "/internal/baskets").json()
    assert body["version"] == 0 and body["data"] == {"baskets": [], "tags": {}}
    assert body["view"]["periods"] == [{"key": "FPT@2027-01-05", "symbol": "FPT", "start": "2027-01-05", "end": None, "basket": None}]
    (untagged,) = body["view"]["rows"]
    assert untagged["id"] is None and untagged["open"] == 1 and untagged["unrealised"] == "1000000"


def test_a_basket_is_named_and_a_period_tagged_with_a_version():
    c, clock = client()
    data = {"baskets": [{"id": "b1", "name": "Dài hạn"}], "tags": {"FPT@2027-01-05": "b1"}}
    saved = call(c, clock, "PUT", "/internal/baskets", {**data, "expected_version": 0, "request_id": "k1"})
    assert saved.status_code == 200 and saved.json()["version"] == 1
    long_, untagged = saved.json()["view"]["rows"]
    assert long_["name"] == "Dài hạn" and long_["open"] == 1 and untagged["open"] == 0
    assert call(c, clock, "PUT", "/internal/baskets", {**data, "expected_version": 0, "request_id": "k2"}).status_code == 409


def test_bad_baskets_are_refused():
    c, clock = client()
    def put(data, rid):
        return call(c, clock, "PUT", "/internal/baskets", {**data, "expected_version": 0, "request_id": rid}).status_code
    nine = [{"id": f"b{i}", "name": f"Giỏ {i}"} for i in range(9)]
    assert put({"baskets": nine, "tags": {}}, "k1") == 422
    assert put({"baskets": [{"id": "b1", "name": "A"}, {"id": "b1", "name": "B"}], "tags": {}}, "k2") == 422
    assert put({"baskets": [{"id": "b1", "name": "A"}, {"id": "b2", "name": "A"}], "tags": {}}, "k3") == 422
    assert put({"baskets": [{"id": "b1", "name": "A"}], "tags": {"FPT@2027-01-05": "b9"}}, "k4") == 422


def test_without_personal_store_baskets_are_unavailable():
    c, clock = client(repo=False)
    assert call(c, clock, "GET", "/internal/baskets").status_code == 503
