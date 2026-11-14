"""Kế hoạch giải ngân theo điều kiện: tranches the owner plans to buy, each waiting for one condition the app can check on stored
public data — the latest daily close at or below a price (thousand đồng), a quarter's report published, or a day reached. The
after-close run marks a tranche met once and sends one note; the owner marks it bought or dropped. Nothing is ordered."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

KINDS = ("price_le", "report", "date")
STATUSES = ("waiting", "met", "done", "dropped")
MAX_TRANCHES = 40
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_QUARTER = re.compile(r"^\d{4}-Q[1-4]$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class PlanError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _dec(raw) -> Decimal | None:
    try:
        v = Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return None
    return v if v.is_finite() else None


def validate(raw: dict) -> dict:
    """One tranche as typed, checked; status and the met fields are the server's."""
    card_id, symbol = str(raw.get("id") or ""), str(raw.get("symbol") or "").strip().upper()
    if not _ID.fullmatch(card_id) or not _SYMBOL.fullmatch(symbol):
        raise PlanError("invalid_symbol", "Cần một mã cổ phiếu hợp lệ.")
    amount = _dec(raw.get("amount"))
    if amount is None or amount <= 0 or amount != amount.to_integral_value():
        raise PlanError("invalid_amount", "Số tiền là số đồng dương.")
    kind, value = raw.get("kind"), str(raw.get("value") or "").strip()
    if kind == "price_le":
        price = _dec(value)
        if price is None or price <= 0:
            raise PlanError("invalid_price", "Giá là số dương, tính bằng nghìn đồng.")
        value = format(price.normalize(), "f")
    elif kind == "report":
        if not _QUARTER.fullmatch(value):
            raise PlanError("invalid_quarter", "Quý theo dạng 2026-Q4.")
    elif kind == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            raise PlanError("invalid_date", "Ngày theo dạng YYYY-MM-DD.") from None
    else:
        raise PlanError("invalid_kind", "Điều kiện không hợp lệ.")
    return {"id": card_id, "symbol": symbol, "amount": format(amount, "f"), "kind": kind, "value": value, "note": str(raw.get("note") or "").strip()[:200]}


def evaluate(tranches: list[dict], *, closes: dict[str, tuple[date, Decimal]], quarters: dict[str, set[str]], today: date) -> tuple[list[dict], list[dict]]:
    """(tranches with the newly met marked, the newly met); only waiting tranches are checked; nothing stored means not met."""
    out, met = [], []
    for t in tranches:
        t = dict(t)
        if t["status"] == "waiting":
            hit = None
            if t["kind"] == "price_le" and t["symbol"] in closes and closes[t["symbol"]][1] <= Decimal(t["value"]):
                hit = format(closes[t["symbol"]][1].normalize(), "f")
            elif t["kind"] == "report" and t["value"] in quarters.get(t["symbol"], set()):
                hit = t["value"]
            elif t["kind"] == "date" and today >= date.fromisoformat(t["value"]):
                hit = t["value"]
            if hit is not None:
                t.update(status="met", met_on=today.isoformat(), met_value=hit)
                met.append(t)
        out.append(t)
    return out, met


def plan_rows(tranches: list[dict], *, closes: dict[str, tuple[date, Decimal]], today: date) -> list[dict]:
    """Each tranche with the latest close and its distance from the level (a price condition), or the days left (a date)."""
    rows = []
    for t in tranches:
        row = {**t, "close": None, "close_date": None, "distance": None, "days_left": None}
        if t["symbol"] in closes:
            day, close = closes[t["symbol"]]
            row.update(close=format(close.normalize(), "f"), close_date=day.isoformat())
            if t["kind"] == "price_le":
                row["distance"] = format(((Decimal(t["value"]) / close) - 1).quantize(Decimal("0.0001")).normalize(), "f")
        if t["kind"] == "date":
            row["days_left"] = max((date.fromisoformat(t["value"]) - today).days, 0)
        rows.append(row)
    return rows


def render(met: list[dict]) -> str:
    what = {"price_le": lambda t: f"giá đóng cửa {t['met_value']} ≤ {t['value']}", "report": lambda t: f"đã có báo cáo {t['value']}",
            "date": lambda t: f"đến ngày {t['value'][8:10]}/{t['value'][5:7]}/{t['value'][:4]}"}
    lines = [f"• {t['symbol']}: {what[t['kind']](t)}" + (f" ({t['note']})" if t["note"] else "") for t in met]
    return ("Kế hoạch giải ngân: đã đến điều kiện\n" + "\n".join(lines)
            + "\nGiá tính bằng nghìn đồng. Phần mềm không đặt lệnh; đánh dấu Đã mua hoặc Bỏ ở Danh mục & Giao dịch. Không phải khuyến nghị.")
