"""Vnstock v5 adapter for the owner-approved restricted mode (latest-restated, adjusted prices).

Documented behaviour (vnstocks.com docs, v5.0.1, read 2026-10-25): daily
`Market().equity(sym).ohlcv(...)` returns prices in thousand đồng adjusted for
corporate actions; Community tier keeps about 2,920 days and 8 financial
periods per call; statements carry no publication dates. Data from this
adapter is therefore labelled latest_restated / adjusted and cannot satisfy
as-reported or 10-year requirements. The library is not a project
dependency: the owner installs it (with their key) from vnstocks.com, and it
is imported only when used. Rights to upstream data stay with the owner.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable

from pydantic import ValidationError

from investment_agent.market.prices import PriceBar

THOUSAND = Decimal(1000)
SOURCE = "kbs"  # vnstock docs: kbs matches vnstock_data 3.x; vci adjusts slightly differently


class ProviderUnavailable(RuntimeError):
    pass


class VnstockProvider:
    def __init__(self, *, market=None, fundamental=None, listing=None, company=None,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._market, self._fundamental, self._listing, self._clock = market, fundamental, listing, clock
        self._company = company  # callable symbol -> object with .events(); vnstock Company(source="VCI") when None

    def _api(self):
        if self._market is None or self._fundamental is None:
            try:
                from vnstock import Fundamental, Market
            except ImportError as exc:
                raise ProviderUnavailable("vnstock is not installed; install it from vnstocks.com with your own key") from exc
            self._market, self._fundamental = self._market or Market(), self._fundamental or Fundamental()
        return self._market, self._fundamental

    def _listing_api(self):
        if self._listing is None:
            try:
                from vnstock import Listing
            except ImportError as exc:
                raise ProviderUnavailable("vnstock is not installed; install it from vnstocks.com with your own key") from exc
            self._listing = Listing()
        return self._listing

    def index_members(self, group: str) -> list[str]:
        """Current constituents of an index group (e.g. VN30, VN100) as listed by the source."""
        return sorted({str(s).upper() for s in self._listing_api().symbols_by_group(group)})

    def industry_map(self, symbols: list[str], level: int = 2) -> dict[str, str]:
        """ICB sector names at one level for the given tickers (VCI is the source that serves this listing)."""
        frame = self._listing_api().symbols_by_industries(source="vci")
        wanted = {s.upper() for s in symbols}
        return {str(r["symbol"]).upper(): str(r["icb_name"]) for r in frame.to_dict("records")
                if int(r["icb_level"]) == level and str(r["symbol"]).upper() in wanted}

    def fetch_index(self, symbol: str, start: date, end: date) -> list[PriceBar]:
        """Index levels in points, as published (no corporate-action adjustment applies)."""
        market, _ = self._api()
        frame = market.index(symbol.upper()).ohlcv(start=start.isoformat(), end=end.isoformat(), interval="1D", source=SOURCE)
        return self._bars(frame, symbol.upper(), scale=Decimal(1), currency="POINT", basis="raw")

    def fetch_closes(self, symbol: str, start: date, end: date, *, interval: str, index: bool) -> list[tuple[datetime, str]]:
        """Closes only, for indicators ("1D" or "1H"). Units follow the source (thousand đồng for stocks, points for
        indices); MACD direction/sign and RSI do not depend on the unit."""
        market, _ = self._api()
        handle = market.index(symbol.upper()) if index else market.equity(symbol.upper())
        frame = handle.ohlcv(start=start.isoformat(), end=end.isoformat(), interval=interval)
        out = []
        for row in frame.to_dict("records"):
            try:
                value = Decimal(str(row["close"]))
            except (InvalidOperation, KeyError):
                continue
            if value.is_finite() and value > 0:
                out.append((row["time"].to_pydatetime(), format(value.normalize(), "f")))
        return out

    def fundamentals_frames(self, symbol: str) -> dict:
        """Annual and quarterly income statement and balance sheet rows (long format) plus company events."""
        _, fundamental = self._api()
        eq = fundamental.equity(symbol.upper())
        if self._company is None:
            try:
                from vnstock import Company
            except ImportError as exc:
                raise ProviderUnavailable("vnstock is not installed; install it from vnstocks.com with your own key") from exc
            self._company = lambda sym: Company(source="VCI", symbol=sym)
        frames = {"income_year": eq.income_statement(period="year", format="long"), "balance_year": eq.balance_sheet(period="year", format="long"),
                  "income_quarter": eq.income_statement(period="quarter", format="long"),
                  "balance_quarter": eq.balance_sheet(period="quarter", format="long"), "events": self._company(symbol.upper()).events()}
        return {k: v.to_dict("records") for k, v in frames.items()}

    def fetch_prices(self, symbol: str, start: date, end: date) -> list[PriceBar]:
        market, _ = self._api()
        symbol = symbol.upper()
        frame = market.equity(symbol).ohlcv(start=start.isoformat(), end=end.isoformat(), interval="1D", source=SOURCE, floating=None)
        return self._bars(frame, symbol, scale=THOUSAND, currency="VND", basis="adjusted")

    def _bars(self, frame, symbol: str, *, scale: Decimal, currency: str, basis: str) -> list[PriceBar]:
        observed = self._clock()
        bars = []
        for row in frame.to_dict("records"):
            try:
                values = {k: Decimal(str(row[k])) * scale for k in ("open", "high", "low", "close")}
                if any(not v.is_finite() for v in values.values()):
                    continue
                bar = PriceBar(entity_id=symbol, session_date=row["time"].date(), **{k: format(v.normalize(), "f") for k, v in values.items()},
                               volume=int(row["volume"]), currency=currency, source_id=f"vnstock:{SOURCE}", observed_at=observed,
                               provenance_mode="latest_restated", price_basis=basis)
            except (InvalidOperation, ValidationError, TypeError, ValueError, KeyError):
                continue
            if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close) or bar.low <= 0:
                continue  # inconsistent row: dropped, never repaired or zero-filled
            bars.append(bar)
        return bars

    def statement_rows(self, symbol: str, period: str = "quarter") -> list[dict]:
        _, fundamental = self._api()
        frame = fundamental.equity(symbol.upper()).income_statement(period=period, format="long")
        return frame.to_dict("records")


def audit_symbol(provider: VnstockProvider, symbol: str, *, today: date, years: int = 10) -> dict:
    """Depth check for one symbol against the design requirement; no data is stored."""
    start = date(today.year - years, today.month, today.day)
    bars = provider.fetch_prices(symbol, start, today)
    rows = provider.statement_rows(symbol, period="quarter")
    periods = sorted({str(r.get("period")) for r in rows if r.get("period")})
    first = min((b.session_date for b in bars), default=None)
    return {
        "symbol": symbol.upper(), "checked_on": today.isoformat(), "source": f"vnstock:{SOURCE}",
        "price_rows": len(bars), "first_price_date": first.isoformat() if first else None,
        "meets_10y_prices": first is not None and first <= start + timedelta(days=7),
        "price_basis": "adjusted", "financial_periods": len(periods), "first_period": periods[0] if periods else None,
        "meets_40_quarters": len(periods) >= 40, "line_items": sorted({str(r.get("id")) for r in rows if r.get("id")}),
        "publication_dates": False,
    }
