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
# L4: the six questions of a thesis, each with a status, a one-line answer, its points and its gaps (what is still to find out).
QUESTIONS = ("business", "strategy", "industry", "valuation", "monitoring", "timing")
STATUSES = ("good", "watch", "bad")
MAX_POINTS, MAX_GAPS, MAX_CATALYSTS = 8, 10, 20
SIGNS = ("+", "-", "?")
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
    return {"scenarios": scenarios, "review": {"when": str(review.get("when") or "").strip()[:200], "on": on}, "indicators": indicators,
            "questions": _questions(raw.get("questions") or {}), "catalysts": _catalysts(raw.get("catalysts") or []),
            "stage": "reviewed" if raw.get("stage") == "reviewed" else "draft", "updated_on": raw.get("updated_on"),
            "headline": _text(raw.get("headline"), 200), "summary": _text(raw.get("summary"), 800), "ranges": _ranges(raw.get("ranges") or [])}


MAX_RANGES, BAND_MONTHS, BAND_MIN_MONTHS = 8, 60, 24


def _ranges(raw: list) -> list:
    """L2: the owner's own valuation ranges (SOTP, EV/EBITDA, brokers' targets…), each low to high with an optional middle."""
    if len(raw) > MAX_RANGES:
        raise ModelError("too_many", f"Tối đa {MAX_RANGES} cách định giá tự nhập.")
    out = []
    for r in raw:
        name = _text(r.get("name"), 40)
        low, high = _dec(r.get("low"), f"{name or 'Cách định giá'}: giá thấp"), _dec(r.get("high"), f"{name or 'Cách định giá'}: giá cao")
        mid = _dec(r.get("mid"), f"{name}: mốc giữa") if str(r.get("mid") or "").strip() else None
        if not _ID.fullmatch(str(r.get("id") or "")) or not name or low <= 0 or high < low or (mid is not None and not low <= mid <= high):
            raise ModelError("invalid_range", "Mỗi cách định giá cần tên và giá thấp ≤ (giữa) ≤ cao, đều dương.")
        out.append({"id": r["id"], "name": name, "low": _s(low), "mid": _s(mid) if mid is not None else None, "high": _s(high),
                    "source": _text(r.get("source"), 120)})
    return out


def suggest_scenarios(*, close: Decimal | None, pe: list[Decimal]) -> list[dict] | None:
    """A6: a mechanical first draft for the three scenarios: P/E at its 25th percentile, median and 75th percentile of the last five
    years × what one share earns today (the close divided by today's P/E), probabilities 25/50/25. None without 24 months."""
    recent = [v for v in pe[-BAND_MONTHS:] if v > 0]
    if close is None or len(recent) < BAND_MIN_MONTHS:
        return None
    from statistics import median
    ordered, per_share = sorted(recent), close / recent[-1]
    at = lambda q: ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]  # noqa: E731
    out = []
    for name, multiple, prob, what in (("bad", at(0.25), "25", "phân vị 25%"), ("base", Decimal(str(median(recent))), "50", "trung vị"),
                                       ("good", at(0.75), "25", "phân vị 75%")):
        price = (multiple * per_share).quantize(Decimal(100), ROUND_HALF_UP)
        out.append({"name": name, "price": _s(price), "prob": prob,
                    "note": f"Gợi ý: P/E {what} {len(recent)} tháng ({format(multiple.quantize(Decimal('0.1'), ROUND_HALF_UP), 'f').replace('.', ',')} lần) × lợi nhuận mỗi CP hiện tại"})
    return out


def valuation_bands(model: dict, *, close: Decimal | None, pe: list[Decimal], pb: list[Decimal], reference: dict | None = None) -> dict:
    """L2: one bar per way of valuing, in đồng per share: the scenarios (lowest to highest, the weighted price as the middle); P/E
    and P/B over the last five years (lowest, median, highest) applied to what one share earns or owns today — the close divided by
    today's multiple, so nothing is estimated; and the owner's own ranges. pe, pb: monthly multiples, oldest first."""
    from statistics import median
    rows, notes = [], []
    if reference and reference.get("low") and reference.get("high"):
        names = ", ".join(m["label"] for m in reference.get("methods") or [] if m.get("value") is not None)
        rows.append({"id": "reference", "name": "Định giá tham chiếu", "low": reference["low"], "mid": reference.get("fair"), "high": reference["high"],
                     "source": f"Trang Định giá: {names}" if names else "Trang Định giá", "auto": True})
    elif reference is not None:
        notes.append(f"Định giá tham chiếu: {reference.get('reason') or 'chưa đủ dữ liệu'}")
    if model["scenarios"]:
        prices = [Decimal(s["price"]) for s in model["scenarios"]]
        expected = sum(Decimal(s["price"]) * Decimal(s["prob"]) / 100 for s in model["scenarios"])
        rows.append({"id": "scenarios", "name": "Kịch bản (của bạn)", "low": _s(min(prices)), "mid": _s(expected.quantize(Decimal(1), ROUND_HALF_UP)),
                     "high": _s(max(prices)), "source": "Ba kịch bản ở trên", "auto": True})
    for key, label, series in (("pe", "P/E 5 năm", pe), ("pb", "P/B 5 năm", pb)):
        recent = [v for v in series[-BAND_MONTHS:] if v > 0]
        if close is None or len(recent) < BAND_MIN_MONTHS:
            notes.append(f"{label}: chưa đủ {BAND_MIN_MONTHS} tháng số dương")
            continue
        per_share = close / recent[-1]
        price = lambda m: _s((m * per_share).quantize(Decimal(100), ROUND_HALF_UP))  # noqa: E731
        ordered = sorted(recent)
        pct = lambda q: ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]  # noqa: E731 - nearest rank
        # The middle half (25th to 75th percentile), not lowest to highest: months of near-zero profit put P/E in the hundreds (ANV, 11/2026).
        rows.append({"id": key, "name": label, "low": price(pct(Decimal("0.25"))), "mid": price(Decimal(str(median(recent)))), "high": price(pct(Decimal("0.75"))),
                     "source": f"{len(recent)} tháng, phân vị 25%–trung vị–75% × {'lợi nhuận' if key == 'pe' else 'giá trị sổ sách'} mỗi CP hiện tại",
                     "auto": True})
    rows += [{**r, "auto": False} for r in model.get("ranges") or []]
    return {"rows": rows, "close": _s(close) if close is not None else None, "notes": notes}


def _text(v, limit: int) -> str:
    return str(v or "").strip()[:limit]


def _day(v, what: str) -> str | None:
    v = _text(v, 10) or None
    if v:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ModelError("invalid_date", f"{what}: ngày theo dạng YYYY-MM-DD.") from None
    return v


def _questions(raw: dict) -> dict:
    out = {}
    for key in QUESTIONS:
        q = raw.get(key) or {}
        status = q.get("status") if q.get("status") in STATUSES else None
        points = [p for p in (_text(p, 300) for p in q.get("points") or []) if p][:MAX_POINTS]
        gaps = []
        for g in (q.get("gaps") or [])[:MAX_GAPS]:
            if not _ID.fullmatch(str(g.get("id") or "")) or not _text(g.get("text"), 200):
                raise ModelError("invalid_gap", "Mỗi chỗ trống cần nội dung.")
            gaps.append({"id": g["id"], "text": _text(g.get("text"), 200), "ref": _text(g.get("ref"), 20), "done": bool(g.get("done"))})
        out[key] = {"status": status, "summary": _text(q.get("summary"), 300), "points": points, "gaps": gaps}
    return out


def _catalysts(raw: list) -> list:
    if len(raw) > MAX_CATALYSTS:
        raise ModelError("too_many", f"Tối đa {MAX_CATALYSTS} mốc.")
    out = []
    for c in raw:
        if not _ID.fullmatch(str(c.get("id") or "")) or not _text(c.get("text"), 200) or c.get("sign") not in SIGNS:
            raise ModelError("invalid_catalyst", "Mỗi mốc cần nội dung và dấu +, − hoặc ?.")
        out.append({"id": c["id"], "when": _text(c.get("when"), 20), "on": _day(c.get("on"), "Ngày nhắc"), "sign": c["sign"], "text": _text(c.get("text"), 200),
                    "source": _text(c.get("source"), 120), "done": bool(c.get("done"))})
    return out


def gap_count(questions: dict) -> dict:
    gaps = [g for q in questions.values() for g in q["gaps"]]
    return {"open": sum(1 for g in gaps if not g["done"]), "total": len(gaps)}


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
    questions = model.get("questions") or _questions({})
    model = {**model, "ranges": model.get("ranges") or [], "headline": model.get("headline", ""), "summary": model.get("summary", "")}
    catalysts = sorted(model.get("catalysts") or [], key=lambda c: (c["done"], c["on"] or "9999", c["when"]))
    due = [c["id"] for c in catalysts if c["on"] and not c["done"] and today >= date.fromisoformat(c["on"])]
    return {"scenarios": scen, "close": _s(close) if close else None, "close_date": close_date, "indicators": out, "lights": lights,
            "questions": questions, "gaps": gap_count(questions), "catalysts": catalysts, "catalysts_due": due,
            "stage": model.get("stage", "draft"), "updated_on": model.get("updated_on"),
            "auto_metrics": {k: {"label": v[0], "unit": v[1]} for k, v in AUTO.items()}}
