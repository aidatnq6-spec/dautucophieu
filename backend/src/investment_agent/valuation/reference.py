"""Reference valuation: several sector-appropriate methods per ticker from free statement data, for the owner's
"rẻ hay đắt" question. Not a recommendation and not wired to buy zones or the universe.

Historical P/E and P/B use the adjusted year-end close × today's share count over that year's profit or equity,
so bonus issues and splits do not distort them. Shares = latest annual parent profit / basic EPS, times share
issues after that year. A method without enough data returns no value and a reason; fewer than two values
means no verdict.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

UNCLASSIFIED = "Chưa phân ngành"
SECTOR_METHODS = {
    "Ngân hàng": ("pb_history", "justified_pb", "pe_history", "pb_peers"),
    "Dịch vụ tài chính": ("pb_history", "pe_history", "pb_peers"),
    "Bảo hiểm": ("pb_history", "pe_history", "pb_peers"),
    "Bất động sản": ("pb_history", "pe_history"),
    "Tài nguyên Cơ bản": ("pe_normalized", "pb_history"),
    "Hóa chất": ("pe_normalized", "pb_history"),
    "Dầu khí": ("pe_normalized", "pb_history"),
}
DEFAULT_METHODS = ("pe_history", "pe_peers", "ddm")
LABELS = {"pe_history": "P/E lịch sử", "pb_history": "P/B lịch sử", "pe_peers": "P/E cùng ngành", "pb_peers": "P/B cùng ngành",
          "justified_pb": "P/B hợp lý theo ROE", "ddm": "Chiết khấu cổ tức", "pe_normalized": "P/E trên lợi nhuận bình quân"}
MIN_YEARS, MIN_PEERS, MIN_PAYING_YEARS = 4, 3, 4


@dataclass(frozen=True)
class Settings:
    required_return: Decimal = Decimal("0.13")
    long_term_growth: Decimal = Decimal("0.05")
    threshold: Decimal = Decimal("0.20")


def _vnd(x: Decimal) -> Decimal:
    return x.quantize(Decimal(1), ROUND_HALF_UP)


def _median(values: list[Decimal]) -> Decimal:
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _d(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def year_end_prices(points, *, today: date) -> dict[int, Decimal]:
    """Last stored close of each finished calendar year, converted from thousand đồng (Vnstock) to đồng."""
    out: dict[int, Decimal] = {}
    for t, close in points:
        if t.year < today.year:
            out[t.year] = Decimal(str(close)) * 1000
    return out


def metrics(record: dict, *, today: date, year_end_prices: dict[int, Decimal]) -> dict | None:
    years, listed = record["years"], _d(record.get("shares_outstanding"))
    annual = [y for y in sorted(years) if _d(years[y].get("npat")) and (_d(years[y].get("eps")) or listed)]
    if not annual:
        return None
    latest_year = annual[-1]
    if _d(years[latest_year].get("eps")):
        shares = _d(years[latest_year]["npat"]) / _d(years[latest_year]["eps"])
        for issue in record.get("issues", []):
            if f"{latest_year}-12-31" < issue["date"] <= today.isoformat():
                shares *= 1 + Decimal(issue["ratio"])
    else:  # no EPS reported (securities firms): the company overview's listed shares, already current
        shares = listed
    shares = shares.quantize(Decimal(1), ROUND_HALF_UP)
    quarters = record["quarters"]
    with_profit = [q for q in sorted(quarters) if _d(quarters[q].get("npat")) is not None]
    with_equity = [q for q in sorted(quarters) if _d(quarters[q].get("equity")) is not None]
    npat_ttm = sum(_d(quarters[q]["npat"]) for q in with_profit[-4:]) if len(with_profit) >= 4 else None
    latest_quarter = with_equity[-1] if with_equity else None
    equity_now = _d(quarters[latest_quarter]["equity"]) if latest_quarter else None
    prev_key = f"{int(latest_quarter[:4]) - 1}{latest_quarter[4:]}" if latest_quarter else None
    equity_prev = _d(quarters.get(prev_key, {}).get("equity")) if prev_key else None
    pe_history, pb_history = {}, {}
    for y in sorted(years):
        price, npat, eq = year_end_prices.get(int(y)), _d(years[y].get("npat")), _d(years[y].get("equity"))
        if price is None:
            continue
        if npat and npat > 0:
            pe_history[int(y)] = price * shares / npat
        if eq and eq > 0:
            pb_history[int(y)] = price * shares / eq
    npats = [_d(years[y]["npat"]) for y in sorted(years) if _d(years[y].get("npat")) is not None]
    divs = record.get("dividends", [])
    # Average cash dividend of the last three full calendar years: payout dates drift by days around a 12-month window.
    recent = range(today.year - 3, today.year)
    dividend_avg3 = sum((Decimal(d["cash"]) for d in divs if int(d["date"][:4]) in recent), Decimal(0)) / len(recent)
    paying = {int(d["date"][:4]) for d in divs if today.year - 5 <= int(d["date"][:4]) <= today.year - 1}
    return {"shares": shares, "eps_ttm": npat_ttm / shares if npat_ttm is not None else None,
            "bvps": equity_now / shares if equity_now is not None else None,
            "roe": npat_ttm / ((equity_now + equity_prev) / 2) if None not in (npat_ttm, equity_now, equity_prev) else None,
            "pe_history": pe_history, "pb_history": pb_history,
            "eps_normalized": (sum(npats) / len(npats)) / shares if npats else None,
            "dividend_avg3": dividend_avg3,
            "paying_years": len(paying), "latest_year": latest_year, "latest_quarter": latest_quarter}


def _result(method, value=None, reason=None, **inputs):
    clean = {k: (str(v.quantize(Decimal("0.0001"), ROUND_HALF_UP)) if isinstance(v, Decimal) else v) for k, v in inputs.items()}
    return {"method": method, "label": LABELS[method], "value": _vnd(value) if value is not None else None, "reason": reason, "inputs": clean}


def _method(name: str, m: dict, peers: dict, s: Settings) -> dict:
    eps, bvps, r, g = m["eps_ttm"], m["bvps"], s.required_return, s.long_term_growth
    if name in ("pe_history", "pe_normalized"):
        base = eps if name == "pe_history" else m["eps_normalized"]
        if len(m["pe_history"]) < MIN_YEARS:
            return _result(name, reason=f"Cần P/E của ít nhất {MIN_YEARS} năm có lãi và có giá cuối năm")
        if not base or base <= 0:
            return _result(name, reason="Lợi nhuận không dương")
        pe = _median(list(m["pe_history"].values()))
        return _result(name, base * pe, eps=base, pe_median=pe, years=len(m["pe_history"]))
    if name == "pb_history":
        if len(m["pb_history"]) < MIN_YEARS:
            return _result(name, reason=f"Cần P/B của ít nhất {MIN_YEARS} năm có giá cuối năm")
        if not bvps or bvps <= 0:
            return _result(name, reason="Vốn chủ sở hữu không dương")
        pb = _median(list(m["pb_history"].values()))
        return _result(name, bvps * pb, bvps=bvps, pb_median=pb, years=len(m["pb_history"]))
    if name in ("pe_peers", "pb_peers"):
        base, ratios = (eps, peers.get("pe", [])) if name == "pe_peers" else (bvps, peers.get("pb", []))
        if len(ratios) < MIN_PEERS:
            return _result(name, reason=f"Cần ít nhất {MIN_PEERS} mã cùng ngành có số liệu")
        if not base or base <= 0:
            return _result(name, reason="Lợi nhuận hoặc vốn chủ sở hữu không dương")
        med = _median(ratios)
        return _result(name, base * med, base=base, peer_median=med, peers=len(ratios))
    if name == "justified_pb":
        roe = m["roe"]
        if roe is None or not bvps or bvps <= 0:
            return _result(name, reason="Thiếu ROE hoặc vốn chủ sở hữu")
        if roe <= g or r <= g:
            return _result(name, reason="ROE không cao hơn tăng trưởng dài hạn")
        pb = (roe - g) / (r - g)
        return _result(name, bvps * pb, bvps=bvps, roe=roe, justified_pb=pb)
    if name == "ddm":
        d = m["dividend_avg3"]
        if m["paying_years"] < MIN_PAYING_YEARS or not d:
            return _result(name, reason=f"Cần trả cổ tức tiền mặt ít nhất {MIN_PAYING_YEARS} trong 5 năm gần nhất")
        if r <= g:
            return _result(name, reason="Lợi suất yêu cầu phải lớn hơn tăng trưởng")
        return _result(name, d * (1 + g) / (r - g), dividend_avg3=d, paying_years=m["paying_years"])
    raise ValueError(name)


def methods_for(names, m: dict, peers: dict, s: Settings) -> list[dict]:
    return [_method(n, m, peers, s) for n in names]


def value_ticker(symbol: str, sector: str | None, m: dict | None, price: Decimal | None, peers: dict, s: Settings) -> dict:
    sector = sector or UNCLASSIFIED
    names = SECTOR_METHODS.get(sector, DEFAULT_METHODS)
    row = {"symbol": symbol, "sector": sector, "price": str(_vnd(price)) if price is not None else None, "fair": None, "low": None,
           "high": None, "gap": None, "verdict": "insufficient", "reason": None, "methods": [],
           "latest_year": m["latest_year"] if m else None, "latest_quarter": m["latest_quarter"] if m else None}
    if m is None:
        return {**row, "reason": "Chưa có báo cáo tài chính"}
    row["methods"] = methods_for(names, m, peers, s)
    values = [x["value"] for x in row["methods"] if x["value"] is not None]
    if len(values) < 2:
        return {**row, "reason": "Ít hơn 2 phương án đủ dữ liệu"}
    fair = _vnd(_median(values))
    row.update(fair=str(fair), low=str(min(values)), high=str(max(values)))
    if price is None:
        return {**row, "reason": "Chưa có giá"}
    gap = price / fair - 1
    verdict = "cheap" if gap <= -s.threshold else "expensive" if gap >= s.threshold else "fair"
    return {**row, "gap": str(gap.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "verdict": verdict}


def reference_board(symbols, *, sectors, records, prices, year_end, settings: Settings, today: date, held: set[str]) -> dict:
    ms = {s: metrics(records[s], today=today, year_end_prices=year_end.get(s, {})) if records.get(s) else None for s in symbols}
    current = {}
    for s, m in ms.items():
        p = prices.get(s)
        if m and p:
            current[s] = {"pe": p / m["eps_ttm"] if m["eps_ttm"] and m["eps_ttm"] > 0 else None,
                          "pb": p / m["bvps"] if m["bvps"] and m["bvps"] > 0 else None}
    rows = []
    for s in symbols:
        sector = sectors.get(s)
        mates = [o for o in symbols if o != s and sector and sectors.get(o) == sector and o in current]
        peers = {k: [current[o][k] for o in mates if current[o][k] is not None] for k in ("pe", "pb")}
        rows.append({**value_ticker(s, sector, ms[s], prices.get(s), peers, settings), "held": s in held})
    return {"as_of": today.isoformat(), "rows": rows,
            "settings": {"required_return": str(settings.required_return), "long_term_growth": str(settings.long_term_growth),
                         "threshold": str(settings.threshold.normalize())}}
