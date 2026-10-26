"""VN-Index and VN30 change for the brief, from the stored daily closes (points)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

IDS = ("VNINDEX", "VN30")
_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")


def index_rows(series_by_id: dict[str, list], *, session_date: date) -> dict:
    rows = []
    for index_id in IDS:
        points = sorted((t, v) for t, v in series_by_id.get(index_id, []) if t.date() <= session_date)
        if len(points) < 2 or points[-1][0].date() != session_date:
            rows.append({"id": index_id, "status": "missing", "reason": "Chưa có giá chỉ số phiên này"})
            continue
        close, prev = Decimal(str(points[-1][1])), Decimal(str(points[-2][1]))
        change = close - prev
        rows.append({"id": index_id, "status": "ok", "close": str(close.quantize(_Q2, ROUND_HALF_UP)),
                     "change": str(change.quantize(_Q2, ROUND_HALF_UP)), "pct": str((change / prev).quantize(_Q4, ROUND_HALF_UP))})
    return {"status": "ok" if any(r["status"] == "ok" for r in rows) else "missing", "rows": rows}
