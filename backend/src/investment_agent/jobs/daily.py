"""After-close report pipeline: snapshot → compose → narrate → publish → notify.

Run key = (owner, session date, report kind, input snapshot, report version);
the same key never yields a second report. The report is written in one
transaction that also checks the input record versions it was built from, so
a profile or ledger change during the run blocks publication instead of
publishing stale numbers. Notification is queued only after the report is
persisted and only for complete reports. The narrative falls back to checked
numbers without AI when the narrator fails.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

from investment_agent.services.records import read_version
from investment_agent.domain.pinned import content_digest
from investment_agent.repositories.personal import VersionConflict
from investment_agent.services.overview import compose_overview

from .publication import INDEX, append_index
from .runner import JobStore

LEASE_SECONDS = 900


@dataclass(frozen=True)
class JobResult:
    job_id: str
    report_id: str
    status: str
    reason: str | None = None


def _no_ai_text(content: dict) -> str:
    lines = [f"Kết luận: {content['decision']['headline']}."]
    for h in content["holdings"]:
        value = h["market_value"] or "chưa có giá"
        lines.append(f"- {h['security_id']}: {h['quantity']} cp, giá trị {value}, giá ngày {h['price_date'] or 'chưa có'}")
    for i in content["items"]:
        lines.append(f"- {i['entity_id']}: {i['action']} ({', '.join(i['reasons'])})")
    return "\n".join(lines)


def _previous(repo, owner, kind: str) -> str | None:
    head = read_version(repo, owner, "reports", INDEX, None)
    for report_id in reversed(head.payload["ids"] if head else []):
        record = read_version(repo, owner, "reports", report_id, None)
        if record and record.payload["report_kind"] == kind:
            return report_id
    return None


def run_after_close(*, repo, owner, market, jobs: JobStore, outbox, session_date: date, now: datetime, worker_id: str,
                    narrate: Callable[[dict], str] | None = None, before_publish: Callable[[], None] | None = None,
                    report_kind: str = "after_close", report_version: str = "1") -> JobResult:
    content = compose_overview(repo, owner, market, now)
    versions = content["input_versions"]
    market_inputs = {h["security_id"]: [h["price"], h["price_date"]] for h in content["holdings"]}
    snapshot = content_digest([versions, market.provenance, market_inputs, session_date.isoformat()])
    run_key = content_digest([owner.uid, session_date.isoformat(), report_kind, snapshot, report_version])
    report_id = run_key[:32]

    existing = read_version(repo, owner, "reports", report_id, None)
    if existing is not None:
        # Finish what a crashed run may have left undone; both steps are idempotent.
        append_index(repo, owner, report_id)
        if existing.payload["status"] == "published":
            outbox.enqueue(report_id)
        known = jobs.by_key(run_key)
        return JobResult(job_id=known["job_id"] if known else "", report_id=report_id, status=existing.payload["status"])
    job_id = jobs.acquire(run_key, worker_id=worker_id, now=now.timestamp(), ttl=LEASE_SECONDS)
    try:
        return _run(repo, owner, market, jobs, outbox, job_id, content, versions, snapshot, report_id, session_date, now, narrate,
                    before_publish, report_kind, report_version)
    except BaseException:
        jobs.finish(job_id, "failed", report_id=report_id, reason="error")
        raise


def _run(repo, owner, market, jobs, outbox, job_id, content, versions, snapshot, report_id, session_date, now, narrate, before_publish,
         report_kind, report_version) -> JobResult:
    jobs.stage(job_id, "snapshot")

    setup = content["setup"]
    flags = list(content["quality_notes"])
    if setup["universe_status"] != "complete":
        flags.append("universe_incomplete")
    if market.provenance != "licensed":
        flags.append(f"market_provenance:{market.provenance}")
    # The latest stored price may predate the session (vendor not yet updated); that is not this session's report.
    behind = [h["security_id"] for h in content["holdings"] if h["price_date"] and h["price_date"] < session_date.isoformat()]
    flags += [f"price_not_for_session:{s}" for s in behind]
    complete = setup["profile"] and setup["risk"] and market.provenance != "none" and not content["quality_notes"] and not behind
    status = "published" if complete else "incomplete"
    jobs.stage(job_id, "compose")

    narrative = {"source": "no_ai", "text": _no_ai_text(content)}
    if narrate is None:
        flags.append("ai_not_configured")
    else:
        try:
            narrative = {"source": "ai", "text": narrate(content)}
        except Exception:  # model, budget or validation failure: never block the numbers
            flags.append("ai_unavailable")
    jobs.stage(job_id, "narrate")

    ledger = content["ledger"]
    report = {
        "schema_version": "1", "report_id": report_id, "report_kind": report_kind, "report_version": report_version,
        "session_date": session_date.isoformat(), "generated_at": now.isoformat(), "status": status, "provenance": market.provenance,
        "input_versions": versions, "input_snapshot": snapshot, "decision": content["decision"], "holdings": content["holdings"],
        "items": content["items"], "ledger_summary": {k: ledger[k] for k in ("cash", "realized_gain", "dividend_income", "dividend_receivable", "net_contributions")},
        "narrative": narrative, "verification_flags": flags, "previous_report_id": _previous(repo, owner, report_kind),
        "sources": sorted({s for i in content["items"] for s in i["source_ids"]}),
    }
    if before_publish:
        before_publish()
    try:
        repo.write(owner, "reports", report_id, report, expected_version=0, request_id=f"report-{report_id}",
                   inputs={tuple(k.split("/")): v for k, v in versions.items() if v >= 1})
    except VersionConflict:
        if read_version(repo, owner, "reports", report_id, None) is None:
            jobs.finish(job_id, "failed", report_id=report_id, reason="inputs_changed")
            return JobResult(job_id=job_id, report_id=report_id, status="failed", reason="inputs_changed")
    append_index(repo, owner, report_id)
    jobs.stage(job_id, "publish")
    if status == "published":
        outbox.enqueue(report_id)
        jobs.stage(job_id, "notify")
    jobs.finish(job_id, status, report_id=report_id)
    return JobResult(job_id=job_id, report_id=report_id, status=status)
