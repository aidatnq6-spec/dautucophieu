"""Hình vẽ trên biểu đồ: the owner's horizontal levels and two-point trend lines on the Xu hướng chart, kept in the personal store
(settings/chart_drawings). A level shows on both frames; a trend line belongs to the frame it was drawn on, its points keyed like the
chart's bars (a date for daily bars, Hà Nội wall-clock seconds for hourly ones). Notes only: nothing is sent or drawn by the software.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from investment_agent.services.records import read_version

RECORD = ("settings", "chart_drawings")
MAX_DRAWINGS = 200


class DrawingError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def read_drawings(repo, owner) -> tuple[list[dict], int]:
    record = read_version(repo, owner, *RECORD, None)
    return (list(record.payload.get("drawings", [])), record.version) if record else ([], 0)


def _price(raw) -> str | None:
    """A plain positive decimal of at most 16 characters ("56.3"); the page rounds the cursor's price before sending."""
    text = str(raw).strip()
    try:
        d = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return format(d.normalize(), "f") if len(text) <= 16 and d.is_finite() and d > 0 else None


def _time(raw, interval: str):
    if interval == "1D":
        try:
            return date.fromisoformat(raw).isoformat() if isinstance(raw, str) and len(raw) == 10 else None
        except ValueError:
            return None
    return raw if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0 else None


def _invalid(message: str) -> DrawingError:
    return DrawingError("invalid_drawing", message)


def _new(change: dict, allowed: set[str], now: datetime) -> dict:
    symbol = str(change.get("symbol") or "").upper()
    if symbol not in allowed:
        raise DrawingError("symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    drawing = {"id": uuid.uuid4().hex[:12], "symbol": symbol, "kind": change.get("kind"), "interval": None, "price": None, "points": None,
               "created_at": now.isoformat()}
    if drawing["kind"] == "hline":
        drawing["price"] = _price(change.get("price"))
        if drawing["price"] is None:
            raise _invalid("Đường ngang cần một mức giá dương.")
    elif drawing["kind"] == "trend":
        interval, points = change.get("interval"), change.get("points")
        if interval not in ("1D", "1H") or not isinstance(points, list) or len(points) != 2:
            raise _invalid("Đường xu hướng cần khung 1D hoặc 1H và đúng hai điểm.")
        kept = [{"t": _time(p.get("t"), interval), "p": _price(p.get("p"))} if isinstance(p, dict) else {"t": None, "p": None} for p in points]
        if any(p["t"] is None or p["p"] is None for p in kept) or kept[0]["t"] == kept[1]["t"]:
            raise _invalid("Hai điểm của đường xu hướng cần thời gian của nến (khác nhau) và giá dương.")
        drawing.update(interval=interval, points=kept)
    else:
        raise _invalid("Chỉ có đường ngang hoặc đường xu hướng.")
    return drawing


def change_drawings(repo, owner, change: dict, *, expected_version: int, request_id: str, allowed: set[str],
                    now: datetime) -> tuple[list[dict], int]:
    drawings, _ = read_drawings(repo, owner)
    action = change.get("action")
    if action == "add":
        drawing = _new(change, allowed, now)
        if len(drawings) >= MAX_DRAWINGS:
            raise DrawingError("too_many_drawings", f"Tối đa {MAX_DRAWINGS} hình vẽ; hãy xóa bớt.")
        drawings.append(drawing)
    elif action == "remove":
        if not any(d["id"] == change.get("id") for d in drawings):
            raise DrawingError("drawing_not_found", "Không tìm thấy hình vẽ này; hãy tải lại.")
        drawings = [d for d in drawings if d["id"] != change.get("id")]
    elif action == "clear":
        symbol = str(change.get("symbol") or "").upper()
        drawings = [d for d in drawings if d["symbol"] != symbol]
    else:
        raise _invalid("Thao tác không hợp lệ.")
    record = repo.write(owner, *RECORD, {"drawings": drawings}, expected_version=expected_version, request_id=request_id)
    return drawings, record.version
