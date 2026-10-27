"""Report records (collection "reports") and their index. A report is written once per report_id."""

from investment_agent.services.records import read_version
from investment_agent.repositories.personal import VersionConflict, prefetch

INDEX = "index"


def append_index(repo, owner, report_id: str, *, attempts: int = 5):
    for _ in range(attempts):
        head = read_version(repo, owner, "reports", INDEX, None)
        ids = head.payload["ids"] if head else []
        if report_id in ids:
            return
        try:
            repo.write(owner, "reports", INDEX, {"ids": [*ids, report_id]}, expected_version=head.version if head else 0,
                       request_id=f"index-{report_id}")
            return
        except VersionConflict:
            continue
    raise VersionConflict("Report index busy")


SUMMARY = ("report_id", "report_kind", "session_date", "generated_at", "status", "provenance")


def list_reports(repo, owner) -> list[dict]:
    head = read_version(repo, owner, "reports", INDEX, None)
    ids = head.payload["ids"] if head else []
    prefetch(getattr(repo, "authoritative", repo), owner, [("reports", i) for i in ids])  # all at once, not one round trip each
    rows = []
    for report_id in ids:
        record = read_version(repo, owner, "reports", report_id, None)
        if record:
            rows.append({k: record.payload[k] for k in SUMMARY})
    return rows


def latest_report(repo, owner) -> dict | None:
    """Summary of the newest report (the index is in publication order): two reads, however many reports exist."""
    head = read_version(repo, owner, "reports", INDEX, None)
    for report_id in reversed(head.payload["ids"] if head else []):
        record = read_version(repo, owner, "reports", report_id, None)
        if record:
            return {k: record.payload[k] for k in SUMMARY}
    return None


def get_report(repo, owner, report_id: str) -> dict | None:
    record = read_version(repo, owner, "reports", report_id, None)
    return record.payload if record else None
