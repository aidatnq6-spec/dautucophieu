"""Số liệu vận hành nhập tay: groups of operating figures the owner defines per ticker (sales volume by product, revenue by segment,
domestic and export, market share), entered by month, quarter or year with a source for each period.

A stacked group adds its lines into a total, each line's share of it and the total's change against the same period a year before;
a period missing one line has no total (nothing is filled in). A line group (shares, prices) is shown as entered, never added up.
"""

import re
from decimal import ROUND_HALF_UP, Decimal

PERIODS = {"month": re.compile(r"^(19|20)\d{2}-(0[1-9]|1[0-2])$"), "quarter": re.compile(r"^(19|20)\d{2}-Q[1-4]$"),
           "year": re.compile(r"^(19|20)\d{2}$")}
_Q4 = Decimal("0.0001")


def valid_period(period: str, kind: str) -> bool:
    pattern = PERIODS.get(kind)
    return bool(pattern and pattern.fullmatch(period))


def _prior(period: str) -> str:
    return f"{int(period[:4]) - 1}{period[4:]}"


def _plain(v: Decimal) -> str:
    return format(v.normalize(), "f") if v != 0 else "0"


def _total(group: dict, period: str) -> Decimal | None:
    values = group.get("values", {}).get(period, {})
    if group.get("chart") != "stack" or any(values.get(s) is None for s in group["series"]):
        return None
    return sum((Decimal(values[s]) for s in group["series"]), Decimal(0))


def group_view(group_id: str, group: dict) -> dict:
    rows = []
    for period in sorted(group.get("values", {})):
        values = group["values"][period]
        total = _total(group, period)
        before = _total(group, _prior(period))
        rows.append({"period": period, "values": {s: values[s] for s in group["series"] if values.get(s) is not None},
                     "total": _plain(total) if total is not None else None,
                     "shares": {s: str((Decimal(values[s]) / total).quantize(_Q4, ROUND_HALF_UP)) for s in group["series"]} if total else {},
                     "total_yoy": str((total / before - 1).quantize(_Q4, ROUND_HALF_UP)) if total is not None and before else None,
                     "source": group.get("sources", {}).get(period),
                     "missing": [s for s in group["series"] if values.get(s) is None]})
    return {"id": group_id, "name": group["name"], "unit": group["unit"], "period": group["period"], "series": group["series"],
            "chart": group["chart"], "periods": [r["period"] for r in rows], "rows": rows}
