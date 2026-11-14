"""Điểm khách quan của quỹ: only what can be measured, each as a percentile among the funds of the same kind (0 = the weakest,
100 = the best), and the score their plain mean.

- returns: Fmarket's 1-year and 3-year returns (each ranked among the funds that have it; their mean);
- fee: the management fee, lower ranks higher;
- risk: from the NAV history kept since 11/2026, once a fund has RISK_MIN_DAYS points: the deepest fall from a peak and the spread
  of daily changes, lower ranks higher (their mean).

A measure without figures is left out of the score and named, never filled in; a fund alone in its kind has no score. The outlook a
fund manager talks about is a judgement, not a measure, and is not scored. Monthly snapshots give the trend.
"""

from decimal import ROUND_HALF_UP, Decimal
from statistics import pstdev

RISK_MIN_DAYS = 120
PARTS = ("returns", "fee", "risk")


def _s(value: Decimal | None) -> str | None:
    if value is None:
        return None
    q = value.quantize(Decimal("0.1"), ROUND_HALF_UP)
    return format(q.normalize(), "f") if q != 0 else "0"


def _percentiles(values: dict[str, Decimal], *, higher_is_better: bool) -> dict[str, Decimal]:
    """Share of the other funds this one beats, ×100; ties share their place. Needs two funds or more."""
    if len(values) < 2:
        return {}
    out = {}
    for code, v in values.items():
        beaten = sum(1 for c, w in values.items() if c != code and (w < v if higher_is_better else w > v))
        tied = sum(1 for c, w in values.items() if c != code and w == v)
        out[code] = (Decimal(beaten) + Decimal(tied) / 2) / (len(values) - 1) * 100
    return out


def history_risk(points: dict[str, str]) -> dict | None:
    """Deepest fall from a running peak and the spread (population standard deviation) of daily changes, as ratios; None when
    fewer than RISK_MIN_DAYS points are kept."""
    navs = [Decimal(v) for _, v in sorted(points.items())]
    if len(navs) < RISK_MIN_DAYS:
        return None
    peak, deepest = navs[0], Decimal(0)
    for v in navs:
        peak = max(peak, v)
        deepest = max(deepest, (peak - v) / peak)
    changes = [float(b / a - 1) for a, b in zip(navs, navs[1:])]
    return {"drawdown": format(deepest.normalize(), "f") if deepest else "0", "spread": format(Decimal(str(pstdev(changes))).normalize(), "f")}


def _mean(values: list[Decimal]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


def fund_scores(profiles: dict, history: dict[str, dict[str, str]]) -> dict[str, dict]:
    """profiles: market.fund_nav.fund_profiles(); history: fund_history(). {code: {score, parts, counted, risk_days, peers}}."""
    out = {}
    kinds = {p.get("kind") for p in profiles.values() if p.get("kind")}
    for kind in kinds:
        codes = [c for c, p in profiles.items() if p.get("kind") == kind]

        def ranked(field, *, higher):
            values = {c: Decimal(v) for c in codes if (v := (profiles[c].get("returns") or {}).get(field) if field in ("m12", "m36")
                                                         else profiles[c].get(field)) is not None}
            return _percentiles(values, higher_is_better=higher)
        m12, m36, fee = ranked("m12", higher=True), ranked("m36", higher=True), ranked("fee", higher=False)
        risks = {c: r for c in codes if (r := history_risk(history.get(c) or {}))}
        drawdown = _percentiles({c: Decimal(r["drawdown"]) for c, r in risks.items()}, higher_is_better=False)
        spread = _percentiles({c: Decimal(r["spread"]) for c, r in risks.items()}, higher_is_better=False)
        for c in codes:
            parts = {"returns": _mean([p[c] for p in (m12, m36) if c in p]), "fee": fee.get(c),
                     "risk": _mean([p[c] for p in (drawdown, spread) if c in p])}
            counted = [k for k in PARTS if parts[k] is not None]
            out[c] = {"score": _s(_mean([parts[k] for k in counted])), "parts": {k: _s(v) for k, v in parts.items()}, "counted": counted,
                      "risk_days": len(history.get(c) or {}), "peers": len(codes)}
    return out


def score_trend(snapshots: dict[str, dict[str, str]], month: str) -> dict[str, dict | None]:
    """Each fund's score this month against the latest earlier month that scored it."""
    earlier = sorted(m for m in snapshots if m < month)
    out = {}
    for code, score in (snapshots.get(month) or {}).items():
        before = next((snapshots[m][code] for m in reversed(earlier) if snapshots[m].get(code) is not None), None)
        out[code] = None if before is None or score is None else {"previous": before, "change": _s(Decimal(score) - Decimal(before))}
    return out


SNAPSHOTS = "fund-scores.json"


def read_snapshots(data_dir) -> dict[str, dict[str, str]]:
    import json
    from pathlib import Path
    path = Path(data_dir) / SNAPSHOTS
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def record_scores(data_dir, month: str, scores: dict[str, dict]) -> None:
    """The month's scores (public fund data only), replaced by each later run in the same month."""
    import json
    import os
    from pathlib import Path
    snaps = read_snapshots(data_dir)
    snaps[month] = {c: s["score"] for c, s in sorted(scores.items()) if s.get("score") is not None}
    path = Path(data_dir) / SNAPSHOTS
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(snaps, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
