"""Thuyết minh TSCĐ nhập tay: the construction projects and depreciation ranges of a company as the owner reads them in its notes, which
VNDirect's statements do not carry. A project's expected quarter of completion changes only by a postponement, which is kept with its day
and reason; it closes when the owner confirms it done. Due once the report of that quarter is stored: the company's construction in
progress and cost of tangible assets are shown beside it, for the owner to judge (the statements do not split them by project). Not advice."""

import re
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

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


# Chi phí trả trước: phân bổ trong năm (25/11/2026). The notes give each year's allocation by kind; VNDirect does not. The years left are
# the year-end long-term prepaid expenses over that year's allocation, at that pace, from the owner's figure and the stored balance.
PREPAID_KINDS = {"tools": "Công cụ dụng cụ", "overhaul": "Sửa chữa lớn", "land": "Tiền thuê đất, đền bù", "preop": "Chi phí trước hoạt động",
                 "other": "Khác"}
MAX_PREPAID_YEARS = 15


def validate_prepaid(raw: dict) -> dict[str, dict[str, str]]:
    """year → {kind: tỷ đồng, and "total" when the notes give it}."""
    if len(raw) > MAX_PREPAID_YEARS:
        raise NoteError("too_many", f"Tối đa {MAX_PREPAID_YEARS} năm.")
    out = {}
    for year, items in raw.items():
        if not _YEAR.fullmatch(str(year)):
            raise NoteError("invalid_year", "Năm dạng 2021.")
        kept = {}
        for kind, value in (items or {}).items():
            if kind != "total" and kind not in PREPAID_KINDS:
                raise NoteError("invalid_kind", "Loại chi phí trả trước không có trong danh sách.")
            if (amount := _money(value)) is not None:
                kept[kind] = amount
        if not kept:
            raise NoteError("empty_year", f"Năm {year}: nhập ít nhất một số.")
        out[str(year)] = {k: kept[k] for k in [*PREPAID_KINDS, "total"] if k in kept}
    return dict(sorted(out.items()))


def prepaid_view(prepaid: dict[str, dict[str, str]], statements: dict) -> list[dict]:
    """Each year with its total (as written, or the kinds added up), the stored long-term prepaid expenses at that year's end, the years
    left at that pace and the allocation against that year's profit before tax (none when a figure is missing or not positive)."""
    out = []
    for year, items in prepaid.items():
        kinds = {k: v for k, v in items.items() if k != "total"}
        summed = "total" not in items
        total = Decimal(items["total"]) if not summed else sum((Decimal(v) for v in kinds.values()), Decimal(0))
        row = (statements.get("years") or {}).get(year) or {}
        lt, pbt = row.get("prepaid_lt"), row.get("pbt")
        per_year = total * 10**9
        out.append({"year": year, "items": kinds, "total": format(total.normalize(), "f"), "summed": summed, "prepaid_lt": lt,
                    "years_left": str((Decimal(lt) / per_year).quantize(Decimal("0.1"), ROUND_HALF_UP)) if lt is not None and per_year > 0 else None,
                    "to_pbt": str((per_year / Decimal(pbt)).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if pbt is not None and Decimal(pbt) > 0 else None})
    return out


# Thương vụ mua bán, sáp nhập (25/11/2026), from the notes on business combinations, which VNDirect does not carry. Goodwill by the
# lesson's formula: price − share × fair value of the net assets bought; positive, an asset amortised straight-line over the years the
# owner writes (VAS: at most 10); negative, a bargain purchase booked as a one-off gain in the year of the deal.
MAX_DEALS, MAX_YEARS = 20, 10
_DMY = re.compile(r"^(\d{1,2})/(\d{1,2})/(20\d{2})$")


def _signed(raw, *, required: bool = True) -> str:
    text = str(raw or "").strip()
    negative = text.startswith(("-", "−"))
    value = _money(text[1:] if negative else text)
    if value is None:
        if required:
            raise NoteError("invalid_amount", "Nhập số tỷ đồng.")
        return None
    return format((-Decimal(value) if negative else Decimal(value)).normalize(), "f")


def _day(raw) -> str:
    text = str(raw or "").strip()
    m = _DMY.fullmatch(text)
    try:
        return (date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else date.fromisoformat(text)).isoformat()
    except (TypeError, ValueError):
        raise NoteError("invalid_date", "Ngày mua dạng 15/03/2024.") from None


def validate_deals(raw: list) -> list[dict]:
    if len(raw) > MAX_DEALS:
        raise NoteError("too_many", f"Tối đa {MAX_DEALS} thương vụ mỗi mã.")
    out = []
    for d in raw:
        name = str(d.get("name") or "").strip()
        if not name or len(name) > 120:
            raise NoteError("invalid_name", "Tên công ty được mua từ 1 đến 120 ký tự.")
        day = _day(d.get("date"))
        try:
            share = Decimal(str(d.get("share") or "").strip().replace(",", "."))
        except InvalidOperation:
            share = Decimal(-1)
        if not share.is_finite() or not 0 < share <= 100:
            raise NoteError("invalid_share", "Tỷ lệ mua từ trên 0 đến 100%.")
        years_raw = str(d.get("years") or "").strip()
        try:
            years = int(years_raw) if years_raw else None
        except ValueError:
            years = 0
        if years is not None and not 1 <= years <= MAX_YEARS:
            raise NoteError("invalid_years", f"Số năm phân bổ từ 1 đến {MAX_YEARS} (VAS).")
        url = str(d.get("source_url") or "").strip()
        if url and not re.fullmatch(r"https?://\S{3,500}", url):
            raise NoteError("invalid_source", "Link nguồn phải bắt đầu bằng http:// hoặc https://.")
        out.append({"id": str(d.get("id") or uuid.uuid4().hex[:12])[:32], "name": name, "date": day, "share": format(share.normalize(), "f"),
                    "price": _signed(d.get("price")), "net_assets": _signed(d.get("net_assets")), "years": years, "source_url": url or None,
                    "note": str(d.get("note") or "").strip()[:500]})
    return sorted(out, key=lambda d: d["date"])


def deals_view(deals: list[dict], *, today: date) -> list[dict]:
    """Each deal with its goodwill (tỷ), kind (goodwill or bargain), yearly charge and end of the schedule when the years are written,
    whether it still charges profit today, and for a bargain the year of its one-off gain."""
    out = []
    for d in deals:
        goodwill = Decimal(d["price"]) - Decimal(d["share"]) / 100 * Decimal(d["net_assets"])
        bought = date.fromisoformat(d["date"])
        row = {**d, "goodwill": format(goodwill.normalize(), "f") if goodwill else "0", "kind": "goodwill" if goodwill > 0 else "bargain" if goodwill < 0 else "none",
               "per_year": None, "ends": None, "charging": False, "gain_year": str(bought.year) if goodwill < 0 else None}
        if goodwill > 0 and d["years"]:
            ends = bought.replace(year=bought.year + d["years"]) if not (bought.month == 2 and bought.day == 29) else date(bought.year + d["years"], 2, 28)
            row |= {"per_year": format((goodwill / d["years"]).quantize(Decimal("0.1"), ROUND_HALF_UP).normalize(), "f"), "ends": ends.isoformat(),
                    "charging": bought <= today < ends}
        out.append(row)
    return out
