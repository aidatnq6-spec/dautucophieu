"""Việc cuối năm (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md).

A fixed list for the year ending, open from 1 December to 31 January. The checks the app can make from stored data tick themselves
(done True/False, or None with the reason when the data cannot be read); the others are ticked by the owner. Reminders go once on or
after 1/12, 20/12 and 5/1 while something is left. Personal data; never sent to a model."""

from datetime import date, timedelta

# id, label, checked by the app
ITEMS = (
    ("theses", "Rà luận điểm các mã đang giữ", True),
    ("tower", "Cân lại Tháp tài sản", True),
    ("calendar", "Lịch giao dịch HOSE năm sau đã có", True),
    ("drill", "Diễn tập khôi phục trong 30 ngày qua", True),
    ("goals", "Đặt mục tiêu năm sau", True),
    ("dividends", "Đối chiếu cổ tức và thuế khấu trừ cả năm với chứng từ công ty chứng khoán", False),
    ("cashflow", "Nhập Thu chi tháng 12", False),
)
MANUAL = frozenset(k for k, _, auto in ITEMS if not auto)
REVIEW_DAYS = 90
LAYER_NAME = {"deposit": "Tiền gửi", "bond": "Trái phiếu", "gold": "Vàng", "stocks": "Cổ phiếu", "crypto": "Tiền số"}
WORD = {"short": "thiếu", "over": "vượt"}


def checklist_year(today: date) -> int | None:
    """The year whose list is open: December of that year and the January after."""
    if today.month == 12:
        return today.year
    if today.month == 1:
        return today.year - 1
    return None


def _touched(thesis: dict) -> date:
    days = [thesis["created_on"], *(h["on"] for h in thesis.get("history", []) if h.get("type") == "edit" and h.get("on"))]
    return date.fromisoformat(max(days))


def theses_fact(theses: list[dict], *, held: set[str], today: date) -> tuple[bool, str]:
    """Done when every held ticker has an open thesis written or edited in the last 90 days."""
    if not held:
        return True, "không giữ mã nào"
    open_ = {t["symbol"]: t for t in theses if not t.get("closed_on")}
    old = sorted(s for s in held if s in open_ and today - _touched(open_[s]) > timedelta(days=REVIEW_DAYS))
    none = sorted(s for s in held if s not in open_)
    parts = ([f"chưa rà trong {REVIEW_DAYS} ngày: {', '.join(old)}"] if old else []) + ([f"chưa có luận điểm đang mở: {', '.join(none)}"] if none else [])
    return (False, "; ".join(parts)) if parts else (True, f"mọi mã đang giữ đã rà trong {REVIEW_DAYS} ngày")


def tower_fact(pyramid: dict | None) -> tuple[bool | None, str]:
    if not pyramid:
        return None, "chưa có Tháp tài sản"
    off = [f"{LAYER_NAME.get(layer['id'], layer['id'])} {WORD[layer['status']]}" for layer in pyramid["layers"] if layer["status"] in WORD]
    return (False, "; ".join(off)) if off else (True, "mọi tầng trong khoảng")


def year_end_view(year: int, *, facts: dict[str, tuple[bool | None, str]], ticks: set[str]) -> dict:
    """facts: id → (done, detail) for the app's checks; ticks: the owner's ticked items. An unknown check counts as left."""
    items = []
    for key, label, auto in ITEMS:
        if auto:
            done, detail = facts.get(key, (None, "chưa kiểm được"))
            items.append({"id": key, "label": label, "auto": True, "done": done, "detail": detail})
        else:
            items.append({"id": key, "label": label, "auto": False, "done": key in ticks, "detail": None})
    return {"year": year, "items": items, "left": sum(1 for i in items if i["done"] is not True)}


def _days(year: int) -> list[date]:
    return [date(year, 12, 1), date(year, 12, 20), date(year + 1, 1, 5)]


def reminder_due(today: date, *, reminded: list[str]) -> str | None:
    """The latest reminder day on or before today, while the list is open and that day has not been reminded."""
    year = checklist_year(today)
    if year is None:
        return None
    due = [d for d in _days(year) if d <= today]
    if not due or due[-1].isoformat() in reminded:
        return None
    return due[-1].isoformat()


def render_reminder(view: dict) -> str | None:
    left = [i for i in view["items"] if i["done"] is not True]
    if not left:
        return None
    lines = [f"Việc cuối năm {view['year']}: còn {len(left)} việc"]
    lines += [f"- {i['label']}" + (f" ({i['detail']})" if i["auto"] and i["detail"] else "") for i in left]
    lines.append("Xem và đánh dấu ở trang Năm tài chính.")
    return "\n".join(lines)
