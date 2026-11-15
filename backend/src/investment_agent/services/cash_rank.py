"""Kho tiền: the watched non-financial tickers by net cash (cash and short-term investments less borrowing, latest quarter) against
their market value (last close × shares outstanding). Those holding net cash of at least a fifth of their market value are the ones
a higher deposit rate pays most (Chuỗi tác động vĩ mô). Banks, securities firms and insurers borrow and lend as their trade: left
out. A missing figure leaves the ratio blank and says which; nothing is filled in. Public figures only; a reading, not advice."""

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from investment_agent.domain.balance_watch import _cash_like, _debt
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.drawdown import last_close

CASH_RICH = Decimal("0.20")


def _s(v: Decimal | None) -> str | None:
    return format(v, "f") if v is not None else None


def cash_ranking(data_dir: Path) -> list[dict]:
    data_dir = Path(data_dir)
    sectors = load_sectors(data_dir)[0]
    statements, fundamentals = StatementStore(data_dir / "statements"), FundamentalsStore(data_dir / "fundamentals")
    series = SeriesStore(data_dir / "trend-sources")
    rows = []
    for symbol in load_watchlist(data_dir).symbols:
        sector = sectors.get(symbol)
        if kind_of(sector) is not None:
            continue
        quarters = (statements.read(symbol) or {}).get("quarters", {})
        latest = max(quarters) if quarters else None
        like, debt = (_cash_like(quarters[latest]), _debt(quarters[latest])) if latest else (None, None)
        net = like - debt if like is not None and debt is not None else None
        close = last_close(series, symbol)
        points = series.read(f"{symbol}-1d")
        shares = (fundamentals.read(symbol) or {}).get("shares_outstanding")
        cap = (Decimal(close) * Decimal(shares)).quantize(Decimal(1), ROUND_HALF_UP) if close and shares else None
        ratio = (net / cap).quantize(Decimal("0.0001"), ROUND_HALF_UP) if net is not None and cap else None
        missing = "statements" if net is None else "price" if close is None else "shares" if shares is None else None
        rows.append({"symbol": symbol, "sector": sector, "quarter": latest, "cash_like": _s(like), "debt": _s(debt), "net_cash": _s(net),
                     "close": close, "close_date": points[-1][0].date().isoformat() if points else None, "market_cap": _s(cap),
                     "net_cash_to_cap": _s(ratio), "missing": missing})
    order = {s: i for i, s in enumerate(r["symbol"] for r in rows)}
    return sorted(rows, key=lambda r: (r["net_cash_to_cap"] is None, -Decimal(r["net_cash_to_cap"] or 0), order[r["symbol"]]))


def cash_rank_rich(data_dir: Path) -> list[dict]:
    """The cash-rich of cash_ranking, highest ratio first."""
    return [{"symbol": r["symbol"], "net_cash_to_cap": r["net_cash_to_cap"], "quarter": r["quarter"]}
            for r in cash_ranking(data_dir) if r["net_cash_to_cap"] is not None and Decimal(r["net_cash_to_cap"]) >= CASH_RICH]

