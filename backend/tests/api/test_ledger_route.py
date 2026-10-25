import pytest

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client


@pytest.fixture
def store():
    return MemoryDocumentStore()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(store, clock):
    return make_client(clock, PersonalRepository("owner-1", store))


def add(client, clock, event, *, version, request_id):
    return call(client, clock, "POST", "/internal/ledger/events", {"event": event, "expected_version": version, "request_id": request_id})


DEPOSIT = {"event_id": "d1", "type": "deposit", "effective_at": "2027-01-04", "sequence": 0, "amount": "10000000"}
BUY = {"event_id": "b1", "type": "buy", "effective_at": "2027-01-05", "sequence": 0, "security_id": "ent-fpt",
       "quantity": 100, "price": "20000", "fee": "3000", "tax": "0"}


def test_empty_ledger_reads_as_version_zero(client, clock):
    body = call(client, clock, "GET", "/internal/ledger").json()
    assert body["version"] == 0 and body["events"] == [] and body["state"]["cash"] == "0"


def test_appending_events_versions_whole_ledger(client, clock):
    assert add(client, clock, DEPOSIT, version=0, request_id="r1").json()["version"] == 1
    body = add(client, clock, BUY, version=1, request_id="r2").json()
    assert body["version"] == 2 and body["state"]["cash"] == "7997000"
    assert body["state"]["positions"] == [{"security_id": "ent-fpt", "quantity": 100, "pending_quantity": 0,
                                         "total_cost": "2003000", "average_cost": "20030", "blocked_by": []}]
    assert [e["event_id"] for e in call(client, clock, "GET", "/internal/ledger").json()["events"]] == ["d1", "b1"]


def test_retry_does_not_duplicate_event(client, clock):
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    assert add(client, clock, DEPOSIT, version=0, request_id="r1").json()["version"] == 1
    assert call(client, clock, "GET", "/internal/ledger").json()["state"]["deposits"] == "10000000"


def test_stale_version_rejected(client, clock):
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    response = add(client, clock, BUY, version=0, request_id="r2")
    assert response.status_code == 409 and response.json()["code"] == "version_conflict"


@pytest.mark.parametrize("event, code", [
    ({**BUY, "event_id": "s1", "type": "sell"}, "ledger_oversell"),
    (BUY, "ledger_cash_negative"),
    ({**DEPOSIT, "event_id": "d2"}, "ledger_ambiguous_order"),
    ({**DEPOSIT}, "ledger_duplicate_event"),
])
def test_impossible_events_are_rejected_without_writing(client, clock, store, event, code):
    if code != "ledger_cash_negative":
        add(client, clock, DEPOSIT, version=0, request_id="r1")
    before = dict(store.documents)
    response = add(client, clock, event, version=1 if code != "ledger_cash_negative" else 0, request_id="r2")
    assert response.status_code == 422 and response.json()["code"] == code
    assert store.documents == before


def test_float_amount_is_rejected(client, clock):
    response = add(client, clock, {**DEPOSIT, "amount": 10000000.0}, version=0, request_id="r1")
    assert response.status_code == 422 and response.json()["code"] == "invalid_request"


def test_unavailable_repository_refuses_mutation(client, clock, store):
    store.available = False
    assert add(client, clock, DEPOSIT, version=0, request_id="r1").status_code == 503
