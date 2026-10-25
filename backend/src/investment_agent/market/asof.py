"""Point-in-time selection: a revision counts only once it was published.

A date-only disclosure is usable from the next trading session after that
date (00:00 Asia/Ho_Chi_Minh), never the same day. Facts without any
publication time can only appear in the latest-restated view. Synthetic
fixtures keep their synthetic label in either view.
"""

from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from .calendar import TradingCalendar
from .financials import FinancialFact

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def available_from(fact: FinancialFact, cal: TradingCalendar) -> datetime | None:
    if fact.published_at is not None:
        return fact.published_at
    if fact.published_date is None:
        return None
    day = fact.published_date + timedelta(days=1)
    while not cal.is_session(day):
        day += timedelta(days=1)
    return datetime.combine(day, time(0), VN)


def facts_as_of(facts: list[FinancialFact], valuation_time: datetime, cal: TradingCalendar, *,
                mode: Literal["historical_as_reported", "latest_restated"]) -> list[FinancialFact]:
    if valuation_time.tzinfo is None:
        raise ValueError("valuation time requires timezone")
    chosen: dict[tuple, tuple] = {}
    for f in facts:
        if f.period_end > valuation_time.astimezone(VN).date():
            continue
        if mode == "historical_as_reported":
            when = available_from(f, cal)
            if when is None or when > valuation_time or f.provenance_mode == "latest_restated":
                continue
            rank = when
        else:
            rank = available_from(f, cal) or datetime.min.replace(tzinfo=VN)
        key = (f.entity_id, f.metric, f.period_type, f.fiscal_label, f.statement_scope)
        if key not in chosen or (rank, f.revision_id) > chosen[key][0]:
            chosen[key] = ((rank, f.revision_id), f)
    out = [f for _, f in chosen.values()]
    if mode == "latest_restated":
        out = [f if f.provenance_mode == "synthetic" else f.model_copy(update={"provenance_mode": "latest_restated"}) for f in out]
    return sorted(out, key=lambda f: (f.entity_id, f.metric, f.period_end, f.statement_scope))
