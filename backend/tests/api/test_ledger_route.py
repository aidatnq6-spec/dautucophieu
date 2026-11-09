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


def amend(client, clock, amendment, *, version, request_id):
    return call(client, clock, "POST", "/internal/ledger/amendments", {"amendment": amendment, "expected_version": version, "request_id": request_id})


FIX = {"amendment_id": "a1", "action": "replace", "target_event_id": "b1", "reason": "Sai giá theo sao kê",
       "replacement": {**BUY, "effective_at": "2027-01-04", "sequence": 1, "price": "21000"}}


def test_correction_replays_records_audit_and_change_log(client, clock):
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    add(client, clock, BUY, version=1, request_id="r2")
    body = amend(client, clock, FIX, version=2, request_id="r3").json()
    assert body["version"] == 3 and body["state"]["positions"][0]["total_cost"] == "2103000"
    assert body["audit"][0]["before"]["price"] == "20000" and body["audit"][0]["after"]["price"] == "21000"
    assert body["changes"] == [{"ledger_version": 1, "affected_from": "2027-01-04"}, {"ledger_version": 2, "affected_from": "2027-01-05"},
                               {"ledger_version": 3, "affected_from": "2027-01-04"}]
    assert [e["event_id"] for e in body["original_events"]] == ["d1", "b1"]


def test_correction_retry_is_idempotent(client, clock):
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    add(client, clock, BUY, version=1, request_id="r2")
    first = amend(client, clock, FIX, version=2, request_id="r3").json()
    again = amend(client, clock, FIX, version=2, request_id="r3").json()
    assert again["version"] == first["version"] == 3 and len(again["audit"]) == 1


def test_cancel_then_restore_through_api(client, clock):
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    add(client, clock, BUY, version=1, request_id="r2")
    cancel = {"amendment_id": "a1", "action": "cancel", "target_event_id": "b1", "reason": "Nhập nhầm"}
    assert amend(client, clock, cancel, version=2, request_id="r3").json()["state"]["positions"] == []
    restore = {"amendment_id": "a2", "action": "restore", "target_event_id": "b1", "reason": "Khôi phục"}
    assert amend(client, clock, restore, version=3, request_id="r4").json()["state"]["cash"] == "7997000"


def test_correction_breaking_later_events_is_rejected(client, clock, store):
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    add(client, clock, BUY, version=1, request_id="r2")
    before = dict(store.documents)
    cancel_deposit = {"amendment_id": "a1", "action": "cancel", "target_event_id": "d1", "reason": "x"}
    response = amend(client, clock, cancel_deposit, version=2, request_id="r3")
    assert response.status_code == 422 and response.json()["code"] == "ledger_cash_negative"
    assert store.documents == before


def _statement(*lines):
    import base64
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[1] / "domain"))
    from test_tcbs_statement import book
    return base64.b64encode(book(*lines)).decode()


def test_a_tcbs_statement_is_previewed_then_imported_once(client, clock):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[1] / "domain"))
    from test_tcbs_statement import line
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    content = _statement(line("FPT", "05/01/2027", "Mua", 100, 20000, 300, 0, order="111"), line("FPT", "06/01/2027", "Bán", 40, 25000, 100, 1000, order="222"), line("FPT", "31/02/2026", order="333"))
    url = "/internal/ledger/import-tcbs"
    preview = call(client, clock, "POST", url, {"content_base64": content, "expected_version": 1, "request_id": "p1"}).json()
    assert preview["counts"]["new"] == 2 and preview["blocked"] is None and preview["problems"][0]["line"] == 8 and preview["version"] == 1
    assert len(call(client, clock, "GET", "/internal/ledger").json()["events"]) == 1  # a preview writes nothing
    done = call(client, clock, "POST", url, {"content_base64": content, "commit": True, "expected_version": 1, "request_id": "c1"}).json()
    assert [e["event_id"] for e in done["events"]][-2:] == ["tcbs-111", "tcbs-222"] and done["state"]["fees_paid"] == "400" and done["state"]["taxes_paid"] == "1000"
    again = call(client, clock, "POST", url, {"content_base64": content, "expected_version": 2, "request_id": "p2"}).json()
    assert again["counts"]["already"] == 2 and again["counts"]["new"] == 0
    assert call(client, clock, "POST", url, {"content_base64": content, "commit": True, "expected_version": 2, "request_id": "c2"}).status_code == 422


def test_a_statement_the_ledger_cannot_hold_writes_nothing(client, clock):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[1] / "domain"))
    from test_tcbs_statement import line
    add(client, clock, DEPOSIT, version=0, request_id="r1")
    content = _statement(line("FPT", "06/01/2027", "Bán", 40, 25000, 100, 1000, order="222"))
    url = "/internal/ledger/import-tcbs"
    preview = call(client, clock, "POST", url, {"content_base64": content, "expected_version": 1, "request_id": "p1"}).json()
    assert preview["blocked"]["code"] == "oversell" and preview["blocked"]["symbol"] == "FPT"
    r = call(client, clock, "POST", url, {"content_base64": content, "commit": True, "expected_version": 1, "request_id": "c1"})
    assert r.status_code == 422 and r.json()["code"] == "ledger_oversell"
    assert len(call(client, clock, "GET", "/internal/ledger").json()["events"]) == 1
    assert call(client, clock, "POST", url, {"content_base64": "bm90IHppcA==", "expected_version": 1, "request_id": "b1"}).json()["code"] == "invalid_file"
