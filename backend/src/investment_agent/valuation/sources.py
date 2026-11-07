"""Where the weekly valuation series takes its profit, equity and publication days from.

A ticker with VNDirect statements (Bảng số tài chính) uses them: parent profit and parent equity (equity less non-controlling
interests; before 2015 those sat outside equity) by quarter from 2010–2015 and by year, so four real quarters replace the annual
stand-ins the eight free Vnstock quarters left. A period counts as out from the day VNDirect listed it when that day falls after
the period ends and within 120 days of it (VNDirect loaded its older figures on 01/12/2019, which is no publication day); otherwise
the fixed rule stays (a quarter 45 days after it ends, a year from 1 April). A listed day later than the rule is kept, so a late
report is not used early. Without VNDirect statements the free Vnstock figures and the fixed rule stay. Today's share count comes
from the reference valuation either way.
"""

from datetime import date, timedelta
from pathlib import Path

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.statements import StatementStore

from .reference import _d, metrics
from .weekly import _QUARTER_END, published_from

LISTED_WITHIN_DAYS = 120


def _end(period: str) -> date:
    if "-Q" not in period:
        return date(int(period), 12, 31)
    return date(int(period[:4]), *_QUARTER_END[int(period[-1])])


def publication_dates(statements: dict):
    listed = {**statements.get("quarters_created", {}), **statements.get("years_created", {})}

    def pub(period: str) -> date:
        day = listed.get(period)
        if day:
            seen, end = date.fromisoformat(day), _end(period)
            if end < seen <= end + timedelta(days=LISTED_WITHIN_DAYS):
                return seen
        return published_from(period)
    return pub


def _parent(f: dict) -> dict[str, str]:
    out = {}
    if f.get("npat_parent") is not None:
        out["npat"] = f["npat_parent"]
    equity = _d(f.get("equity"))
    if equity is not None:
        out["equity"] = format((equity - (_d(f.get("minority_equity")) or 0)).normalize(), "f")
    return out


def valuation_record(data_dir: Path, symbol: str, *, today: date) -> dict:
    fundamentals = FundamentalsStore(Path(data_dir) / "fundamentals").read(symbol)
    m = metrics(fundamentals, today=today, year_end_prices={}) if fundamentals and fundamentals.get("years") else None
    shares = int(m["shares"]) if m else None
    statements = StatementStore(Path(data_dir) / "statements").read(symbol)
    if statements and statements.get("quarters"):
        pick = lambda periods: {p: v for p, v in ((p, _parent(f)) for p, f in sorted(periods.items())) if v}  # noqa: E731
        return {"source": "vndirect", "shares": shares, "published": publication_dates(statements),
                "record": {"quarters": pick(statements.get("quarters", {})), "years": pick(statements.get("years", {}))}}
    return {"source": "vnstock", "shares": shares, "published": None, "record": fundamentals}


def merged_fundamentals(data_dir: Path, symbol: str) -> tuple[dict | None, str | None]:
    """The Vnstock fundamentals record with VNDirect's parent profit and parent equity in place of its own by year and quarter, when
    the ticker has VNDirect statements; Vnstock's EPS of the same year stays (the reference valuation's share count comes from it),
    and dividends, share issues, listed shares and the report-quality lines are kept. Vnstock's record unchanged otherwise."""
    fundamentals = FundamentalsStore(Path(data_dir) / "fundamentals").read(symbol)
    statements = StatementStore(Path(data_dir) / "statements").read(symbol)
    if not statements or not statements.get("quarters"):
        return fundamentals, ("vnstock" if fundamentals else None)
    old_years = (fundamentals or {}).get("years", {})
    years = {}
    for y, f in sorted(statements.get("years", {}).items()):
        figures = _parent(f)
        if figures:
            eps = old_years.get(y, {}).get("eps")
            years[y] = {**figures, **({"eps": eps} if eps is not None else {})}
    quarters = {q: v for q, v in ((q, _parent(f)) for q, f in sorted(statements["quarters"].items())) if v}
    return {**(fundamentals or {"symbol": symbol, "dividends": [], "issues": []}), "years": years, "quarters": quarters}, "vndirect"
