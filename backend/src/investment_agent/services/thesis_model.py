"""Kịch bản và chỉ báo: the owner's models (settings/thesis_models, one record for every ticker), the public figures the automatic
indicators read, and the after-close check that sends one note when a light turns bad or a review day comes."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from investment_agent.domain.thesis_model import AUTO, model_view
from investment_agent.services.records import read_version

RECORD, SEEN = ("settings", "thesis_models"), ("settings", "thesis_lights_seen")
B = Decimal(10) ** 9


def read_models(repo, owner) -> tuple[dict, int]:
    record = read_version(repo, owner, *RECORD, None)
    return (dict(record.payload.get("models", {})), record.version) if record else ({}, 0)


def public_figures(data_dir: Path | None, symbol: str, *, today: date, multiples: dict | None = None) -> tuple[Decimal | None, str | None, dict]:
    """(latest close in đồng, its day, {metric: (period, value)}) from stored public data; a metric without a figure is left out.
    multiples: filled with the monthly P/E and P/B series (oldest first) when given."""
    if data_dir is None:
        return None, None, {}
    from investment_agent.market.series import SeriesStore
    from investment_agent.market.statements import StatementStore
    from investment_agent.valuation.history import monthly_multiples
    from investment_agent.valuation.sources import valuation_record
    data_dir = Path(data_dir)
    series = SeriesStore(data_dir / "trend-sources")
    points = series.points(f"{symbol}-1d")
    close, day = (Decimal(points[-1][1]) * 1000, points[-1][0][:10]) if points else (None, None)
    record = StatementStore(data_dir / "statements").read(symbol) or StatementStore(data_dir / "statements-financial").read(symbol) or {}
    auto: dict[str, tuple[str, Decimal]] = {}
    tenth = lambda v: v.quantize(Decimal("0.1"), ROUND_HALF_UP)  # noqa: E731
    for q in sorted(record.get("quarters") or {}, reverse=True):
        f = record["quarters"][q]
        for metric, line in (("npat_parent_q", "npat_parent"), ("revenue_q", "revenue"), ("associates_q", "associates")):
            if metric not in auto and f.get(line) is not None:
                auto[metric] = (q, tenth(Decimal(f[line]) / B))
        if "gross_margin_q" not in auto and f.get("gross_profit") is not None and f.get("revenue") not in (None, "0"):
            auto["gross_margin_q"] = (q, tenth(Decimal(f["gross_profit"]) / Decimal(f["revenue"]) * 100))
    v = valuation_record(data_dir, symbol, today=today)
    hist = monthly_multiples(v["record"], series.read(f"{symbol}-1d"), today=today, shares=v["shares"], published=v["published"])
    for metric, key in (("pe_ttm", "pe"), ("pb", "pb")):
        known = [p for p in hist[key]["points"] if p["value"] is not None]
        if multiples is not None:
            multiples[key] = [Decimal(str(p["value"])) for p in known]
        if known:
            auto[metric] = (known[-1]["month"], Decimal(str(known[-1]["value"])).quantize(Decimal("0.01"), ROUND_HALF_UP))
    return close, day, auto


def view_for(data_dir, symbol: str, model: dict, *, today: date, plans: dict | None = None) -> dict:
    """plans: the owner's own annual plans for the ticker (settings/annual_plan_<symbol>), for the strategy facts."""
    from investment_agent.domain.thesis_model import valuation_bands
    multiples: dict = {}
    close, day, auto = public_figures(data_dir, symbol, today=today, multiples=multiples)
    view = model_view(model, close=close, close_date=day, auto=auto, today=today)
    full = {**model, "ranges": model.get("ranges") or []}
    out = {**view, "bands": valuation_bands(full, close=close, pe=multiples.get("pe", []), pb=multiples.get("pb", []))}
    if data_dir is None:
        return {**out, "auto_catalysts": [], "suggested_indicators": [], "facts": {}, "auto_gaps": {}}
    from investment_agent.market.statements import StatementStore
    from investment_agent.services import thesis_auto
    record = StatementStore(Path(data_dir) / "statements").read(symbol) or StatementStore(Path(data_dir) / "statements-financial").read(symbol) or {}
    quarters, years = record.get("quarters") or {}, record.get("years") or {}
    own = {c["id"] for c in model.get("catalysts") or []}
    facts, gaps = thesis_auto.facts(Path(data_dir), symbol, quarters, years, pe=multiples.get("pe", []), pb=multiples.get("pb", []), plans=plans or {},
                                    lights=view["lights"], today=today)
    return {**out, "auto_catalysts": [c for c in thesis_auto.catalysts(Path(data_dir), symbol, quarters, today=today) if c["id"] not in own],
            "suggested_indicators": thesis_auto.suggested_indicators(quarters, multiples.get("pe", []), have={i["source"] for i in model.get("indicators") or []}),
            "facts": facts, "auto_gaps": gaps}


def check_lights(repo, owner, data_dir, *, send, today: date, request_id: str) -> dict:
    """One note for the indicators newly bad (each once per period) and the scenario reviews whose day has come (each once)."""
    models, _ = read_models(repo, owner)
    if not models:
        return {"status": "ok", "bad": 0, "reviews": 0, "sent": False}
    seen_record = read_version(repo, owner, *SEEN, None)
    seen = dict(seen_record.payload) if seen_record else {}
    lines, new_seen = [], {s: dict(v) for s, v in seen.items()}
    for symbol, model in sorted(models.items()):
        view = view_for(data_dir, symbol, model, today=today)
        mine = new_seen.setdefault(symbol, {})
        for i in view["indicators"]:
            if i["grade"] == "bad" and mine.get(i["id"]) != i["period"]:
                lines.append(f"• {symbol}: {i['name']} {i['current']} {i['unit']} ({i['period']}) chạm mức Xấu {i['bad']}")
                mine[i["id"]] = i["period"]
        for c in view["catalysts"]:
            if c["id"] in view["catalysts_due"] and mine.get(f"_c_{c['id']}") != c["on"]:
                lines.append(f"• {symbol}: đến mốc {c['when'] or c['on']} ({c['sign']}) {c['text']}")
                mine[f"_c_{c['id']}"] = c["on"]
        s = view["scenarios"]
        if s and s["review_due"] and mine.get("_review") != s["review"]["on"]:
            lines.append(f"• {symbol}: đến ngày xem lại kịch bản ({s['review']['when'] or s['review']['on']})")
            mine["_review"] = s["review"]["on"]
    if not lines:
        return {"status": "ok", "bad": 0, "reviews": 0, "sent": False}
    text = "Chỉ báo luận điểm\n" + "\n".join(lines) + "\nTheo ngưỡng bạn đặt ở trang mã. Không phải khuyến nghị."
    if not send(text):
        return {"status": "ok", "lines": len(lines), "sent": False}
    repo.write(owner, *SEEN, new_seen, expected_version=seen_record.version if seen_record else 0, request_id=request_id)
    return {"status": "ok", "lines": len(lines), "sent": True}


__all__ = ["AUTO", "RECORD", "check_lights", "public_figures", "read_models", "view_for"]
