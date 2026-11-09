"""Đối chiếu định giá: VNDirect's own market value, P/E and P/B for each watched ticker, beside what Bảng số tài chính works out. The two
differ a little by design (share counts, earnings per share); more than a tenth apart is worth a look. Nothing is adjusted to fit."""

import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .leading import _get_with_retry

URL = "https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{symbol}~ratioCode:MARKETCAP,PRICE_TO_EARNINGS,PRICE_TO_BOOK,OUTSTANDING_SHARES~reportDate:gte:{start}&sort=reportDate:desc&size=60"
PROFIT_URL = "https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{symbol}~ratioCode:NET_PROFIT_TR&sort=reportDate:desc&size=1"
CODES = {"MARKETCAP": "market_cap", "PRICE_TO_EARNINGS": "pe", "PRICE_TO_BOOK": "pb", "OUTSTANDING_SHARES": "shares"}
LABELS = {"market_cap": "Vốn hoá", "pe": "P/E", "pb": "P/B"}
LOOKBACK_DAYS = 14
OFF = Decimal("0.10")
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


class ValuationCheckStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol.upper()):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol.upper()}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, symbol: str, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(symbol)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record), encoding="utf-8")
        os.replace(tmp, path)


def _plain(value) -> str | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return format(d.normalize(), "f") if d.is_finite() else None


def parse_latest(text: str, *, today: date) -> dict:
    """{date, market_cap, pe, pb}: each code's newest row dated up to today; a row dated later (VNDirect keeps some at the year's end) is skipped."""
    best: dict[str, tuple[str, str]] = {}
    for row in json.loads(text).get("data") or []:
        key, day, value = CODES.get(row.get("ratioCode")), str(row.get("reportDate", ""))[:10], _plain(row.get("value"))
        # VNDirect keeps the current share count under the year's end: its date says nothing, the others' later rows are not yet real.
        if key and value is not None and (key == "shares" or day <= today.isoformat()) and (key not in best or day > best[key][0]):
            best[key] = (day, value)
    return {"date": max((d for k, (d, _) in best.items() if k != "shares"), default=None), **{k: best[k][1] if k in best else None for k in CODES.values()}}


def _quarter_of(day: str) -> str:
    return f"{day[:4]}-Q{(int(day[5:7]) + 2) // 3}"


def _profit_quarter(text: str) -> str | None:
    """The last quarter in VNDirect's own four-quarter profit, which its P/E rests on."""
    days = [str(r.get("reportDate", ""))[:10] for r in json.loads(text).get("data") or [] if r.get("ratioCode") == "NET_PROFIT_TR"]
    return _quarter_of(max(days)) if days else None


def fetch_checks(store: ValuationCheckStore, symbols: list[str], *, get: Callable[[str], str], today: date, sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    results = {}
    start = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    for symbol in symbols:
        try:
            got = parse_latest(_get_with_retry(get, URL.format(symbol=symbol, start=start), sleep), today=today)
            if got["date"] is None:
                results[symbol] = "error:no_observations"
                continue
            try:
                got["profit_quarter"] = _profit_quarter(_get_with_retry(get, PROFIT_URL.format(symbol=symbol), sleep))
            except Exception:
                got["profit_quarter"] = None  # the comparison then stands as it is
            store.save(symbol, {"fetched_at": datetime.now(timezone.utc).isoformat(), **got})
            results[symbol] = "ok"
        except Exception as exc:
            results[symbol] = f"error:{type(exc).__name__}"
    return results


def _q(period: str) -> str:
    return f"Q{period[-1]}/{period[:4]}"


def compare(ours: dict, theirs: dict | None, *, ttm: dict | None = None) -> dict | None:
    """Each figure beside VNDirect's and how far apart, as a share of VNDirect's; only a figure both sides have can be flagged. VNDirect's
    P/E can rest on four quarters ending earlier than ours: it is then compared on those same quarters, and the note says so."""
    if not theirs:
        return None
    rows = []
    ttm = ttm or {}
    their_q, last_q = theirs.get("profit_quarter"), max(ttm, default=None)
    for key, label in LABELS.items():
        a, b, note = ours.get(key), theirs.get(key), None
        if key == "pe" and their_q and last_q and their_q < last_q and ttm.get(their_q) and ours.get("market_cap") and Decimal(ttm[their_q]) > 0:
            same = (Decimal(ours["market_cap"]) / Decimal(ttm[their_q])).quantize(Decimal("0.01"), ROUND_HALF_UP)
            note = f"VNDirect chưa cập nhật {_q(last_q)}, P/E của họ tính trên 4 quý tới {_q(their_q)}; cùng 4 quý đó phần mềm ra {str(same).replace('.', ',')}x."
            a = str(same)
        diff = None if a is None or b is None or Decimal(b) == 0 else Decimal(a) / Decimal(b) - 1
        shown = ours.get(key)
        rows.append({"key": key, "label": label, "note": note, "ours": shown, "theirs": b, "diff": None if diff is None else str(diff.quantize(Decimal("0.0001"), ROUND_HALF_UP)),
                     "off": diff is not None and abs(diff) > OFF})
    return {"date": theirs.get("date"), "ours_date": ours.get("close_date"), "rows": rows, "flagged": sum(r["off"] for r in rows), "shares_from_vndirect": bool(ours.get("shares_from_vndirect"))}
