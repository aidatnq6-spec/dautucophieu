"""Lịch và nhật ký vĩ mô: the owner's dated events in the personal store (settings/macro_events), and the after-close reminder the
day before those marked for it — sent once; an event moved to another day may be reminded again."""

from datetime import date

from investment_agent.domain.macro_extras import EventError, KINDS, due_tomorrow, validate_events
from investment_agent.services.records import read_version

RECORD = ("settings", "macro_events")


def read_events(repo, owner) -> tuple[list[dict], int]:
    record = read_version(repo, owner, *RECORD, None)
    return (list(record.payload.get("events", [])), record.version) if record else ([], 0)


def merge_events(stored: list[dict], sent: list[dict]) -> list[dict]:
    if len({e.get("id") for e in sent}) != len(sent):
        raise EventError("duplicate", "Hai sự kiện trùng mã số.")
    before = {e["id"]: e for e in stored}
    out = []
    for e in validate_events(sent):
        old = before.get(e["id"])
        reminded = old.get("reminded_on") if old and old["date"] == e["date"] else None
        out.append({**e, "reminded_on": reminded})
    return out


def render(events: list[dict]) -> str:
    lines = ["📅 Lịch vĩ mô ngày mai"]
    for e in events:
        d = date.fromisoformat(e["date"]).strftime("%d/%m/%Y")
        lines.append(f"• {d} [{KINDS[e['kind']]}] {e['title']}" + (f" — nguồn: {e['source']}" if e["source"] else ""))
    return "\n".join(lines)


def remind(repo, owner, *, send, today: date, request_id: str) -> dict:
    events, version = read_events(repo, owner)
    due = [e for e in due_tomorrow(events, today=today) if not e.get("reminded_on")]
    if not due:
        return {"status": "ok", "due": 0, "sent": False}
    if not send(render(due)):
        return {"status": "ok", "due": len(due), "sent": False}
    ids = {e["id"] for e in due}
    updated = [{**e, "reminded_on": today.isoformat()} if e["id"] in ids else e for e in events]
    repo.write(owner, *RECORD, {"events": updated}, expected_version=version, request_id=request_id)
    return {"status": "ok", "due": len(due), "sent": True}
