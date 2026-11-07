"""Kế hoạch năm (ĐHCĐ): the owner's entry of a ticker's revenue and profit plan for a year, with its source, against the year-to-date
sum of VNDirect's quarters.

Plans are in tỷ đồng as the meeting states them; revenue is compared with net revenue, profit with the line the plan names
(LNST hợp nhất, LNST công ty mẹ or LNTT). The sum runs from the first quarter on and stops at the first quarter without that line,
saying which; nothing is filled in or annualised. Newest years first. A year the owner has not entered takes CafeF's plan when
one was read (profit: LNST when given, otherwise LNTT), marked as such; the owner's entry always wins.
"""

from decimal import ROUND_HALF_UP, Decimal

KINDS = {"npat": "LNST", "npat_parent": "LNST công ty mẹ", "pbt": "LNTT"}
_Q4 = Decimal("0.0001")
_TY = Decimal(10**9)


def _plain(v: Decimal) -> str:
    return format(v.quantize(Decimal(1), ROUND_HALF_UP).normalize(), "f") if v != 0 else "0"


def _line(year: str, quarters: dict | None, key: str, label: str, plan: str | None) -> dict | None:
    if plan is None:
        return None
    target = Decimal(plan) * _TY
    base = {"actual": None, "plan": _plain(target), "ratio": None}
    if quarters is None:
        return {**base, "reason": "Chưa có số quý VNDirect của mã này"}
    total, last = Decimal(0), 0
    for q in (1, 2, 3, 4):
        value = (quarters.get(f"{year}-Q{q}") or {}).get(key)
        if value is None:
            break
        total += Decimal(value)
        last = q
    if last == 0:
        return {**base, "reason": f"Chưa có số quý 1/{year}"}
    later = any(f"{year}-Q{q}" in quarters for q in range(last + 1, 5))
    reason = f"Thiếu {label} quý {last + 1}/{year}: chỉ cộng tới quý {last}" if later else None
    return {"actual": _plain(total), "plan": base["plan"], "ratio": str((total / target).quantize(_Q4, ROUND_HALF_UP)) if target > 0 else None,
            "reason": reason}


def _from_cafef(c: dict) -> dict:
    kind, profit = ("npat", c.get("npat")) if c.get("npat") else ("pbt", c.get("pbt"))
    day = c.get("read_on") or ""
    return {"revenue": c.get("revenue"), "profit": profit, "profit_kind": kind,
            "source": f"CafeF (Kế hoạch kinh doanh), đọc {day[8:10]}/{day[5:7]}/{day[:4]}" if day else "CafeF (Kế hoạch kinh doanh)"}


def plan_progress(plans: dict, quarters: dict | None, cafef: dict | None = None) -> list[dict]:
    """The owner's plans, and CafeF's for the years the owner has not entered (the owner's entry wins)."""
    merged = {y: (_from_cafef(c), "cafef") for y, c in (cafef or {}).items() if c.get("revenue") or c.get("npat") or c.get("pbt")}
    merged.update({y: (p, "owner") for y, p in plans.items()})
    out = []
    for year in sorted(merged, reverse=True):
        p, origin = merged[year]
        kind = p.get("profit_kind") or "npat"
        seen = [q for q in (1, 2, 3, 4) if quarters and f"{year}-Q{q}" in quarters]
        out.append({"year": year, "origin": origin, "source": p.get("source"), "profit_kind": kind, "profit_label": KINDS[kind],
                    "plan_revenue": p.get("revenue"), "plan_profit": p.get("profit"), "through": f"{year}-Q{seen[-1]}" if seen else None,
                    "revenue": _line(year, quarters, "revenue", "doanh thu thuần", p.get("revenue")),
                    "profit": _line(year, quarters, kind, KINDS[kind], p.get("profit"))})
    return out
