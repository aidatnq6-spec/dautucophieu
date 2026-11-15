from datetime import date

from investment_agent.api.auth import OwnerContext
from investment_agent.market.leading import MacroStore
from investment_agent.services.macro_events import remind

from signed_client import call
from test_deposit_book_route import client


def test_the_spread_reads_the_stored_overnight_rates(tmp_path):
    store = MacroStore(tmp_path)
    store.upsert("vn_interbank_on", [(date(2026, 11, 12), "3.5"), (date(2026, 11, 13), "4.2")], entry="auto")
    store.upsert("sofr", [(date(2026, 11, 12), "3.9")], entry="auto")
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/macro/spread").json()
    assert body["latest"]["spread"] == "0.3" and body["negative_days"] == 1 and len(body["points"]) == 2


def test_events_are_saved_and_reminded_once_the_day_before(tmp_path):
    c, clock = client(tmp_path)
    ev = [{"id": "fed1", "date": "2027-02-09", "title": "Fed họp chính sách", "kind": "fed", "source": "federalreserve.gov", "remind": True},
          {"id": "sbv1", "date": "2027-01-09", "title": "NHNN hoán đổi ngoại tệ", "kind": "sbv", "source": "sbv.gov.vn"}]
    body = call(c, clock, "PUT", "/internal/macro/events", {"events": ev, "expected_version": 0, "request_id": "me1"}).json()
    assert body["version"] == 1 and [e["id"] for e in body["past"]] == ["sbv1"] and body["coming"][0]["id"] == "fed1"
    bad = call(c, clock, "PUT", "/internal/macro/events", {"events": [{**ev[0], "date": "9/12"}], "expected_version": 1, "request_id": "me2"})
    assert bad.status_code == 422
    owner, sent = OwnerContext(uid="owner-1", role="owner", correlation_id="t"), []
    send = lambda text: sent.append(text) or True  # noqa: E731
    repo = c.app.state.personal_repository
    assert remind(repo, owner, send=send, today=date(2027, 2, 7), request_id="mev-rem0")["due"] == 0
    assert remind(repo, owner, send=send, today=date(2027, 2, 8), request_id="mev-rem1") == {"status": "ok", "due": 1, "sent": True}
    assert "09/02/2027 [Fed] Fed họp chính sách — nguồn: federalreserve.gov" in sent[0]
    assert remind(repo, owner, send=send, today=date(2027, 2, 8), request_id="mev-rem2")["due"] == 0 and len(sent) == 1
    view = call(c, clock, "GET", "/internal/macro/events").json()
    assert view["version"] == 2 and view["coming"][0]["reminded_on"] == "2027-02-08"
