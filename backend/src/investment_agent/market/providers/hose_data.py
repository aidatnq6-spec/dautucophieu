"""Shares outstanding from HOSE's own public API (api.hsx.vn, the data behind hsx.vn's ticker pages; robots.txt of hsx.vn disallows
nothing, checked 14/11/2026). outStanding counts newly issued shares before their extra listing (SHB: 5,343,703,838 outstanding,
4,594,200,024 listed), which the valuation needs; it can also lag a bonus issue (TCB in 11/2026), so fundamentals.py changes a held
count only when HOSE and VNDirect agree."""

import json
from typing import Callable

STOCK_URL = "https://api.hsx.vn/l/api/v1/1/securities/stock?code={symbol}"


def default_get(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
    response.raise_for_status()
    return response.text


def outstanding(symbol: str, get: Callable[[str], str] = default_get) -> str | None:
    """HOSE's shares outstanding of a listed stock, as a whole number in a string; None when HOSE has no figure."""
    rows = ((json.loads(get(STOCK_URL.format(symbol=symbol.upper()))).get("data") or {}).get("list") or [])
    row = next((r for r in rows if str(r.get("code") or "").upper() == symbol.upper()), None)
    raw = str((row or {}).get("outStanding") or "").replace(",", "").strip()
    return raw if raw.isdigit() and int(raw) > 0 else None
