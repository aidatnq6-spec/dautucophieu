"""Concentration view for the owner: weights of each held ticker and sector on investable capital, flagged above a limit.

Display only: this does not change allocation decisions (the exception policy keeps its own issuer/industry caps).
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

UNCLASSIFIED = "Chưa phân ngành"
_Q4 = Decimal("0.0001")


def _w(value: Decimal, capital: Decimal) -> str:
    return str((value / capital).quantize(_Q4, ROUND_HALF_UP))


def concentration(holdings: list[dict], *, capital: str | None, sectors: dict[str, str], limit: Decimal) -> dict:
    """holdings: [{security_id, market_value (đồng, str or None)}]; capital: investable capital in đồng."""
    base = {"limit": str(limit), "capital": capital, "tickers": [], "sectors": [], "cash": None, "missing_prices": [], "sector_of": dict(sectors)}
    if capital is None or Decimal(capital) <= 0:
        return {**base, "status": "no_capital"}
    cap = Decimal(capital)
    tickers, by_sector, missing = [], defaultdict(lambda: [Decimal(0), []]), []
    for h in holdings:
        sym, raw = h["security_id"], h.get("market_value")
        sector = sectors.get(sym) or UNCLASSIFIED
        if raw is None:
            missing.append(sym)
            tickers.append({"symbol": sym, "sector": sector, "value": None, "weight": None, "over": False})
            continue
        value = Decimal(raw)
        tickers.append({"symbol": sym, "sector": sector, "value": str(value), "weight": _w(value, cap), "over": value > cap * limit})
        by_sector[sector][0] += value
        by_sector[sector][1].append(sym)
    tickers.sort(key=lambda t: Decimal(t["value"]) if t["value"] is not None else Decimal(-1), reverse=True)
    sector_rows = [{"sector": name, "value": str(v), "weight": _w(v, cap), "over": v > cap * limit, "symbols": sorted(syms)}
                   for name, (v, syms) in by_sector.items()]
    sector_rows.sort(key=lambda s: Decimal(s["value"]), reverse=True)
    invested = sum((Decimal(t["value"]) for t in tickers if t["value"] is not None), Decimal(0))
    cash = cap - invested
    return {**base, "status": "ok", "tickers": tickers, "sectors": sector_rows, "missing_prices": missing,
            "cash": {"value": str(cash), "weight": _w(cash, cap)}}


def simulate(view: dict, *, symbol: str, amount: Decimal, sector: str | None) -> dict:
    """What-if: move `amount` đồng from cash into `symbol` (negative = sell). Nothing is recorded."""
    symbol = symbol.upper()
    holdings = [{"security_id": t["symbol"], "market_value": t["value"]} for t in view["tickers"]]
    sectors = dict(view.get("sector_of") or {})
    sectors.update({t["symbol"]: t["sector"] for t in view["tickers"]})
    for h in holdings:
        if h["security_id"] == symbol and h["market_value"] is not None:
            h["market_value"] = str(max(Decimal(0), Decimal(h["market_value"]) + amount))
            break
    else:
        holdings.append({"security_id": symbol, "market_value": str(max(Decimal(0), amount))})
    if sector:
        sectors.setdefault(symbol, sector)
    return concentration([h for h in holdings if h["market_value"] != "0"], capital=view["capital"], sectors=sectors, limit=Decimal(view["limit"]))
