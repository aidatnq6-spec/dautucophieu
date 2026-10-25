from datetime import date
from decimal import Decimal

from investment_agent.jobs.runner import JobStore
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client


class Outbox:
    def __init__(self):
        self.queued = []

    def enqueue(self, report_id):
        self.queued.append(report_id)


def client_with_jobs(tmp_path, clock):
    outbox = Outbox()
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()),
                         market=SyntheticMarket(prices={"FPT": PricePoint(Decimal(60000), date(2027, 1, 14))}),
                         jobs=JobStore(tmp_path / "jobs.sqlite"), outbox=outbox)
    return client, outbox


def test_job_accepted_then_report_listed_and_readable(tmp_path):
    clock = Clock()
    client, outbox = client_with_jobs(tmp_path, clock)
    accepted = call(client, clock, "POST", "/internal/jobs/after-close", {"session_date": "2027-01-14"})
    assert accepted.status_code == 202
    job = call(client, clock, "GET", f"/internal/jobs/{accepted.json()['job_id']}").json()
    assert job["status"] == "incomplete" and job["report_id"]  # no profile/survey yet
    listed = call(client, clock, "GET", "/internal/reports").json()["reports"]
    assert listed[0]["report_id"] == job["report_id"] and listed[0]["session_date"] == "2027-01-14"
    detail = call(client, clock, "GET", f"/internal/reports/{job['report_id']}").json()
    assert detail["status"] == "incomplete" and detail["narrative"]["source"] == "no_ai" and outbox.queued == []


def test_session_date_cannot_be_in_the_future(tmp_path):
    clock = Clock()
    client, _ = client_with_jobs(tmp_path, clock)
    response = call(client, clock, "POST", "/internal/jobs/after-close", {"session_date": "2027-01-16"})
    assert response.status_code == 422 and response.json()["code"] == "session_in_future"


def test_jobs_unavailable_without_job_store(tmp_path):
    clock = Clock()
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    assert call(client, clock, "POST", "/internal/jobs/after-close", {"session_date": "2027-01-14"}).status_code == 503


def test_unknown_job_and_report(tmp_path):
    clock = Clock()
    client, _ = client_with_jobs(tmp_path, clock)
    assert call(client, clock, "GET", "/internal/jobs/nope").status_code == 404
    assert call(client, clock, "GET", "/internal/reports/nope").status_code == 404
