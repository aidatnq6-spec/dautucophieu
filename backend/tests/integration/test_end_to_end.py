"""Deterministic end-to-end flow over the real API, job pipeline and delivery with synthetic data and fakes."""

import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from signed_client import Clock, call, make_client  # noqa: E402

from investment_agent.ai.openrouter import AIUnavailable  # noqa: E402
from investment_agent.api.auth import OwnerContext  # noqa: E402
from investment_agent.jobs.daily import run_after_close  # noqa: E402
from investment_agent.jobs.runner import JobStore  # noqa: E402
from investment_agent.market.view import EvidenceRef, PricePoint, SyntheticMarket  # noqa: E402
from investment_agent.notifications.outbox import DeliveryStore, NotificationSettings, deliver  # noqa: E402
from investment_agent.notifications.telegram import TelegramSender  # noqa: E402
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository  # noqa: E402

OWNER = OwnerContext("owner-1", "owner", "e2e")
SESSION = date(2027, 1, 14)
NOW = datetime(2027, 1, 15, 8, tzinfo=timezone.utc)  # matches signed_client.NOW
MARKET = SyntheticMarket(prices={"FPT": PricePoint(Decimal(60_000), SESSION)},
                         documents={"FPT": [EvidenceRef("doc-fpt", "BCTC (tổng hợp)", "financial_statement", "https://example.invalid/fpt", "2027-01-10")]},
                         industries={"FPT": "tech"})
PROFILE = {"as_of": "2027-01-15", "emergency_reserve": "100000000",
           "assets": [{"asset_id": "cash", "kind": "deposit", "amount": "1100000000", "liquidity": "liquid",
                       "earmarks": [{"purpose": "emergency", "amount": "100000000"}]}]}
SCENARIO = {"cash_flows": ["90000", "90000"], "discount_rate": "0.10", "terminal_growth": "0"}
ASSUMPTIONS = {"entity_id": "FPT", "model": "fcfe_dcf", "valuation_date": "2027-01-14", "required_margin": "0.2", "tranche_fraction": "0.25",
               "scenarios": {"down": {**SCENARIO, "discount_rate": "0.12"}, "base": SCENARIO, "up": {**SCENARIO, "discount_rate": "0.09"}},
               "shares": 1, "sources": ["doc-fpt"]}


class Telegram:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), 0

    def __call__(self, request):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def ok(n):
    return httpx.Response(200, json={"ok": True, "result": {"message_id": n}})


@pytest.fixture
def world(tmp_path):
    store = MemoryDocumentStore()
    repo = PersonalRepository("owner-1", store)
    clock = Clock()
    client = make_client(clock, repo, market=MARKET)
    preview = call(client, clock, "POST", "/internal/profile/assessment", {"profile": PROFILE, "ledger_value": None}).json()
    assert preview["investable_capital"] == "1000000000"
    assert call(client, clock, "PUT", "/internal/profile", {"profile": PROFILE, "ledger_value": None, "reviewed_net": preview["net"],
                                                            "expected_version": 0, "request_id": "p1"}).status_code == 200
    answers = [{"question": n, "answer": "C"} for n in range(1, 14)]
    assert call(client, clock, "PUT", "/internal/risk", {"answers": answers, "confirmed_conflicts": [], "expected_version": 0, "request_id": "r1"}).json()["assessment"]["group"] == "balanced"
    events = [{"event_id": "d1", "type": "deposit", "effective_at": "2027-01-04", "sequence": 0, "amount": "100000000"},
              {"event_id": "b1", "type": "buy", "effective_at": "2027-01-05", "sequence": 0, "security_id": "FPT", "quantity": 100, "price": "50000",
               "fee": "15000", "tax": "0"},
              {"event_id": "e1", "type": "cash_dividend_entitlement", "effective_at": "2027-01-08", "sequence": 0, "action_id": "div-1", "security_id": "FPT",
               "record_date": "2027-01-09", "payment_date": "2027-01-20", "eligible_quantity": 100, "expected_gross": "200000", "expected_tax": "10000"}]
    for i, e in enumerate(events):
        assert call(client, clock, "POST", "/internal/ledger/events", {"event": e, "expected_version": i, "request_id": f"l{i}"}).status_code == 200
    call(client, clock, "PUT", "/internal/valuation/FPT/draft", {"assumptions": ASSUMPTIONS, "expected_version": 0, "request_id": "v1"})
    call(client, clock, "POST", "/internal/valuation/FPT/approve", {"draft_version": 1, "request_id": "v2"})
    call(client, clock, "PUT", "/internal/settings/trading", {"settings": {"fee_rate": "0.0015"}, "expected_version": 0, "request_id": "t1"})
    return {"repo": repo, "store": store, "client": client, "clock": clock, "jobs": JobStore(tmp_path / "jobs.sqlite"),
            "deliveries": DeliveryStore(tmp_path / "deliveries.sqlite")}


def job(world, **kw):
    return run_after_close(repo=world["repo"], owner=OWNER, market=kw.pop("market", MARKET), jobs=world["jobs"], outbox=world["deliveries"],
                           session_date=SESSION, now=NOW, worker_id="e2e", **kw)


SETTINGS = NotificationSettings(enabled=True, chat_id="-100123", members_may_view_personal_data=True, scheduled_enabled=True)


def sender(transport):
    return TelegramSender("1:" + "T" * 35, client=httpx.Client(transport=httpx.MockTransport(transport)), sleep=lambda s: None)


def test_full_flow_publishes_once_and_delivers_once(world):
    overview = call(world["client"], world["clock"], "GET", "/internal/overview").json()
    fpt = overview["holdings"][0]
    assert (fpt["market_value"], fpt["total_cost"], fpt["unrealized_gain"]) == ("6000000", "5015000", "985000")
    assert overview["ledger"]["dividend_receivable"] == "190000" and overview["ledger"]["dividend_income"] == "190000"
    first = job(world)
    assert first.status == "published" and world["deliveries"].queued() == [first.report_id]
    assert job(world).report_id == first.report_id and world["deliveries"].queued() == [first.report_id]  # same snapshot: no duplicate
    report = world["repo"].read(OWNER, "reports", first.report_id).payload
    t = Telegram(ok(1), ok(2), ok(3))
    assert deliver(report, SETTINGS, sender(t), world["deliveries"]).status == "sent"
    sent = t.calls
    assert deliver(report, SETTINGS, sender(t), world["deliveries"]).status == "sent" and t.calls == sent  # never resent


def test_firebase_offline_blocks_mutations_and_publication(world):
    world["store"].available = False
    assert call(world["client"], world["clock"], "GET", "/internal/overview").status_code == 503
    with pytest.raises(Exception):
        job(world)
    world["store"].available = True
    assert world["deliveries"].queued() == []


def test_missing_price_gives_incomplete_unsent_report(world):
    result = job(world, market=SyntheticMarket())
    assert result.status == "incomplete" and world["deliveries"].queued() == []


@pytest.mark.parametrize("failure", [AIUnavailable("budget_exceeded"), AIUnavailable("no_compliant_route"), ValueError("schema")])
def test_ai_credit_privacy_or_schema_failure_falls_back_without_ai(world, failure):
    def narrate(content):
        raise failure
    result = job(world, narrate=narrate)
    report = world["repo"].read(OWNER, "reports", result.report_id).payload
    assert result.status == "published" and report["narrative"]["source"] == "no_ai" and "ai_unavailable" in report["verification_flags"]


def test_profile_change_mid_job_is_not_published_with_wrong_version(world):
    def change():
        head = world["repo"].read(OWNER, "profile_versions", "main")
        world["repo"].write(OWNER, "profile_versions", "main", head.payload, expected_version=head.version, request_id="race")
    result = job(world, before_publish=change)
    assert result.status == "failed" and result.reason == "inputs_changed" and world["deliveries"].queued() == []


def test_telegram_timeout_is_unknown_and_not_resent(world):
    result = job(world)
    report = world["repo"].read(OWNER, "reports", result.report_id).payload
    t = Telegram(httpx.ReadTimeout("slow"))
    assert deliver(report, SETTINGS, sender(t), world["deliveries"]).status == "unknown"
    assert deliver(report, SETTINGS, sender(Telegram()), world["deliveries"]).status == "unknown"


def test_backdated_correction_changes_report_inputs(world):
    first = job(world)
    ledger = call(world["client"], world["clock"], "GET", "/internal/ledger").json()
    fix = {"amendment_id": "a1", "action": "replace", "target_event_id": "b1", "reason": "Sửa phí theo sao kê",
           "replacement": {**ledger["events"][1], "fee": "20000"}}
    assert call(world["client"], world["clock"], "POST", "/internal/ledger/amendments",
                {"amendment": fix, "expected_version": ledger["version"], "request_id": "a1"}).status_code == 200
    second = job(world)
    assert second.report_id != first.report_id
    report = world["repo"].read(OWNER, "reports", second.report_id).payload
    assert report["holdings"][0]["total_cost"] == "5020000"
