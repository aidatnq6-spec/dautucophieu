"""Thuyết minh TSCĐ nhập tay: the construction projects and depreciation ranges of a company as the owner reads them in its notes, which
VNDirect's statements do not carry. A project's expected quarter of completion changes only by a postponement, which is kept with its day
and reason; it closes when the owner confirms it done. Due once the report of that quarter is stored: the company's construction in
progress and cost of tangible assets are shown beside it, for the owner to judge (the statements do not split them by project). Not advice."""

import re
import uuid
from datetime import date

from investment_agent.domain.property_projects import ProjectError, _amount

MAX_PROJECTS = 20
GROUPS = {"buildings": "Nhà cửa, vật kiến trúc", "machinery": "Máy móc, thiết bị", "vehicles": "Phương tiện vận tải, truyền dẫn",
          "office": "Thiết bị, dụng cụ quản lý", "livestock": "Vật nuôi, cây lâu năm", "other": "TSCĐ khác"}
_QUARTER = (re.compile(r"^Q([1-4])/(20\d{2})$"), re.compile(r"^(20\d{2})-Q([1-4])$"))
_YEAR = re.compile(r"^20\d{2}$")


class NoteError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def parse_quarter(raw) -> str:
    """Q3/2027 or 2027-Q3 → 2027-Q3."""
    text = str(raw or "").strip().upper()
    if m := _QUARTER[0].fullmatch(text):
        return f"{m.group(2)}-Q{m.group(1)}"
    if _QUARTER[1].fullmatch(text):
        return text
    raise NoteError("invalid_quarter", "Quý dạng Q3/2027.")


def _period(raw) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if _YEAR.fullmatch(text):
        return text
    try:
        return parse_quarter(text)
    except NoteError:
        raise NoteError("invalid_period", "Kỳ báo cáo dạng 2025 hoặc Q2/2026.") from None


def _money(raw) -> str | None:
    try:
        return _amount(raw)
    except ProjectError as exc:
        raise NoteError(exc.code, exc.message) from None


def _ranges(raw: dict) -> dict:
    groups = {}
    for key, value in raw.items():
        if key == "period":
            continue
        if key not in GROUPS:
            raise NoteError("invalid_group", "Nhóm tài sản không có trong thuyết minh.")
        try:
            low, high = int(str(value.get("from")).strip()), int(str(value.get("to")).strip())
        except (AttributeError, TypeError, ValueError):
            raise NoteError("invalid_range", "Số năm khấu hao là số nguyên.") from None
        if not 0 <= low <= high <= 100:
            raise NoteError("invalid_range", "Số năm khấu hao từ 0 đến 100, \"từ\" không lớn hơn \"đến\".")
        groups[key] = {"from": low, "to": high}
    return {"period": _period(raw.get("period")), "groups": {k: groups[k] for k in GROUPS if k in groups}}


def validate_notes(raw_projects: list, raw_ranges: dict, *, stored: list[dict]) -> tuple[list[dict], dict]:
    """The owner's projects and ranges; a stored project keeps its status, completion day and postponements, and its quarter unless postponed."""
    if len(raw_projects) > MAX_PROJECTS:
        raise NoteError("too_many", f"Tối đa {MAX_PROJECTS} dự án mỗi mã.")
    kept = {p["id"]: p for p in stored}
    out = []
    for p in raw_projects:
        name = str(p.get("name") or "").strip()
        if not name or len(name) > 120:
            raise NoteError("invalid_name", "Tên dự án từ 1 đến 120 ký tự.")
        due = parse_quarter(p.get("due"))
        url = str(p.get("source_url") or "").strip()
        if url and not re.fullmatch(r"https?://\S{3,500}", url):
            raise NoteError("invalid_source", "Link nguồn phải bắt đầu bằng http:// hoặc https://.")
        old = kept.get(str(p.get("id") or ""))
        if old and old["due"] != due:
            raise NoteError("due_locked", "Đổi quý hoàn thành dự kiến bằng nút Lùi hạn.")
        out.append({"id": old["id"] if old else uuid.uuid4().hex[:12], "name": name, "due": due, "read_period": _period(p.get("read_period")),
                    "cip_value": _money(p.get("cip_value")), "budget": _money(p.get("budget")), "source_url": url or None,
                    "note": str(p.get("note") or "").strip()[:500], "status": old["status"] if old else "open",
                    "done_on": old["done_on"] if old else None, "postpones": old["postpones"] if old else []})
    return out, _ranges(raw_ranges or {})


def _find(projects: list[dict], pid: str) -> dict:
    p = next((p for p in projects if p["id"] == pid), None)
    if p is None:
        raise NoteError("not_found", "Không thấy dự án này; hãy tải lại.")
    if p["status"] != "open":
        raise NoteError("not_open", "Dự án đã ghi là hoàn thành.")
    return p


def postpone(projects: list[dict], pid: str, to, reason: str, *, today: date) -> list[dict]:
    p, new = _find(projects, pid), parse_quarter(to)
    if new <= p["due"]:
        raise NoteError("not_later", "Quý mới phải sau quý hoàn thành dự kiến hiện tại.")
    entry = {"from": p["due"], "to": new, "on": today.isoformat(), "reason": str(reason or "").strip()[:200]}
    return [{**x, "due": new, "postpones": [*x["postpones"], entry]} if x["id"] == pid else x for x in projects]


def complete(projects: list[dict], pid: str, *, today: date) -> list[dict]:
    _find(projects, pid)
    return [{**x, "status": "done", "done_on": today.isoformat()} if x["id"] == pid else x for x in projects]


def _quarter_end(q: str) -> date:
    year, n = int(q[:4]), int(q[-1])
    return date(year + 1, 1, 1) if n == 4 else date(year, 3 * n + 1, 1)


def _figures(statements: dict, period: str | None) -> dict | None:
    if not period:
        return None
    row = (statements.get("years" if _YEAR.fullmatch(period) else "quarters") or {}).get(period)
    return None if row is None else {"period": period, "cip": row.get("cip"), "ppe_gross": row.get("ppe_gross")}


def due_view(projects: list[dict], statements: dict, *, today: date) -> list[dict]:
    """Each project with its state (done; due: its quarter's report is stored; waiting_report: the quarter is over, the report not yet;
    upcoming) and the company's figures at the period read, at the due quarter and at the latest stored quarter."""
    quarters = statements.get("quarters") or {}
    latest = max((q for q, row in quarters.items() if "cip" in row), default=None)
    out = []
    for p in projects:
        at_due = _figures(statements, p["due"]) if "cip" in (quarters.get(p["due"]) or {}) else None
        state = "done" if p["status"] == "done" else "due" if at_due else "waiting_report" if today >= _quarter_end(p["due"]) else "upcoming"
        out.append({**p, "state": state, "at_read": _figures(statements, p["read_period"]), "at_due": at_due, "latest": _figures(statements, latest)})
    return out
