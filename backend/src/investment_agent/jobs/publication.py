"""Report records (collection "reports") and their index. A report is written once per report_id."""

from investment_agent.api.routes.common import read_version
from investment_agent.repositories.personal import VersionConflict

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


def list_reports(repo, owner) -> list[dict]:
    head = read_version(repo, owner, "reports", INDEX, None)
    rows = []
    for report_id in (head.payload["ids"] if head else []):
        record = read_version(repo, owner, "reports", report_id, None)
        if record:
            p = record.payload
            rows.append({k: p[k] for k in ("report_id", "report_kind", "session_date", "generated_at", "status", "provenance")})
    return rows


def get_report(repo, owner, report_id: str) -> dict | None:
    record = read_version(repo, owner, "reports", report_id, None)
    return record.payload if record else None
