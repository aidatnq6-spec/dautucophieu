"""Turning matched orders from a broker statement into ledger trades. An order already imported, or already typed by hand, is not added
again; one before the opening balance stays out. The rest are checked by replaying the whole ledger with them: if it cannot hold them,
nothing is added and the first order that breaks it is named."""

from collections import Counter

from .ledger import LedgerError, Trade, parse_events, replay

MESSAGES = {"oversell": "Lệnh bán này vượt số cổ phiếu trong sổ: sổ chưa có lệnh mua hoặc số dư của mã này trước ngày đó.",
            "cash_negative": "Tiền trong sổ sẽ âm từ lệnh này: cần ghi nộp tiền hoặc số dư đầu kỳ trước ngày đó.",
            "before_opening_balance": "Có lệnh nằm trước số dư đầu kỳ.", "ambiguous_order": "Trùng thứ tự trong ngày.", "duplicate_event": "Trùng mã giao dịch."}


def _key(day, kind, symbol, quantity, price):
    return (str(day), kind, symbol, quantity, float(price))


def plan_import(original, effective, orders: list[dict]) -> dict:
    """`original`: every event ever recorded, cancelled ones too; `effective`: the ledger after amendments. Returns rows with a status
    (new, already, manual, before_opening), the trades to add, counts, and what blocks the import."""
    known = {e.event_id for e in original}
    opening = next((e.effective_at for e in effective if e.type == "opening_balance"), None)
    typed = Counter(_key(e.effective_at, e.type, e.security_id, e.quantity, e.price) for e in effective if isinstance(e, Trade) and not e.event_id.startswith("tcbs-"))
    used = {}
    for e in effective:
        used[e.effective_at] = max(used.get(e.effective_at, -1), e.sequence)
    rows, made, seen = [], [], Counter()
    for o in sorted(orders, key=lambda x: (x["date"], x["type"] != "sell", x["line"])):  # shares bought today cannot be sold today (T+2)
        seen[o["order_no"]] += 1
        event_id = f"tcbs-{o['order_no']}" + (f"-{seen[o['order_no']]}" if seen[o["order_no"]] > 1 else "")
        key = _key(o["date"], o["type"], o["symbol"], o["quantity"], o["price"])
        if event_id in known:
            status = "already"
        elif typed[key] > 0:
            typed[key] -= 1
            status = "manual"
        elif opening is not None and o["date"] < opening:
            status = "before_opening"
        else:
            status = "new"
            used[o["date"]] = used.get(o["date"], -1) + 1
            made.append({"event_id": event_id, "type": o["type"], "effective_at": o["date"].isoformat(), "sequence": used[o["date"]], "security_id": o["symbol"],
                         "quantity": o["quantity"], "price": o["price"], "fee": o["fee"], "tax": o["tax"], "note": "Nhập từ sao kê TCBS"})
        rows.append({**o, "date": o["date"].isoformat(), "status": status})
    counts = Counter(r["status"] for r in rows)
    blocked = None
    try:
        replay([*effective, *parse_events(made)])
    except LedgerError as exc:
        culprit = next((e for e in made if e["event_id"] == getattr(exc, "event_id", None)), None)
        blocked = {"code": exc.code, "message": MESSAGES.get(exc.code, "Các lệnh này mâu thuẫn với sổ hiện tại."), "symbol": culprit["security_id"] if culprit else None,
                   "date": culprit["effective_at"] if culprit else None}
    return {"rows": rows, "events": made, "blocked": blocked, "counts": {k: counts.get(k, 0) for k in ("new", "already", "manual", "before_opening")}}
