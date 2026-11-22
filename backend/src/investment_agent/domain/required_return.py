"""Lợi suất cần có để đạt đúng hạn (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-tu-do-tai-chinh-thuc-design.md).

The same growth as Mục tiêu dòng tiền thụ động: interest compounded monthly at the yearly rate ÷ 12, contributions at each month's end.
Solved backwards: the yearly rate that reaches the target in n months; at a given rate, the months it takes and the monthly contribution
that reaches it on time. Assumptions held for the whole period; not a forecast, not advice."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CAP = Decimal(50)  # percent per year: beyond it "not feasible with this capital and contribution"
HORIZON_MONTHS = 600


def _future(capital: Decimal, contribution: Decimal, yearly_pct: Decimal, months: int) -> Decimal:
    i = yearly_pct / 100 / 12
    if i == 0:
        return capital + contribution * months
    g = (1 + i) ** months
    return capital * g + contribution * (g - 1) / i


def months_until(target: date, today: date) -> int:
    """Whole months from today to the end of the target year."""
    return (target.year - today.year) * 12 + (12 - today.month)


def required_return(*, capital: Decimal, contribution: Decimal, goal: Decimal, months: int) -> dict:
    """The yearly rate (two decimals) that reaches goal in months: "reached" when already there, "not_feasible" beyond 50%."""
    if capital >= goal:
        return {"rate": None, "status": "reached"}
    if months <= 0:
        return {"rate": None, "status": "no_time"}
    if _future(capital, contribution, CAP, months) < goal:
        return {"rate": None, "status": "not_feasible"}
    lo, hi = Decimal(-20), CAP
    if _future(capital, contribution, lo, months) >= goal:
        return {"rate": format(lo, "f"), "status": "ok"}
    for _ in range(60):
        mid = (lo + hi) / 2
        if _future(capital, contribution, mid, months) >= goal:
            hi = mid
        else:
            lo = mid
    return {"rate": format(hi.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"), "status": "ok"}


def months_at(*, capital: Decimal, contribution: Decimal, goal: Decimal, yearly_pct: Decimal) -> int | None:
    value, months, i = capital, 0, yearly_pct / 100 / 12
    while value < goal and months < HORIZON_MONTHS:
        value = value * (1 + i) + contribution
        months += 1
    return months if value >= goal else None


def contribution_for(*, capital: Decimal, goal: Decimal, yearly_pct: Decimal, months: int) -> Decimal | None:
    """The monthly contribution that reaches goal in months at that rate (0 when capital alone does)."""
    if months <= 0:
        return None
    i = yearly_pct / 100 / 12
    g = (1 + i) ** months
    need = goal - capital * g
    if need <= 0:
        return Decimal(0)
    return (need * i / (g - 1) if i != 0 else need / months).quantize(Decimal(1), ROUND_HALF_UP)


def yearly_growth(first: tuple[date, Decimal], last: tuple[date, Decimal]) -> str | None:
    """Compound growth per year between two dated values, percent with two decimals; None without time between them."""
    years = (last[0] - first[0]).days / 365.25
    if years <= 0 or first[1] <= 0:
        return None
    rate = (float(last[1] / first[1]) ** (1 / years) - 1) * 100
    return format(Decimal(str(rate)).quantize(Decimal("0.01"), ROUND_HALF_UP), "f")
