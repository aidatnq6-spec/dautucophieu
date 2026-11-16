"""Chứng khoán châu Á: Nikkei 225, KOSPI, Shanghai and Hang Seng from VNDirect's public change_prices (no robots.txt), read with the
Brief's snapshot. VNDirect gives the latest move without a session date (its lastUpdated reads "<day> 23:59" whatever the session), so
each figure is shown with the time it was read, never a session day; a price unchanged since an earlier day is said to be not new, and
Nikkei is dated by FRED's NIKKEI225 when the same close is there. data/macro/asia-indices.json keeps the last read."""

import json
import os
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable

CODES = (("NIKKEI225", "Nikkei 225"), ("KOSPI", "KOSPI"), ("SHANGHAI", "Thượng Hải"), ("HANGSENG", "Hang Seng"))
URL = "https://api-finfo.vndirect.com.vn/v4/change_prices?q=code:" + ",".join(c for c, _ in CODES) + "~period:1D&size=10"
FRED_NIKKEI = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NIKKEI225"
FILE = ("macro", "asia-indices.json")


def _plain(v: Decimal) -> str:
    return format(v.normalize(), "f")


def _fred_date(text: str, price: Decimal) -> str | None:
    for line in text.splitlines()[1:]:
        day, _, value = line.partition(",")
        try:
            if value and Decimal(value) == price:
                return day
        except ArithmeticError:
            continue
    return None


def read_asia(data_dir: Path, *, get: Callable[[str], str], now: datetime) -> dict:
    try:
        data = {r["code"]: r for r in json.loads(get(URL)).get("data") or []}
    except Exception:
        return {"status": "missing", "reason": "Không đọc được chỉ số châu Á từ VNDirect"}
    path = Path(data_dir).joinpath(*FILE)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    seen = state.get("seen") or {}
    today = now.date().isoformat()
    rows = []
    for code, name in CODES:
        r = data.get(code)
        if not r or not r.get("price"):
            continue
        price = Decimal(str(r["price"]))
        before = seen.get(code)
        unchanged = before["first_seen"] if before and Decimal(before["price"]) == price and before["first_seen"] < today else None
        if not before or Decimal(before["price"]) != price:
            seen[code] = {"price": _plain(price), "first_seen": today}
        fred = None
        if code == "NIKKEI225":
            try:
                fred = _fred_date(get(FRED_NIKKEI), price)
            except Exception:
                fred = None
        pct = Decimal(str(r.get("changePct") or 0)) / 100
        rows.append({"code": code, "name": name, "price": _plain(price), "change_pct": str(pct.quantize(Decimal("0.0001"), ROUND_HALF_UP)),
                     "unchanged_since": unchanged, "fred_date": fred if fred and fred < today else None})
    if not rows:
        return {"status": "missing", "reason": "VNDirect không có chỉ số châu Á"}
    out = {"status": "ok", "read_at": now.isoformat(), "rows": rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({**out, "seen": seen}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return out


def latest_asia(data_dir: Path) -> dict | None:
    path = Path(data_dir).joinpath(*FILE)
    if not path.is_file():
        return None
    saved = json.loads(path.read_text(encoding="utf-8"))
    return {k: saved[k] for k in ("status", "read_at", "rows") if k in saved}


def _pct(ratio: str) -> str:
    v = Decimal(ratio) * 100
    text = f"{abs(v):.2f}".replace(".", ",")
    return ("+" if v > 0 else "−" if v < 0 else "") + text + "%"


def asia_line(out: dict | None) -> str | None:
    """One line for the brief: each index's last move, flagged when it is not new or dated by FRED."""
    if not out or out.get("status") != "ok":
        return None
    at = datetime.fromisoformat(out["read_at"])
    parts = []
    for r in out["rows"]:
        note = f" (chưa có phiên mới từ {r['unchanged_since'][8:10]}/{r['unchanged_since'][5:7]})" if r["unchanged_since"] else \
            f" (phiên {r['fred_date'][8:10]}/{r['fred_date'][5:7]} theo FRED)" if r["fred_date"] else ""
        parts.append(f"{r['name']} {_pct(r['change_pct'])}{note}")
    return f"Châu Á (VNDirect, đọc {at.strftime('%H:%M %d/%m')}): " + " · ".join(parts)
