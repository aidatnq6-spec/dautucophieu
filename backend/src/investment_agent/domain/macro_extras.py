"""Two additions to Vĩ mô (11/2026, after the talk on the State Bank's 2 bn USD swap):

- V1 Chênh lệch lãi suất VND–USD: the State Bank's average overnight interbank rate less the USD overnight rate known that day
  (SOFR, else the Fed's EFFR; a USD figure older than 7 days is not used). Below zero, holding VND pays less than USD, which tends to
  weigh on the exchange rate (interest rate parity).
- V5 Lịch và nhật ký vĩ mô: dated policy events and releases the owner records with their source (a Fed meeting, a State Bank
  operation, a data release), coming ones counted down; a reminder the day before for those marked so. Nothing is filled in.
"""

import re
from datetime import date, timedelta
from decimal import Decimal

USD_MAX_AGE = timedelta(days=7)
KINDS = {"fed": "Fed", "sbv": "NHNN", "data": "Số liệu", "fiscal": "Tài khóa", "other": "Khác"}
MAX_EVENTS = 120
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _s(v: Decimal) -> str:
    q = v.quantize(Decimal("0.01"))
    return format(q.normalize(), "f") if q != 0 else "0"


def _usd_on(series: list[tuple[date, str]], day: date) -> Decimal | None:
    known = [(d, v) for d, v in series if d <= day and day - d <= USD_MAX_AGE]
    return Decimal(max(known)[1]) if known else None


def rate_spread(vnd: list[tuple[date, str]], *, sofr: list[tuple[date, str]], effr: list[tuple[date, str]]) -> dict:
    points = []
    for day, value in sorted(vnd):
        usd, source = _usd_on(sofr, day), "SOFR"
        if usd is None:
            usd, source = _usd_on(effr, day), "EFFR"
        if usd is None:
            continue
        v = Decimal(value)
        points.append({"date": day.isoformat(), "vnd": _s(v), "usd": _s(usd), "usd_source": source, "spread": _s(v - usd)})
    latest = points[-1] if points else None
    return {"points": points, "latest": latest, "days": len(points), "negative_days": sum(1 for p in points if Decimal(p["spread"]) < 0)}


class EventError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def validate_events(raw: list[dict]) -> list[dict]:
    if len(raw) > MAX_EVENTS:
        raise EventError("too_many", f"Tối đa {MAX_EVENTS} sự kiện.")
    out = []
    for e in raw:
        title = str(e.get("title") or "").strip()[:160]
        try:
            day = date.fromisoformat(str(e.get("date") or ""))
        except ValueError:
            raise EventError("invalid_date", "Ngày theo dạng YYYY-MM-DD.") from None
        if not _ID.fullmatch(str(e.get("id") or "")) or not title or e.get("kind") not in KINDS:
            raise EventError("invalid_event", "Mỗi sự kiện cần ngày, nội dung và loại.")
        out.append({"id": e["id"], "date": day.isoformat(), "title": title, "kind": e["kind"], "note": str(e.get("note") or "").strip()[:300],
                    "source": str(e.get("source") or "").strip()[:160], "remind": bool(e.get("remind"))})
    return sorted(out, key=lambda e: e["date"])


def events_view(events: list[dict], *, today: date) -> dict:
    coming = [{**e, "days": (date.fromisoformat(e["date"]) - today).days} for e in events if e["date"] >= today.isoformat()]
    past = [e for e in events if e["date"] < today.isoformat()][::-1]
    return {"coming": coming, "past": past, "kinds": KINDS}


def due_tomorrow(events: list[dict], *, today: date) -> list[dict]:
    """Events marked for a reminder that fall tomorrow."""
    tomorrow = (today + timedelta(days=1)).isoformat()
    return [e for e in events if e["remind"] and e["date"] == tomorrow]
