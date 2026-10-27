"""Tài sản vô hình: money put into oneself (courses, certificates, books) — the base of VWA's asset pyramid — this year, against a
share of yearly income. Counted apart from financial assets."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def intangibles_year(entries: list[dict], *, monthly_income: Decimal | None, target_rate: Decimal, today: date) -> dict:
    """entries: {on (ISO date), amount (đồng; negative lines adjust)}. Target = monthly income × 12 × target_rate %."""
    spent = sum((Decimal(e["amount"]) for e in entries if e["on"][:4] == str(today.year)), Decimal(0))
    target = monthly_income * 12 * target_rate / 100 if monthly_income else None
    progress = spent / target if target else None
    return {"year": today.year, "spent": format(spent, "f"), "target": format(target.quantize(Decimal(1), ROUND_HALF_UP), "f") if target else None,
            "progress": str(progress.quantize(Decimal("0.0001"), ROUND_HALF_UP)) if progress is not None else None}
