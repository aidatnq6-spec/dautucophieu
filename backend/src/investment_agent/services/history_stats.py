"""Thống kê lịch sử: reads the stored public series (VN-Index closes, VN-Index P/E, oil, the broad dollar, the US 10-year yield) and
hands them to domain.history_stats. Results are kept in memory for the day: about two seconds to work out, the series change daily."""

from __future__ import annotations

import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.history_stats import light_groups, pe_groups
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore

HORIZONS = (20, 60, 120, 250)
LIGHTS = ("oil", "usd", "us10y", "pe")
_CACHE: dict = {}
TTL_SECONDS = 3600


def _series(store: SeriesStore, key: str) -> list[tuple[date, Decimal]]:
    return [(t.date(), Decimal(str(v))) for t, v in store.read(key) if v]


def _macro(data_dir: Path, key: str) -> list[tuple[date, Decimal]]:
    return [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in MacroStore(data_dir).read(key)]


FX_THRESHOLDS = ("0.5", "1", "2", "3")  # % in three months, the 2×2's USD/VND slider


def _us10y(data_dir: Path) -> list[tuple[date, Decimal]]:
    """FRED's long DGS10 history with the recent series the light reads (the same figures on common days); the recent one wins."""
    merged = dict(_macro(data_dir, "us10y_long"))
    merged.update(dict(_macro(data_dir, "us10y")))
    return sorted(merged.items())


def all_series(data_dir: Path) -> dict[str, list[tuple[date, Decimal]]]:
    data_dir = Path(data_dir)
    out = {k: _macro(data_dir, k) for k in ("factor_oil", "factor_usd", "wb_vn_cpi_yoy", "wb_vn_iip", "wb_vn_usdvnd", "wb_vn_exports")}
    out["us10y"] = _us10y(data_dir)
    out["vnindex_pe"] = _series(SeriesStore(data_dir / "index-valuation"), "VNINDEX-pe-1d")
    return out


def conditions_now(data_dir: Path, *, fx: str, today: date) -> tuple[dict, list[dict]]:
    """(each condition's known states, each condition today: its state if its figure still stands, the figure's own date, since when)."""
    from investment_agent.domain.history_states import CONDITIONS, MONTHLY_LAG, STALE, condition_days
    series, threshold = all_series(Path(data_dir)), Decimal(fx) / 100
    known = {k: condition_days(k, series, fx=threshold) for k in CONDITIONS}
    conditions = []
    for k, spec in CONDITIONS.items():
        last = known[k][-1] if known[k] else None
        fresh = last is not None and today - last[0] <= STALE[spec["kind"]]
        # the figure's own date: a month's end (known on the 10th after, USD/VND on the 1st), a day's (known the next day)
        figure = None if last is None else last[0] - (timedelta(days=0) if k == "pe_high" else MONTHLY_LAG if spec["kind"] == "monthly" and k != "fx_up"
                                                       else timedelta(days=1))
        conditions.append({"id": k, "label": spec["label"].replace("{fx}", f"{fx}%"), "kind": spec["kind"], "state": last[1] if fresh else None,
                           "known_on": last[0].isoformat() if last else None, "figure_date": figure.isoformat() if figure else None,
                           "from": known[k][0][0].isoformat() if known[k] else None})
    return known, conditions


def history_states(data_dir: Path, *, a: str, b: str, h: int, fx: str, today: date) -> dict:
    """The 2×2 of two conditions, every condition's state today (known since when) and VN-Index's weekly line for the chart."""
    from investment_agent.domain.history_states import CONDITIONS, condition_days, states_table
    key = ("states", str(data_dir), a, b, h, fx, today)
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]
    closes = _series(SeriesStore(Path(data_dir) / "trend-sources"), "VNINDEX-1d")
    known, conditions = conditions_now(Path(data_dir), fx=fx, today=today)
    label = lambda k: CONDITIONS[k]["label"].replace("{fx}", f"{fx}%")  # noqa: E731
    table = states_table(known[a], known[b], closes, h=h, kinds=(CONDITIONS[a]["kind"], CONDITIONS[b]["kind"]))
    weekly = {}
    for d, v in closes:
        weekly[d.isocalendar()[:2]] = (d, v)
    out = {**table, "a": {"id": a, "label": label(a)}, "b": {"id": b, "label": label(b)}, "fx": fx, "conditions": conditions,
           "line": [{"date": d.isoformat(), "close": format(v, "f")} for d, v in sorted(weekly.values())]}
    _CACHE[key] = (time.monotonic(), out)
    return out


def history_stats(data_dir: Path, *, h: int, today: date) -> dict:
    key = (str(data_dir), h, today)
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]
    data_dir = Path(data_dir)
    closes = _series(SeriesStore(data_dir / "trend-sources"), "VNINDEX-1d")
    pe = _series(SeriesStore(data_dir / "index-valuation"), "VNINDEX-pe-1d")
    series = {"factor_oil": _macro(data_dir, "factor_oil"), "factor_usd": _macro(data_dir, "factor_usd"), "us10y": _us10y(data_dir),
              "vnindex_pe": pe}
    out = {"h": h, "horizons": list(HORIZONS), "closes_from": closes[0][0].isoformat() if closes else None,
           "pe": pe_groups(pe, closes, h=h), "lights": [light_groups(k, series, closes, h=h) for k in LIGHTS]}
    from investment_agent.domain.history_stats import history_summary
    out["summary"] = history_summary(out, conditions_now(data_dir, fx="1", today=today)[1])  # by a fixed pattern, no model
    _CACHE.clear() if len(_CACHE) > 16 else None
    _CACHE[key] = (time.monotonic(), out)
    return out
