"""Lịch sử cổ tức on the ticker page: cash and stock dividends by calendar year of the ex-right date, the payout against the
previous fiscal year's EPS, a three-year cash average, and the trailing-twelve-month yield on today's price.

Only the trailing yield is computed: stored closes are adjusted for later dividends and issues, so a past year's yield on
them would be overstated. A stock dividend without a stated ratio is reported as such, not counted as zero.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

_Q4 = Decimal("0.0001")


def _plain(d: Decimal) -> str:
    return format(d.normalize(), "f")


def dividend_history(record: dict | None, *, price: Decimal | None, today: date) -> dict:
    record = record or {}
    dividends, issues = record.get("dividends") or [], record.get("share_issues") or []
    cash, stock, unknown = defaultdict(Decimal), defaultdict(Decimal), set()
    for d in dividends:
        cash[d["date"][:4]] += Decimal(d["cash"])
    for i in issues:
        if i["kind"] != "bonus":
            continue
        if i.get("ratio") is None:
            unknown.add(i["date"][:4])
        else:
            stock[i["date"][:4]] += Decimal(i["ratio"])
    years_eps = record.get("years") or {}
    rows = []
    for y in sorted(set(cash) | set(stock) | unknown, reverse=True):
        eps = years_eps.get(str(int(y) - 1), {}).get("eps")
        eps_prev = Decimal(eps) if eps else None
        rows.append({"year": y, "cash": _plain(cash[y]) if y in cash else "0",
                     "stock": None if y in unknown else (_plain(stock[y]) if y in stock else "0"),
                     "eps_prev": _plain(eps_prev) if eps_prev else None,
                     "payout": str((cash[y] / eps_prev).quantize(_Q4, ROUND_HALF_UP)) if eps_prev and eps_prev > 0 else None,
                     "stock_note": "Có đợt thưởng hoặc cổ tức cổ phiếu chưa rõ tỷ lệ" if y in unknown else None})
    since = today - timedelta(days=365)
    ttm = sum((Decimal(d["cash"]) for d in dividends if d["date"] > since.isoformat()), Decimal(0))
    recent = [str(y) for y in range(today.year - 3, today.year)]
    avg3 = sum((cash[y] for y in recent), Decimal(0)) / 3
    return {"reason": None if rows else "Chưa có dữ liệu cổ tức", "years": rows,
            "ttm": {"cash": _plain(ttm), "yield": str((ttm / price).quantize(_Q4, ROUND_HALF_UP)) if price else None,
                    "price": _plain(price) if price else None, "since": since.isoformat()},
            "avg3": {"cash": _plain(avg3.quantize(Decimal(1), ROUND_HALF_UP)), "years": recent}}
