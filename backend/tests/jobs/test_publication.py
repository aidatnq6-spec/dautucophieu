from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.jobs.daily import run_after_close
from investment_agent.jobs.publication import list_reports
from investment_agent.jobs.runner import JobStore, LeaseBusy
from investment_agent.market.view import EvidenceRef, PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.profile import ConfirmedProfile
from investment_agent.domain.risk import assess_risk, load_questionnaire

OWNER = OwnerContext("owner-1", "owner", "job")
RUN_AT = datetime(2026, 10, 23, 11, 0, tzinfo=timezone.utc)  # 18:00 in Hanoi
SESSION = date(2026, 10, 23)
MARKET = SyntheticMarket(prices={"FPT": PricePoint(Decimal(60_000), SESSION)},
                         documents={"FPT": [EvidenceRef("doc-1", "BCTC (tổng hợp)", "financial_statement", "https://example.invalid/1", "2026-10-20")]})


class Outbox:
    def __init__(self):
        self.queued = []

    def enqueue(self, report_id):  # idempotent, like DeliveryStore.enqueue
        if report_id not in self.queued:
            self.queued.append(report_id)


@pytest.fixture
def repo():
    r = PersonalRepository("owner-1", MemoryDocumentStore())
    profile = FinancialProfile.model_validate({"as_of": "2026-10-01", "emergency_reserve": "200000000",
        "assets": [{"asset_id": "cash", "kind": "deposit", "amount": "1200000000", "liquidity": "liquid",
                    "earmarks": [{"purpose": "emergency", "amount": "200000000"}]}],
        "goals": [{"goal_id": "debt-payment", "due_date": "2027-03-01", "amount": "77700000", "preserve_capital": False, "deferrable": False, "confirmed": True}]})
    confirmed = ConfirmedProfile(profile=profile, assessment=assess_capital(profile, ledger_value=None), confirmed_at="2026-10-20T00:00:00+00:00")
    r.write(OWNER, "profile_versions", "main", confirmed.model_dump(mode="json"), expected_version=0, request_id="p1")
    risk = assess_risk(load_questionnaire(), [{"question": n, "answer": "C"} for n in range(1, 14)])
    r.write(OWNER, "risk_versions", "main", {"schema_version": "1", "assessment": risk.model_dump(mode="json"),
                                             "assessed_at": "2026-10-20T00:00:00+00:00", "profile_version": 1}, expected_version=0, request_id="r1")
    events = [{"event_id": "d1", "type": "deposit", "effective_at": "2026-10-01", "sequence": 0, "amount": "100000000"},
              {"event_id": "b1", "type": "buy", "effective_at": "2026-10-02", "sequence": 0, "security_id": "FPT", "quantity": 100, "price": "50000",
               "fee": "0", "tax": "0"}]
    r.write(OWNER, "ledger_events", "main", {"schema_version": "2", "events": events, "amendments": [], "changes": []}, expected_version=0, request_id="l1")
    return r


def run(repo, tmp_path, *, market=MARKET, outbox=None, narrate=None, hook=None):
    return run_after_close(repo=repo, owner=OWNER, market=market, jobs=JobStore(tmp_path / "jobs.sqlite"), outbox=outbox or Outbox(),
                           session_date=SESSION, now=RUN_AT, narrate=narrate, before_publish=hook, worker_id="w1")


def test_publishes_once_and_queues_notification_after_persisting(repo, tmp_path):
    outbox = Outbox()
    first = run(repo, tmp_path, outbox=outbox)
    assert first.status == "published" and outbox.queued == [first.report_id]
    report = repo.read(OWNER, "reports", first.report_id).payload
    assert report["status"] == "published" and report["session_date"] == "2026-10-23"
    assert report["generated_at"].startswith("2026-10-23T11:00")
    second = run(repo, tmp_path, outbox=outbox)
    assert second.report_id == first.report_id and second.status == "published" and outbox.queued == [first.report_id]
    assert [r["report_id"] for r in list_reports(repo, OWNER)] == [first.report_id]


def test_inputs_changing_during_the_job_block_publication(repo, tmp_path):
    def change_profile():
        head = repo.read(OWNER, "profile_versions", "main")
        repo.write(OWNER, "profile_versions", "main", head.payload, expected_version=head.version, request_id="p-race")
    outbox = Outbox()
    result = run(repo, tmp_path, outbox=outbox, hook=change_profile)
    assert result.status == "failed" and result.reason == "inputs_changed" and outbox.queued == []
    assert list_reports(repo, OWNER) == []
    rerun = run(repo, tmp_path, outbox=outbox)
    assert rerun.status == "published" and rerun.report_id != result.report_id


def test_ai_failure_still_publishes_verified_numbers(repo, tmp_path):
    def broken(content):
        raise RuntimeError("model down")
    result = run(repo, tmp_path, narrate=broken)
    report = repo.read(OWNER, "reports", result.report_id).payload
    assert result.status == "published" and report["narrative"]["source"] == "no_ai"
    assert "FPT" in report["narrative"]["text"] and "ai_unavailable" in report["verification_flags"]


def test_missing_data_makes_report_incomplete_and_not_sent(repo, tmp_path):
    outbox = Outbox()
    result = run(repo, tmp_path, outbox=outbox, market=SyntheticMarket())
    report = repo.read(OWNER, "reports", result.report_id).payload
    assert result.status == "incomplete" and report["status"] == "incomplete" and outbox.queued == []
    assert "price_missing:FPT" in report["verification_flags"]


def test_report_has_portfolio_values_but_no_private_financial_detail(repo, tmp_path):
    result = run(repo, tmp_path)
    text = str(repo.read(OWNER, "reports", result.report_id).payload)
    assert "6000000" in text  # FPT market value
    for private in ("1200000000", "200000000", "77700000", "debt-payment", "emergency"):
        assert private not in text


def test_concurrent_worker_with_live_lease_is_refused(repo, tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite")
    store.acquire("key-1", worker_id="w1", now=RUN_AT.timestamp(), ttl=600)
    with pytest.raises(LeaseBusy):
        store.acquire("key-1", worker_id="w2", now=RUN_AT.timestamp() + 10, ttl=600)
    store.acquire("key-1", worker_id="w2", now=RUN_AT.timestamp() + 601, ttl=600)  # expired lease can be taken over


def test_stage_checkpoints_are_recorded(repo, tmp_path):
    result = run(repo, tmp_path)
    store = JobStore(tmp_path / "jobs.sqlite")
    assert store.get(result.job_id)["stages"] == ["snapshot", "compose", "narrate", "publish", "notify"]


def test_previous_report_of_same_scope_is_linked(repo, tmp_path):
    first = run(repo, tmp_path)
    head = repo.read(OWNER, "ledger_events", "main")
    payload = dict(head.payload)
    payload["events"] = [*payload["events"], {"event_id": "d2", "type": "deposit", "effective_at": "2026-10-23", "sequence": 0, "amount": "1000"}]
    repo.write(OWNER, "ledger_events", "main", payload, expected_version=head.version, request_id="l2")
    second = run(repo, tmp_path)
    report = repo.read(OWNER, "reports", second.report_id).payload
    assert second.report_id != first.report_id and report["previous_report_id"] == first.report_id


def test_price_from_an_earlier_session_keeps_the_report_unpublished(repo, tmp_path):
    # An early slot can run before the vendor has today's bar; yesterday's close must not be published as today's.
    outbox = Outbox()
    stale = SyntheticMarket(prices={"FPT": PricePoint(Decimal(60_000), date(2026, 10, 22))}, documents=MARKET.documents)
    result = run(repo, tmp_path, outbox=outbox, market=stale)
    report = repo.read(OWNER, "reports", result.report_id).payload
    assert result.status == "incomplete" and outbox.queued == []
    assert "price_not_for_session:FPT" in report["verification_flags"]
