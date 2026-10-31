"""Cảnh báo giá: the owner sets a level for a watched ticker or VNINDEX/VN30 (thousand đồng for stocks, points for indices); during
the session a scheduled check reads the board and sends one Telegram note for the levels crossed. Each alert fires once and
stays listed as triggered with the time and price, until the owner arms it again or removes it. Kept in the personal store
(settings/price_alerts); a level is marked triggered only after the message went out. No price, no trigger.
"""

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from investment_agent.services.records import read_version

RECORD = ("settings", "price_alerts")
MAX_ALERTS = 50
OPS = {"above": "≥", "below": "≤"}


class AlertError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def read_alerts(repo, owner) -> tuple[list[dict], int]:
    record = read_version(repo, owner, *RECORD, None)
    return (list(record.payload.get("alerts", [])), record.version) if record else ([], 0)


def _price(raw) -> Decimal | None:
    """A plain decimal ("56.3", "1800"); the page converts what the owner types (56,3 or 1.800) before sending."""
    try:
        d = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() and d > 0 else None


def change_alerts(repo, owner, change: dict, *, expected_version: int, request_id: str, allowed: set[str], now: datetime) -> tuple[list[dict], int]:
    alerts, _ = read_alerts(repo, owner)
    action = change.get("action")
    if action == "add":
        symbol = str(change.get("symbol") or "").upper()
        if symbol not in allowed:
            raise AlertError("symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
        price = _price(change.get("price"))
        if change.get("op") not in OPS or price is None or len(str(change.get("price"))) > 16:
            raise AlertError("invalid_alert", "Cảnh báo cần điều kiện ≥ hoặc ≤ và một mức giá dương, ví dụ 56,3.")
        if len(alerts) >= MAX_ALERTS:
            raise AlertError("too_many_alerts", f"Tối đa {MAX_ALERTS} cảnh báo; hãy xóa bớt.")
        alerts.append({"id": uuid.uuid4().hex[:12], "symbol": symbol, "op": change["op"], "price": format(price.normalize(), "f"),
                       "created_at": now.isoformat(), "triggered_at": None, "triggered_price": None})
    elif action in ("remove", "rearm"):
        found = next((a for a in alerts if a["id"] == change.get("id")), None)
        if found is None:
            raise AlertError("alert_not_found", "Không tìm thấy cảnh báo này; hãy tải lại.")
        if action == "remove":
            alerts = [a for a in alerts if a is not found]
        else:
            found.update(triggered_at=None, triggered_price=None)
    else:
        raise AlertError("invalid_alert", "Thao tác không hợp lệ.")
    record = repo.write(owner, *RECORD, {"alerts": alerts}, expected_version=expected_version, request_id=request_id)
    return alerts, record.version


def _num(d: Decimal) -> str:
    whole, _, frac = f"{d:,.2f}".partition(".")
    return f"{whole.replace(',', '.')},{frac}"


def render(hits: list[tuple[dict, Decimal]], now: datetime) -> str:
    lines = [f"• {a['symbol']} {_num(p)} {OPS[a['op']]} {_num(Decimal(a['price']))} (mức bạn đặt)" for a, p in hits]
    return (f"Cảnh báo giá · {now.strftime('%H:%M %d/%m')}\n" + "\n".join(lines)
            + "\nGiá cổ phiếu tính bằng nghìn đồng, chỉ số bằng điểm. Mỗi cảnh báo báo một lần; bật lại ở tab Xu hướng. Không phải khuyến nghị.")


def check_alerts(repo, owner, *, prices: dict[str, Decimal], send, now: datetime, request_id: str) -> dict:
    alerts, version = read_alerts(repo, owner)
    hits = []
    for a in alerts:
        price = prices.get(a["symbol"])
        if a["triggered_at"] is None and price is not None:
            level = Decimal(a["price"])
            if (a["op"] == "above" and price >= level) or (a["op"] == "below" and price <= level):
                hits.append((a, price))
    if not hits:
        return {"status": "ok", "triggered": 0, "sent": False}
    if not send(render(hits, now)):
        return {"status": "ok", "triggered": len(hits), "sent": False}
    for a, price in hits:
        a.update(triggered_at=now.isoformat(), triggered_price=format(price.normalize(), "f"))
    repo.write(owner, *RECORD, {"alerts": alerts}, expected_version=version, request_id=request_id)
    return {"status": "ok", "triggered": len(hits), "sent": True}
