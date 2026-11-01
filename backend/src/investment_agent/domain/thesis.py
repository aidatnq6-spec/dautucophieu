"""Luận điểm đầu tư: why the owner bought a held ticker and the measurable conditions that would tell them they were wrong.

Each condition reads only stored facts; a fact that is missing makes the condition "unknown" with the reason, never passed or
broken. Prices in the facts are in đồng; a close_below level is typed in thousand đồng, as on the price board. Nothing here
says to sell: the owner decides."""

import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from investment_agent.market.indicators import macd
from investment_agent.notifications.render import _num

REASONS = ("cheap", "earnings", "trend", "industry", "fomo")
REASON_VI = {"cheap": "Giá rẻ so với định giá", "earnings": "Kết quả kinh doanh tốt", "trend": "Xu hướng giá đẹp",
             "industry": "Câu chuyện ngành", "fomo": "Sợ bỏ lỡ"}
# kind: (label, params, scope, companies it applies to); scope "price" is checked during the session, "data" after the close.
KINDS = {
    "loss_vs_cost": ("Lỗ so với giá vốn", ("pct",), "price", None),
    "close_below": ("Giá đóng cửa dưới mức", ("level",), "data", None),
    "above_fair": ("Giá vượt mức hợp lý", ("pct",), "data", None),
    "fair_cut": ("Mức hợp lý bị hạ", ("pct",), "data", None),
    "f_score": ("F-Score thấp", ("n",), "data", "other"),
    "health_weak": ("Điểm sức khỏe yếu", (), "data", "financial"),
    "profit_drop": ("Lợi nhuận quý giảm so với cùng kỳ", ("n",), "data", None),
    "macd_weekly": ("MACD tuần cắt xuống", (), "data", None),
    "chain_headwind": ("Chuỗi giá trị chuyển sang bất lợi", (), "data", None),
    "insider_sell": ("Người nội bộ hoặc cổ đông lớn bán", (), "data", None),
}
LIMITS = {"pct": (Decimal(1), Decimal(90)), "n": {"f_score": (0, 8), "profit_drop": (1, 4)}}
MAX_CONDITIONS = 10


class ThesisError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _dec(value) -> Decimal | None:
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _k(value: Decimal) -> str:
    """Đồng as thousand đồng with two decimals, as the price board shows them."""
    return _num(value / 1000, 2)


def _result(state: str, reading: str | None = None, reason: str | None = None) -> dict:
    return {"state": state, "reading": reading, "reason": reason}


def _unknown(reason: str) -> dict:
    return _result("unknown", None, reason)


def _weekly_macd(daily: list[tuple[date, float]]) -> list[tuple[date, float, float]]:
    """(week's Monday, macd, signal) on the last close of each week."""
    weeks: dict[date, float] = {}
    for day, close in daily:
        weeks[day - timedelta(days=day.weekday())] = close
    keys = sorted(weeks)
    line, signal = macd([weeks[k] for k in keys])
    return [(k, a, s) for k, a, s in zip(keys, line, signal) if a is not None and s is not None]


def evaluate(cond: dict, facts: dict) -> dict:
    kind, p = cond["kind"], cond.get("params", {})
    if kind == "loss_vs_cost":
        price, cost = facts.get("price"), facts.get("cost")
        if price is None:
            return _unknown("Chưa có giá khớp")
        if not cost:
            return _unknown("Chưa có giá vốn trong sổ")
        change = price / cost - 1
        reading = f"giá {_k(price)} so với giá vốn {_k(cost)} ({_num(change * 100, 1, sign=True)}%)"
        return _result("broken" if price <= cost * (1 - Decimal(p["pct"]) / 100) else "ok", reading)
    if kind == "close_below":
        close = facts.get("close")
        if close is None:
            return _unknown("Chưa có giá đóng cửa")
        level = Decimal(p["level"]) * 1000
        return _result("broken" if close < level else "ok", f"giá đóng cửa {_k(close)}, mức {_k(level)}")
    if kind in ("above_fair", "fair_cut"):
        fair = facts.get("fair")
        if fair is None:
            return _unknown("Chưa có mức hợp lý (định giá tham khảo)")
        pct = Decimal(p["pct"]) / 100
        if kind == "above_fair":
            price = facts.get("price")
            if price is None:
                return _unknown("Chưa có giá")
            return _result("broken" if price >= fair * (1 + pct) else "ok", f"giá {_k(price)}, mức hợp lý {_k(fair)}")
        before = _dec(cond.get("fair_at_set"))
        if not before:
            return _unknown("Không có mức hợp lý lúc đặt điều kiện")
        return _result("broken" if fair < before * (1 - pct) else "ok", f"mức hợp lý {_k(fair)}, lúc đặt {_k(before)}")
    if kind in ("f_score", "health_weak"):
        q = facts.get("quality")
        wanted = "f_score" if kind == "f_score" else "health"
        if not q or q.get("kind") != wanted:
            return _unknown(facts.get("quality_reason") or ("Chưa có F-Score" if kind == "f_score" else "Chưa có Điểm sức khỏe"))
        if kind == "f_score":
            return _result("broken" if q["score"] <= int(p["n"]) else "ok", f"F-Score {q['score']} (năm {q['year']}), ngưỡng {p['n']}")
        if q.get("level") is None:
            return _unknown("Điểm sức khỏe chưa đủ tiêu chí để xếp mức")
        return _result("broken" if q["level"] == "weak" else "ok", f"Điểm sức khỏe {q['score']} ({q['year']}), mức {q['level']}")
    if kind == "profit_drop":
        quarters = facts.get("quarters") or {}
        latest = sorted(quarters)[-int(p["n"]):] if quarters else []
        pairs = []
        for q in latest:
            year, _, part = q.partition("-")
            before = quarters.get(f"{int(year) - 1}-{part}")
            if before is None:
                return _unknown("Thiếu lợi nhuận quý cùng kỳ năm trước")
            pairs.append((q, quarters[q], before))
        if len(pairs) < int(p["n"]):
            return _unknown("Chưa đủ quý có lợi nhuận")
        reading = "; ".join(f"{q}: {_num(now / 10**9, 1)} tỷ so với {_num(before / 10**9, 1)} tỷ" for q, now, before in pairs)
        return _result("broken" if all(now < before for _, now, before in pairs) else "ok", reading)
    if kind == "macd_weekly":
        weekly = _weekly_macd(facts.get("daily") or [])
        if len(weekly) < 2:
            return _unknown("Chưa đủ nến tuần để tính MACD")
        set_week = date.fromisoformat(cond["set_on"])
        set_week -= timedelta(days=set_week.weekday())
        _, line, signal = weekly[-1]
        crossed = any(a < s and pa >= ps for (_, pa, ps), (k, a, s) in zip(weekly, weekly[1:]) if k >= set_week)
        return _result("broken" if line < signal and crossed else "ok", f"MACD tuần {_num(line, 2)}, tín hiệu {_num(signal, 2)}")
    if kind == "chain_headwind":
        chains = facts.get("chains")
        if not chains:
            return _unknown("Mã không thuộc chuỗi giá trị nào")
        if "headwind" in chains:
            return _result("broken", "ít nhất một chuỗi giá trị của mã đang bất lợi")
        if all(c in (None, "insufficient") for c in chains):
            return _unknown("Chuỗi giá trị chưa duyệt hoặc thiếu dữ liệu")
        return _result("ok", "không chuỗi nào bất lợi")
    if kind == "insider_sell":
        sells = facts.get("insider_sells")
        if sells is None:
            return _unknown("Chưa đọc được thông báo giao dịch nội bộ")
        if not sells:
            return _result("ok", "không có thông báo bán mới")
        first = sells[0]
        return _result("broken", f"{len(sells)} thông báo bán, gần nhất {first.get('date')}: {first.get('name')}")
    raise ThesisError("invalid_condition", "Loại điều kiện không hợp lệ.")


def _param(kind: str, name: str, raw) -> str:
    if name == "pct":
        d = _dec(raw)
        low, high = LIMITS["pct"]
        if d is None or not low <= d <= high:
            raise ThesisError("invalid_condition", "Tỷ lệ cần từ 1 đến 90 (%).")
        return format(d.normalize(), "f")
    if name == "level":
        d = _dec(raw)
        if d is None or d <= 0 or len(str(raw)) > 16:
            raise ThesisError("invalid_condition", "Mức giá cần là số dương (nghìn đồng), ví dụ 48,5.")
        return format(d.normalize(), "f")
    low, high = LIMITS["n"][kind]
    if isinstance(raw, bool) or not isinstance(raw, int) or not low <= raw <= high:
        raise ThesisError("invalid_condition", f"Số cần từ {low} đến {high}.")
    return raw


def validate_condition(raw: dict, *, company: str | None) -> dict:
    kind = raw.get("kind") if isinstance(raw, dict) else None
    if kind not in KINDS:
        raise ThesisError("invalid_condition", "Loại điều kiện không hợp lệ.")
    label, names, _, applies = KINDS[kind]
    if applies is not None and company is not None and company != applies:
        raise ThesisError("not_applicable", f"“{label}” không áp dụng cho loại doanh nghiệp này.")
    params = raw.get("params") or {}
    return {"id": uuid.uuid4().hex[:12], "kind": kind, "params": {n: _param(kind, n, params.get(n)) for n in names}}


STEP = Decimal("0.05")  # a further fall of 5% from the price at the first report is reported again, once per step
MAX_HOLD_DAYS = 90


def _fresh(cond: dict, today: date, fair: str | None) -> dict:
    out = {**cond, "set_on": today.isoformat(), "status": None, "reading": None, "reason": None, "current": None, "broken_on": None,
           "broken_price": None, "broken_reading": None, "sent_first": False, "steps_sent": [], "hold": None}
    if cond["kind"] == "fair_cut":
        out["fair_at_set"] = fair
    return out


def new_thesis(symbol: str, validated: dict, *, today: date, snapshot: dict) -> dict:
    """A new thesis from validate_thesis(); snapshot holds the figures at that moment (each may be None)."""
    return {"id": uuid.uuid4().hex[:12], "symbol": symbol, "reasons": validated["reasons"], "note": validated["note"],
            "created_on": today.isoformat(), "snapshot": snapshot, "version": 1, "closed_on": None, "history": [],
            "conditions": [_fresh(c, today, snapshot.get("fair")) for c in validated["conditions"]]}


def _holding(cond: dict, today: date) -> bool:
    hold = cond.get("hold")
    return bool(hold) and (hold.get("until") is None or today <= date.fromisoformat(hold["until"]))


def advance(thesis: dict, results: dict[str, dict], *, today: date, price: Decimal | None) -> tuple[dict, list[dict]]:
    """Apply one check. A broken condition stays broken (only its current reading changes) until the thesis closes or the owner
    holds on with a reason. Returns the events to report: first (newly broken, offered until sent), step (a further 5% fall
    from the price at the first report), review (a hold-on date has passed)."""
    t = {**thesis, "conditions": [dict(c) for c in thesis["conditions"]]}
    events = []
    for c in t["conditions"]:
        r = results.get(c["id"])
        if r is None:
            continue
        if c["status"] == "broken":
            c["current"] = r["reading"] or r["reason"]
        else:
            c.update(status=r["state"], reading=r["reading"], reason=r["reason"], current=r["reading"])
            if r["state"] == "broken":
                c.update(broken_on=today.isoformat(), broken_price=None if price is None else format(price.normalize(), "f"),
                         broken_reading=r["reading"])
        if c["status"] != "broken":
            continue
        hold = c.get("hold")
        if _holding(c, today):
            continue
        if hold and not hold.get("review_sent"):
            events.append({"type": "review", "condition": c})
        elif not c["sent_first"]:
            events.append({"type": "first", "condition": c})
        elif price is not None and c["broken_price"]:
            level = int((1 - price / Decimal(c["broken_price"])) / STEP)
            if level >= 1 and level not in c["steps_sent"] and level > max(c["steps_sent"], default=0):
                events.append({"type": "step", "condition": c, "level": level})
    return t, events


def mark_sent(thesis: dict, events: list[dict]) -> dict:
    """Record the events as delivered (call only after the message went out)."""
    t = {**thesis, "conditions": [dict(c) for c in thesis["conditions"]]}
    by_id = {c["id"]: c for c in t["conditions"]}
    for e in events:
        c = by_id.get(e["condition"]["id"])
        if c is None:
            continue
        if e["type"] == "first":
            c["sent_first"] = True
        elif e["type"] == "step":
            c["steps_sent"] = sorted({*c["steps_sent"], e["level"]})
        elif e["type"] == "review":
            c["hold"] = {**c["hold"], "review_sent": True}
            c["sent_first"] = True
    return t


def hold_condition(thesis: dict, cond_id: str, *, reason: str, until: date | None, new_condition: dict | None, today: date, entry_id: str,
                   company: str | None = None, fair: str | None = None) -> dict:
    """Giữ tiếp, có lý do: a written reason and either a replacement condition or a review date within 90 days."""
    c = next((c for c in thesis["conditions"] if c["id"] == cond_id), None)
    if c is None:
        raise ThesisError("condition_not_found", "Không tìm thấy điều kiện này; hãy tải lại.")
    if c["status"] != "broken":
        raise ThesisError("not_broken", "Chỉ điều kiện đã bị phá mới cần quyết định giữ tiếp.")
    if not reason.strip():
        raise ThesisError("reason_required", "Viết lý do giữ tiếp.")
    if new_condition is None and until is None:
        raise ThesisError("hold_needs_condition_or_date", "Đặt điều kiện mới hoặc ngày xem lại.")
    if until is not None and not today < until <= today + timedelta(days=MAX_HOLD_DAYS):
        raise ThesisError("invalid_review_date", f"Ngày xem lại trong vòng {MAX_HOLD_DAYS} ngày tới.")
    record = {"type": "hold", "condition": c["id"], "kind": c["kind"], "on": today.isoformat(), "reason": reason.strip(),
              "broken_on": c["broken_on"], "broken_price": c["broken_price"], "until": None if until is None else until.isoformat(),
              "entry_id": entry_id}
    t = {**thesis, "history": [*thesis["history"]]}
    if new_condition is not None:
        fresh = _fresh(validate_condition(new_condition, company=company), today, fair)
        t["history"].append({**c, "ended_on": today.isoformat(), "ended_by": "hold"})
        t["conditions"] = [fresh if x["id"] == cond_id else x for x in thesis["conditions"]]
    else:
        t["conditions"] = [{**x, "hold": {"since": today.isoformat(), "until": until.isoformat(), "reason": reason.strip(), "entry_id": entry_id,
                                          "review_sent": False}} if x["id"] == cond_id else x for x in thesis["conditions"]]
    t["history"].append(record)
    return t


def edit_thesis(thesis: dict, raw: dict, *, company: str | None, today: date, fair: str | None) -> dict:
    """Change reasons, note and conditions. A broken condition can be neither changed nor removed (only held on with a reason);
    a changed condition starts afresh under a new id and the old one goes to history."""
    validated = validate_thesis(raw, company=company)
    current = {c["id"]: c for c in thesis["conditions"]}
    kept_ids = [c.get("id") for c in raw["conditions"]]
    history = [*thesis["history"]]
    for c in thesis["conditions"]:
        if c["status"] == "broken" and c["id"] not in kept_ids:
            raise ThesisError("broken_locked", "Điều kiện đã bị phá chỉ thay đổi qua “Giữ tiếp, có lý do”.")
    conditions = []
    for asked, checked in zip(raw["conditions"], validated["conditions"]):
        old = current.get(asked.get("id"))
        if old is not None and old["kind"] == checked["kind"] and old["params"] == checked["params"]:
            conditions.append(old)
            continue
        if old is not None:
            if old["status"] == "broken":
                raise ThesisError("broken_locked", "Điều kiện đã bị phá chỉ thay đổi qua “Giữ tiếp, có lý do”.")
            history.append({**old, "ended_on": today.isoformat(), "ended_by": "edit"})
        conditions.append(_fresh(checked, today, fair))
    history += [{**c, "ended_on": today.isoformat(), "ended_by": "edit"} for c in thesis["conditions"] if c["id"] not in kept_ids]
    return {**thesis, "reasons": validated["reasons"], "note": validated["note"], "conditions": conditions, "history": history,
            "version": thesis["version"] + 1}


def validate_thesis(raw: dict, *, company: str | None) -> dict:
    reasons = raw.get("reasons") or []
    if not reasons:
        raise ThesisError("reason_required", "Chọn ít nhất một lý do mua.")
    if any(r not in REASONS for r in reasons):
        raise ThesisError("invalid_reason", "Lý do mua không hợp lệ.")
    note = str(raw.get("note") or "")
    if len(note) > 2000:
        raise ThesisError("invalid_note", "Lời viết tối đa 2.000 ký tự.")
    conditions = raw.get("conditions") or []
    if not conditions:
        raise ThesisError("condition_required", "Đặt ít nhất một điều kiện cho biết bạn đã sai.")
    if len(conditions) > MAX_CONDITIONS:
        raise ThesisError("invalid_condition", f"Tối đa {MAX_CONDITIONS} điều kiện.")
    kept = [validate_condition(c, company=company) for c in conditions]
    if "fomo" in reasons and not any(c["kind"] == "loss_vs_cost" for c in kept):
        raise ThesisError("loss_limit_required", "Mua vì sợ bỏ lỡ thì cần đặt mức lỗ tối đa so với giá vốn.")
    return {"reasons": [r for r in REASONS if r in reasons], "note": note, "conditions": kept}
