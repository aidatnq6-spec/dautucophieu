"""Dự án và điểm rơi lợi nhuận: the main projects of a property developer as the owner reads them in the company's public documents
(total expected revenue, what has been booked so far, and how much the owner expects to be booked in each year), in tỷ đồng.

The timeline adds up the owner's own yearly figures; nothing is spread over years by the application. What a project has left
(total − booked) is set against what the owner placed in years, so an unplaced remainder shows. Not advice."""

import re
import uuid
from decimal import Decimal, InvalidOperation

MAX_PROJECTS = 30
_YEAR = re.compile(r"^20[0-9]{2}$")


class ProjectError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _amount(raw, *, required: bool = False) -> str | None:
    if raw is None or str(raw).strip() == "":
        if required:
            raise ProjectError("invalid_amount", "Nhập số tỷ đồng.")
        return None
    text = str(raw).strip().replace(" ", "")
    text = text.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", text) else text  # 7.500 = bảy nghìn năm trăm
    try:
        value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        raise ProjectError("invalid_amount", "Số tỷ đồng không hợp lệ.") from None
    if not value.is_finite() or value < 0 or value > Decimal(10) ** 7:
        raise ProjectError("invalid_amount", "Số tỷ đồng phải từ 0 trở lên.")
    return format(value.normalize(), "f")


def validate_projects(raw: list) -> list[dict]:
    if len(raw) > MAX_PROJECTS:
        raise ProjectError("too_many", f"Tối đa {MAX_PROJECTS} dự án mỗi mã.")
    out = []
    for p in raw:
        name = str(p.get("name") or "").strip()
        if not name or len(name) > 120:
            raise ProjectError("invalid_name", "Tên dự án từ 1 đến 120 ký tự.")
        by_year = {}
        for year, amount in (p.get("by_year") or {}).items():
            if not _YEAR.fullmatch(str(year)):
                raise ProjectError("invalid_year", "Năm ghi nhận dạng 2027.")
            by_year[str(year)] = _amount(amount, required=True)
        url = str(p.get("source_url") or "").strip()
        if url and not re.fullmatch(r"https?://\S{3,500}", url):
            raise ProjectError("invalid_source", "Link nguồn phải bắt đầu bằng http:// hoặc https://.")
        note = str(p.get("note") or "").strip()[:500]
        out.append({"id": str(p.get("id") or uuid.uuid4().hex[:12])[:32], "name": name, "total": _amount(p.get("total")), "booked": _amount(p.get("booked")),
                    "by_year": dict(sorted(by_year.items())), "source_url": url or None, "note": note})
    return out


def timeline(projects: list[dict]) -> dict:
    years: dict[str, tuple[Decimal, int]] = {}
    shown = []
    for p in projects:
        planned = sum((Decimal(v) for v in p["by_year"].values()), Decimal(0))
        for y, v in p["by_year"].items():
            total, count = years.get(y, (Decimal(0), 0))
            years[y] = (total + Decimal(v), count + 1)
        remaining = Decimal(p["total"]) - Decimal(p["booked"] or 0) if p["total"] is not None else None
        shown.append({**p, "planned": format(planned.normalize(), "f"), "remaining": format(remaining.normalize(), "f") if remaining is not None else None,
                      "unplaced": format((remaining - planned).normalize(), "f") if remaining is not None else None})
    return {"years": [{"year": y, "amount": format(v.normalize(), "f"), "projects": n} for y, (v, n) in sorted(years.items())], "projects": shown}
