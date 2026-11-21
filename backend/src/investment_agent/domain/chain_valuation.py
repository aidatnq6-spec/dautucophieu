"""Định giá chuỗi so với 5 năm (owner, 21/11/2026): each value chain's median P/E and P/B of its listed members, week by week, and
today's median against the five years before.

Each member's weekly P/E (four quarters) and P/B come from valuation.weekly: every week is priced only with the reports already out
that week. A loss gives no P/E. A chain's week is the median of the members that have a figure that week; today's is its latest
week. The five-year median and position (the share of weeks at or below today's, 0% = cheapest) use the weeks within five years
of it; a chain with less history says since when. A member with no week in the last 30 days is left out and named. Describes; never
recommends."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

YEARS_5 = timedelta(days=round(365.25 * 5))
STALE = timedelta(days=30)


def _q(v: Decimal, places: str = "0.01") -> str:
    return format(v.quantize(Decimal(places), ROUND_HALF_UP), "f")


def _week(day: str) -> tuple[int, int]:
    return date.fromisoformat(day).isocalendar()[:2]


def _side(members: dict[str, list[dict]], *, positive_only: bool) -> dict:
    by_week: dict[tuple, list[Decimal]] = defaultdict(list)
    last_day: dict[tuple, str] = {}
    for points in members.values():
        for p in points:
            if p.get("value") is None:
                continue
            v = Decimal(str(p["value"]))
            if positive_only and v <= 0:
                continue
            w = _week(p["date"])
            by_week[w].append(v)
            last_day[w] = max(last_day.get(w, p["date"]), p["date"])
    if not by_week:
        return {"now": None, "median_5y": None, "position": None, "n": 0, "weeks": 0, "first": None}
    weeks = sorted(by_week)
    medians = [(date.fromisoformat(last_day[w]), Decimal(median(by_week[w]))) for w in weeks]
    latest_day, now = medians[-1]
    window = [v for d, v in medians if d > latest_day - YEARS_5]
    # the five-year figure is the median: a mean was dragged to P/E 1,987 by a year of tiny profits (drilling, 21/11/2026)
    return {"now": _q(now), "median_5y": _q(Decimal(median(window))),
            "position": _q(Decimal(sum(1 for v in window if v <= now)) / len(window)), "n": len(by_week[weeks[-1]]),
            "weeks": len(window), "first": medians[0][0]}


def chain_valuation(chains: list[dict], weekly: dict[str, dict], *, today: date) -> list[dict]:
    """weekly: symbol -> {"pe": points, "pb": points} as valuation.weekly gives them ({date, value})."""
    out = []
    for chain in chains:
        symbols = list(dict.fromkeys(chain["symbols"]))
        live, no_data, stale = {}, [], []
        for s in symbols:
            w = weekly.get(s) or {}
            points = (w.get("pe") or []) + (w.get("pb") or [])
            if not points:
                no_data.append(s)
            elif today - date.fromisoformat(max(p["date"] for p in points)) > STALE:
                stale.append(s)
            else:
                live[s] = w
        pe = _side({s: w.get("pe") or [] for s, w in live.items()}, positive_only=True)
        pb = _side({s: w.get("pb") or [] for s, w in live.items()}, positive_only=True)
        firsts = [x["first"] for x in (pe, pb) if x["first"] is not None]
        latest = today if not live else max(date.fromisoformat(p["date"]) for w in live.values() for p in (w.get("pe") or []) + (w.get("pb") or []))
        first = min(firsts) if firsts else None
        out.append({"id": chain["id"], "name": chain["name"], "members": len(symbols), "priced": len(live), "no_data": no_data, "stale": stale,
                    "pe": {k: v for k, v in pe.items() if k != "first"}, "pb": {k: v for k, v in pb.items() if k != "first"},
                    "since": first.isoformat() if first and first > latest - YEARS_5 else None})
    return out
