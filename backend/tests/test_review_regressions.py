"""Regression tests for findings from the whole-branch review."""

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "api"))
from signed_client import Clock, call, make_client  # noqa: E402

from investment_agent.ai.budget import SpendLedger  # noqa: E402
from investment_agent.api.auth import OwnerContext  # noqa: E402
from investment_agent.domain.ledger import parse_events, replay  # noqa: E402
from investment_agent.domain.performance import performance  # noqa: E402
from investment_agent.jobs.daily import run_after_close  # noqa: E402
from investment_agent.jobs.publication import list_reports  # noqa: E402
from investment_agent.jobs.runner import JobStore  # noqa: E402
from investment_agent.market.view import PricePoint, SyntheticMarket  # noqa: E402
from investment_agent.notifications.outbox import DeliveryStore, NotificationSettings, deliver  # noqa: E402
from investment_agent.notifications.render import render_report, split_message  # noqa: E402
from investment_agent.notifications.telegram import TelegramSender  # noqa: E402
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository, _MemoryTransaction  # noqa: E402

OWNER = OwnerContext("owner-1", "owner", "t")
NOW = datetime(2027, 1, 15, 8, tzinfo=timezone.utc)
ANSWERS = [{"question": n, "answer": "C"} for n in range(1, 14)]
PROFILE = {"as_of": "2027-01-15", "emergency_reserve": "0", "assets": [{"asset_id": "c", "kind": "deposit", "amount": "100", "liquidity": "liquid"}]}


def ev(event_id, event_type, day, seq=0, **fields):
    return {"event_id": event_id, "type": event_type, "effective_at": day, "sequence": seq, **fields}


DEP = ev("d1", "deposit", "2026-03-02", amount="1000000")
BUY = ev("b1", "buy", "2026-03-03", security_id="X", quantity=100, price="1000", fee="0", tax="0")
ENTITLE = ev("se", "stock_dividend_entitlement", "2026-04-01", action_id="sd", security_id="X", record_date="2026-04-02",
             eligible_quantity=100, shares_entitled=10)


# Finding 1: a failing background job must surface and release its lease.
def test_failed_background_job_reports_failed(tmp_path, monkeypatch):
    from investment_agent.api.routes import jobs as jobs_route
    clock = Clock()
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()), jobs=JobStore(tmp_path / "j.sqlite"),
                         outbox=DeliveryStore(tmp_path / "d.sqlite"))
    monkeypatch.setattr(jobs_route, "run_after_close", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    job_id = call(client, clock, "POST", "/internal/jobs/after-close", {"session_date": "2027-01-14"}).json()["job_id"]
    assert call(client, clock, "GET", f"/internal/jobs/{job_id}").json()["status"] == "failed"


def test_exception_inside_pipeline_releases_lease(tmp_path):
    class BrokenOutbox:
        def enqueue(self, report_id):
            raise RuntimeError("disk")
    jobs = JobStore(tmp_path / "j.sqlite")
    with pytest.raises(RuntimeError):
        run_after_close(repo=PersonalRepository("owner-1", MemoryDocumentStore()), owner=OWNER, market=SyntheticMarket(), jobs=jobs,
                        outbox=BrokenOutbox(), session_date=date(2027, 1, 14), now=NOW, worker_id="w1",
                        before_publish=lambda: (_ for _ in ()).throw(RuntimeError("crash")))
    rows = jobs._db.execute("SELECT status FROM job_runs").fetchall()
    assert rows and all(r[0] != "running" for r in rows)


# Finding 2: a report written before a crash is indexed (and queued) on the next run.
def test_existing_unindexed_report_is_recovered(tmp_path, monkeypatch):
    from investment_agent.jobs import daily
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    kw = dict(repo=repo, owner=OWNER, market=SyntheticMarket(), jobs=JobStore(tmp_path / "j.sqlite"), outbox=DeliveryStore(tmp_path / "d.sqlite"),
              session_date=date(2027, 1, 14), now=NOW, worker_id="w1")
    real = daily.append_index
    monkeypatch.setattr(daily, "append_index", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("crash")))
    with pytest.raises(RuntimeError):
        run_after_close(**kw)
    monkeypatch.setattr(daily, "append_index", real)
    result = run_after_close(**kw)
    assert [r["report_id"] for r in list_reports(repo, OWNER)] == [result.report_id]


# Finding 3: a part left in "sending" has an unknown outcome and is not resent.
REPORT = {"report_id": "ab" * 16, "status": "published", "report_version": "1", "session_date": "2027-01-14", "provenance": "synthetic",
          "decision": {"headline": "Giữ"}, "ledger_summary": {"cash": "0", "realized_gain": "0", "dividend_income": "0"}, "holdings": [],
          "items": [], "narrative": {"text": "x"}, "verification_flags": []}
SETTINGS = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=False)


def test_sending_part_is_treated_as_unknown(tmp_path):
    store = DeliveryStore(tmp_path / "d.sqlite")
    store.ensure(REPORT["report_id"], "1", "-100123", split_message(render_report(REPORT)))
    store.set(REPORT["report_id"], "1", "-100123", 0, "sending")
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    sender = TelegramSender("1:" + "T" * 35, client=httpx.Client(transport=httpx.MockTransport(transport)))
    assert deliver(REPORT, SETTINGS, sender, store).status == "unknown" and calls == []
    store.resolve_unknown(REPORT["report_id"], "-100123", 0, outcome="received")
    assert deliver(REPORT, SETTINGS, sender, store).status == "sent" and calls == []


def test_unparseable_telegram_response_is_unknown():
    sender = TelegramSender("1:" + "T" * 35, client=httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, headers={"content-type": "application/json"}, content=b"not json"))))
    assert sender.send("-100123", "x").status == "unknown"


# Finding 4: profile and risk retries with the same request id return the committed revision.
def test_profile_and_risk_retries_are_idempotent():
    clock = Clock()
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    body = {"profile": PROFILE, "ledger_value": None, "reviewed_net": "100", "expected_version": 0, "request_id": "p1"}
    first = call(client, clock, "PUT", "/internal/profile", body)
    clock.now += 1
    again = call(client, clock, "PUT", "/internal/profile", body)
    assert again.status_code == 200 and again.json()["version"] == first.json()["version"] == 1
    risk = {"answers": ANSWERS, "confirmed_conflicts": [], "expected_version": 0, "request_id": "r1"}
    call(client, clock, "PUT", "/internal/risk", risk)
    clock.now += 1
    assert call(client, clock, "PUT", "/internal/risk", risk).status_code == 200


# Finding 5: a split also scales the pending entitlement it will later settle.
def test_split_scales_pending_entitlement():
    state = replay(parse_events([DEP, BUY, ENTITLE,
                                 ev("sp", "share_split", "2026-04-05", action_id="split", security_id="X", ratio_from=1, ratio_to=2),
                                 ev("sc", "stock_dividend_credit", "2026-05-01", action_id="sd", shares_credited=20, cash_in_lieu="0")]))
    assert (state.positions[0].quantity, state.positions[0].pending_quantity) == (220, 0)


# Finding 9: cost left on pending shares that never arrive is released, keeping reconciliation exact.
def test_zero_credit_releases_remaining_cost():
    events = parse_events([DEP, BUY, ENTITLE, ev("s1", "sell", "2026-04-10", security_id="X", quantity=100, price="1000", fee="0", tax="0"),
                           ev("sc", "stock_dividend_credit", "2026-05-01", action_id="sd", shares_credited=0, cash_in_lieu="500")])
    result = performance(events, end_prices={})
    assert result.status == "complete" and result.reconciliation_difference == 0


# Finding 6: restore reads every document before writing any (Firestore transaction rule).
def test_import_reads_before_writes():
    class Tx(_MemoryTransaction):
        wrote = False

        def read(self, path):
            if self.wrote:
                raise AssertionError("read after write")
            return super().read(path)

        def create(self, path, value):
            self.wrote = True
            super().create(path, value)

    class StrictStore(MemoryDocumentStore):
        def atomic(self, operation):
            working = dict(self.documents)
            result = operation(Tx(working))
            self.documents = working
            return result
    repo = PersonalRepository("owner-1", StrictStore())
    assert repo.import_documents(OWNER, {"a/x": {"v": 1}, "a/y": {"v": 2}}, dry_run=False) == (2, 0, 0)


# Finding 7: malformed AI responses and old months do not leave blocking reservations.
def test_stale_reservations_do_not_block_concurrency(tmp_path):
    ledger = SpendLedger(tmp_path / "s.sqlite")
    old = datetime(2026, 9, 1, tzinfo=timezone.utc)
    ledger.reserve("j", Decimal("0.1"), monthly=Decimal(10), per_request=Decimal(1), per_job=Decimal(10), now=old, max_concurrency=1)
    ledger.reserve("j2", Decimal("0.1"), monthly=Decimal(10), per_request=Decimal(1), per_job=Decimal(10), now=NOW, max_concurrency=1)


def test_malformed_ai_response_is_reconciled_as_uncertain(tmp_path):
    from investment_agent.ai.catalog import parse_catalog
    from investment_agent.ai.openrouter import AIUnavailable, AiPolicy, OpenRouterGateway
    from investment_agent.settings import Settings
    data = json.loads(Path("config/ai-policy.example.json").read_text(encoding="utf-8"))
    data["status"] = "approved"
    data["budget"]["monthly_usd"] = "10"
    catalog = parse_catalog({"data": [{"id": "example/model-a", "pricing": {"prompt": "0.000001", "completion": "0.000001"},
                                       "supported_parameters": ["response_format", "tools"]}]}, fetched_at=NOW)
    ledger = SpendLedger(tmp_path / "s.sqlite")
    gw = OpenRouterGateway(Settings(openrouter_api_key="sk-or-v1-" + "a" * 40), AiPolicy.model_validate(data), catalog, ledger,
                           client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"unexpected": True}))),
                           clock=lambda: NOW, sleep=lambda s: None)
    with pytest.raises(AIUnavailable):
        gw.complete("brief", [{"role": "user", "content": "x"}], job_id="j")
    assert ledger.summary(NOW).reserved_usd == 0 and ledger.summary(NOW).uncertain_usd > 0


# Finding 8: buying power uses the Hanoi calendar date.
def test_overview_uses_hanoi_date_for_availability(monkeypatch):
    from investment_agent.services import overview
    early = Clock(int(datetime(2027, 1, 14, 23, tzinfo=timezone.utc).timestamp()))  # 06:00 Hanoi, 2027-01-15
    client = make_client(early, PersonalRepository("owner-1", MemoryDocumentStore()), market=SyntheticMarket())
    seen = {}
    real = overview.availability

    def spy(events, *, as_of, **kw):
        seen["as_of"] = as_of
        return real(events, as_of=as_of, **kw)
    monkeypatch.setattr(overview, "availability", spy)
    call(client, early, "PUT", "/internal/profile", {"profile": PROFILE, "ledger_value": None, "reviewed_net": "100", "expected_version": 0, "request_id": "p"})
    call(client, early, "PUT", "/internal/risk", {"answers": ANSWERS, "confirmed_conflicts": [], "expected_version": 0, "request_id": "r"})
    call(client, early, "POST", "/internal/ledger/events", {"event": {**DEP, "effective_at": "2027-01-15"}, "expected_version": 0, "request_id": "l"})
    call(client, early, "GET", "/internal/overview")
    assert seen["as_of"] == date(2027, 1, 15)
