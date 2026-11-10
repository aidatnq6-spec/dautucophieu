"""Thu chi hằng tháng (`settings/monthly_cashflow`): the months read from the owner's workbook, what they saved, the income paid regularly, and averages
over the last three months already closed. The month being written is shown but kept out of averages. Personal data; never sent to a model."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

RECORD = ("settings", "monthly_cashflow")
AVERAGE_OVER = 3


def merge_import(stored: dict, parsed: dict, *, imported_at: str) -> dict:
    """The year in the file replaces that year's months; other years stay."""
    prefix = f"{parsed['year']:04d}-"
    months = {k: v for k, v in (stored.get("months") or {}).items() if not k.startswith(prefix)} | parsed["months"]
    return {"months": dict(sorted(months.items())), "sources": parsed["sources"], "imported_at": imported_at}


def _passive(stored: dict, month: dict) -> Decimal:
    regular = {s["label"] for s in stored.get("sources") or [] if s.get("passive")}
    return sum((Decimal(v) for k, v in month["sources"].items() if k in regular), Decimal(0))


def closed_months(stored: dict, today: date) -> list[str]:
    now = today.strftime("%Y-%m")
    return [k for k in sorted(stored.get("months") or {}) if k < now][-AVERAGE_OVER:]


def _s(v: Decimal) -> str:
    return format(v.quantize(Decimal(1), ROUND_HALF_UP), "f")


def passive_actual(stored: dict | None, *, today: date) -> str | None:
    """Average income paid regularly over the last closed months; None without any."""
    keys = closed_months(stored or {}, today)
    return _s(sum((_passive(stored, stored["months"][k]) for k in keys), Decimal(0)) / len(keys)) if keys else None


def lifestyle_history(stored: dict | None) -> dict:
    return {k: {"income": v["income"], "expenses": v["spending"]} for k, v in ((stored or {}).get("months") or {}).items()}


def cashflow_view(stored: dict | None, *, today: date, birth_year: int | None) -> dict:
    stored = stored or {}
    now, rows = today.strftime("%Y-%m"), []
    for k, m in sorted((stored.get("months") or {}).items()):
        income, spending = Decimal(m["income"]), Decimal(m["spending"])
        rows.append({"month": k, "income": m["income"], "spending": m["spending"], "saved": _s(income - spending),
                     "rate": format(((income - spending) / income).quantize(Decimal("0.0001"), ROUND_HALF_UP), "f") if income > 0 else None,
                     "passive": _s(_passive(stored, m)), "current": k == now})
    keys = closed_months(stored, today)
    average = None
    if keys:
        picked = [r for r in rows if r["month"] in keys]
        income, spending = sum(Decimal(r["income"]) for r in picked), sum(Decimal(r["spending"]) for r in picked)
        average = {"months": keys, "income": _s(income / len(keys)), "spending": _s(spending / len(keys)), "passive": passive_actual(stored, today=today),
                   "rate": format(((income - spending) / income).quantize(Decimal("0.0001"), ROUND_HALF_UP), "f") if income > 0 else None}
    return {"months": rows, "sources": stored.get("sources") or [], "average": average, "age": today.year - birth_year if birth_year else None,
            "imported_at": stored.get("imported_at")}
