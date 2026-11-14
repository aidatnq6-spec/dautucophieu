"""Kịch bản và chỉ báo của luận điểm (L1, L3), per watched ticker.

L1 — three scenarios (bad, base, good), each a price per share and a probability (all three adding to 100, or none), with one line of
assumptions: the weighted price and the upside against the latest stored close; a "review when" note with an optional day.

L3 — indicators the thesis is watched by, each with a tier (lead, coincident, lag, valuation), its bad, base and good levels and
whether lower is better; its current value is the owner's latest reading or, for an automatic one, the latest published figure.
Graded by the owner's rule (14/11/2026): good when at or beyond the base level, bad when at or beyond the bad level, watch in
between. The good level is shown as the stretch mark. No value, no grade — never guessed.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

NAMES = ("bad", "base", "good")
TIERS = ("lead", "coincident", "lag", "valuation")
AUTO = {"npat_parent_q": ("LN cổ đông mẹ quý", "tỷ"), "revenue_q": ("Doanh thu thuần quý", "tỷ"), "associates_q": ("Lãi công ty liên doanh, liên kết quý", "tỷ"),
        "gross_margin_q": ("Biên lợi nhuận gộp quý", "%"), "pe_ttm": ("P/E bốn quý", "lần"), "pb": ("P/B", "lần")}
MAX_INDICATORS, MAX_READINGS = 15, 12
_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class ModelError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _dec(raw, what: str) -> Decimal:
    try:
        v = Decimal(str(raw).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ModelError("invalid_number", f"{what}: cần một số.") from None
    if not v.is_finite():
        raise ModelError("invalid_number", f"{what}: cần một số.")
    return v


def _s(v: Decimal) -> str:
    return format(v.normalize(), "f") if v != 0 else "0"


def validate_model(raw: dict) -> dict:
    scenarios = []
    for s in raw.get("scenarios") or []:
        price, prob = _dec(s.get("price"), "Giá kịch bản"), _dec(s.get("prob"), "Xác suất")
        if s.get("name") not in NAMES or price <= 0 or not 0 <= prob <= 100:
            raise ModelError("invalid_scenario", "Mỗi kịch bản cần giá dương và xác suất 0–100%.")
        scenarios.append({"name": s["name"], "price": _s(price), "prob": _s(prob), "note": str(s.get("note") or "").strip()[:200]})
    if scenarios:
        if sorted(s["name"] for s in scenarios) != sorted(NAMES):
            raise ModelError("three_scenarios", "Cần đủ ba kịch bản Xấu, Cơ sở, Tốt.")
        if sum(Decimal(s["prob"]) for s in scenarios) != 100:
            raise ModelError("probabilities", "Tổng xác suất ba kịch bản phải bằng 100%.")
        scenarios.sort(key=lambda s: NAMES.index(s["name"]))
    review = raw.get("review") or {}
    on = str(review.get("on") or "").strip() or None
    if on:
        try:
            date.fromisoformat(on)
        except ValueError:
            raise ModelError("invalid_date", "Ngày xem lại theo dạng YYYY-MM-DD.") from None
    indicators = []
    for i in (raw.get("indicators") or [])[:MAX_INDICATORS + 1]:
        if len(indicators) >= MAX_INDICATORS:
            raise ModelError("too_many", f"Tối đa {MAX_INDICATORS} chỉ báo.")
        source = str(i.get("source") or "manual")
        if not _ID.fullmatch(str(i.get("id") or "")) or i.get("tier") not in TIERS or (source != "manual" and source.removeprefix("auto:") not in AUTO):
            raise ModelError("invalid_indicator", "Chỉ báo không hợp lệ.")
        name = str(i.get("name") or "").strip()[:80]
        if not name:
            raise ModelError("invalid_indicator", "Chỉ báo cần tên.")
        levels = {k: _dec(i.get(k), f"Mức {k}") for k in NAMES}
        lower = bool(i.get("lower_better"))
        ordered = levels["bad"] > levels["base"] >= levels["good"] if lower else levels["bad"] < levels["base"] <= levels["good"]
        if not ordered:
            raise ModelError("levels", f"{name}: mức Xấu, Cơ sở, Tốt phải theo đúng thứ tự ({'giảm dần' if lower else 'tăng dần'}).")
        readings = [{"period": str(r.get("period") or "").strip()[:20], "value": _s(_dec(r.get("value"), f"{name}: số đọc"))}
                    for r in (i.get("readings") or [])][-MAX_READINGS:] if source == "manual" else []
        indicators.append({"id": i["id"], "name": name, "tier": i["tier"], "unit": str(i.get("unit") or "").strip()[:12], **{k: _s(v) for k, v in levels.items()},
                           "lower_better": lower, "source": source, "readings": readings})
    return {"scenarios": scenarios, "review": {"when": str(review.get("when") or "").strip()[:200], "on": on}, "indicators": indicators}


def grade(value: Decimal, *, bad: Decimal, base: Decimal, lower_better: bool) -> str:
    if lower_better:
        return "bad" if value >= bad else "good" if value <= base else "watch"
    return "bad" if value <= bad else "good" if value >= base else "watch"


def model_view(model: dict, *, close: Decimal | None, close_date: str | None, auto: dict[str, tuple[str, Decimal]], today: date) -> dict:
    """auto: metric → (period, value) of the latest published figure, in the metric's unit."""
    q4 = lambda v: _s(v.quantize(Decimal("0.0001"), ROUND_HALF_UP))  # noqa: E731
    scen = None
    if model["scenarios"]:
        expected = sum(Decimal(s["price"]) * Decimal(s["prob"]) / 100 for s in model["scenarios"]).quantize(Decimal(1), ROUND_HALF_UP)
        rows = [{**s, "upside": q4(Decimal(s["price"]) / close - 1) if close else None} for s in model["scenarios"]]
        scen = {"rows": rows, "expected": _s(expected), "upside": q4(expected / close - 1) if close else None}
    review = model["review"]
    if scen is not None or review["when"]:
        scen = {**(scen or {"rows": [], "expected": None, "upside": None}), "review": review,
                "review_due": bool(review["on"]) and today >= date.fromisoformat(review["on"])}
    out, lights = [], {"good": 0, "watch": 0, "bad": 0, "none": 0}
    for i in model["indicators"]:
        current, period = None, None
        if i["source"] == "manual" and i["readings"]:
            current, period = i["readings"][-1]["value"], i["readings"][-1]["period"]
        elif i["source"].startswith("auto:") and i["source"][5:] in auto:
            period, v = auto[i["source"][5:]]
            current = _s(v)
        g = grade(Decimal(current), bad=Decimal(i["bad"]), base=Decimal(i["base"]), lower_better=i["lower_better"]) if current is not None else None
        lights[g or "none"] += 1
        out.append({**i, "current": current, "period": period, "grade": g})
    return {"scenarios": scen, "close": _s(close) if close else None, "close_date": close_date, "indicators": out, "lights": lights,
            "auto_metrics": {k: {"label": v[0], "unit": v[1]} for k, v in AUTO.items()}}
