"""Tổng kết năm on Năm tài chính (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md).

Every figure comes from a part the app already has, read for one year: Hiệu suất's monthly returns chained over the year's months,
the ledger replayed at the two year ends (dividends, tax withheld and gains taken are the difference), deposits and withdrawals of the
year, Góp vốn đều's months, Thu chi hằng tháng's closed months, and Tháp tài sản's month-end snapshots. Missing parts are named,
never filled in. Personal data; never sent to a model."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

Q4 = Decimal("0.0001")


def _s(v: Decimal, q: Decimal = Decimal(1)) -> str:
    return format(v.quantize(q, ROUND_HALF_UP), "f")


def _dmy(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def year_portfolio(perf: dict, *, year: int) -> dict:
    """The year's return chained from Hiệu suất's months (deposits and withdrawals already taken out), VN-Index the same way, and the
    portfolio's value at the last session before the year (or the ledger's first session in it) and the last session in it."""
    months = [m for m in perf.get("monthly", []) if m["month"].startswith(f"{year}-")]
    series = perf.get("series", [])
    before = [p for p in series if p["date"] < f"{year}-01-01"]
    within = [p for p in series if p["date"][:4] == str(year)]
    if not months or not within:
        return {"return": None, "vnindex": None, "start": None, "end": None, "note": f"Hiệu suất chưa có phiên nào của năm {year}"}
    prior = [m for m in perf.get("monthly", []) if m["month"] < f"{year}-01"]

    def chain(key: str, level: str) -> str:
        if all(level in m for m in months) and (not prior or level in prior[-1]):  # the unrounded levels: one division, no twelve roundings
            base = Decimal(prior[-1][level]) if prior else Decimal(100)
            return _s(Decimal(months[-1][level]) / base - 1, Q4)
        return _s(_compound([Decimal(m[key]) for m in months]) - 1, Q4)
    start = before[-1] if before else within[0]
    note = None if before else f"sổ giao dịch bắt đầu {_dmy(within[0]['date'])}: tính từ ngày đó"
    return {"return": chain("portfolio", "level"), "vnindex": chain("vnindex", "index_level"), "start": {"date": start["date"], "value": start["value"]},
            "end": {"date": within[-1]["date"], "value": within[-1]["value"]}, "note": note}


def _compound(changes: list[Decimal]) -> Decimal:
    out = Decimal(1)
    for c in changes:
        out *= 1 + c
    return out


def year_flows(events: list, *, year: int) -> dict:
    """Deposits and withdrawals dated in the year; dividends received, tax withheld and gains taken as the ledger at the year's end less
    the ledger at the previous year's end (the same replay as everywhere else, corporate actions included)."""
    from investment_agent.domain.ledger import replay
    end, before = date(year, 12, 31), date(year - 1, 12, 31)
    deposits = sum((Decimal(e.amount) for e in events if e.type == "deposit" and e.effective_at.year == year), Decimal(0))
    withdrawals = sum((Decimal(e.amount) for e in events if e.type == "withdrawal" and e.effective_at.year == year), Decimal(0))
    at = lambda day: replay([e for e in events if e.effective_at <= day])  # noqa: E731
    a, b = at(end), at(before)
    return {"deposits": _s(deposits), "withdrawals": _s(withdrawals), "net": _s(deposits - withdrawals),
            "dividends": _s(Decimal(a.dividend_income) - Decimal(b.dividend_income)),
            "tax_withheld": _s(Decimal(a.dividend_taxes_withheld) - Decimal(b.dividend_taxes_withheld)),
            "realized": _s(Decimal(a.realized_gain) - Decimal(b.realized_gain))}


def year_contributions(status: dict | None, *, amount: str | None, year: int) -> dict | None:
    """Góp vốn đều over the year's months so far (the current month before its day left out): planned (months × the plan's amount),
    put in, months met."""
    if not status or amount is None:
        return None
    months = [m for m in status["months"] if m["month"].startswith(f"{year}-") and m["status"] != "pending"]
    if not months:
        return None
    return {"months": len(months), "met": sum(1 for m in months if m["status"] == "met"),
            "planned": _s(Decimal(amount) * len(months)), "put_in": _s(sum((Decimal(m["net"]) for m in months), Decimal(0)))}


def year_cashflow(stored: dict | None, *, year: int, today: date) -> dict:
    """Thu chi hằng tháng over the year's closed months; months not yet entered are named, never filled in."""
    last = 12 if today.year > year else today.month - 1
    expected = [f"{year}-{m:02d}" for m in range(1, last + 1)]
    have = (stored or {}).get("months") or {}
    got = [k for k in expected if k in have]
    missing = [k for k in expected if k not in have]
    if not got:
        return {"months": 0, "missing": missing, "income": None, "spending": None, "saved": None, "rate": None}
    income = sum((Decimal(have[k]["income"]) for k in got), Decimal(0))
    spending = sum((Decimal(have[k]["spending"]) for k in got), Decimal(0))
    return {"months": len(got), "missing": missing, "income": _s(income), "spending": _s(spending), "saved": _s(income - spending),
            "rate": _s((income - spending) / income, Q4) if income > 0 else None}


def year_tower(snapshots: dict, pyramid: dict | None, *, year: int) -> dict:
    """Tháp tài sản now, and the month-end snapshots that open and close the year when the app has them."""
    first = snapshots.get(f"{year - 1}-12")
    ends = sorted(k for k in snapshots if k.startswith(f"{year}-"))
    last = snapshots[ends[-1]] if ends else None
    note = None if first else (f"không có số đầu năm {year}: phần mềm bắt đầu lưu ảnh chụp cuối tháng từ 11/2026" if year <= 2026
                               else f"không có ảnh chụp tháng 12/{year - 1}")
    layers = [{"id": l["id"], "share": l["share"], "target_min": l["target_min"], "target_max": l["target_max"], "status": l["status"]}
              for l in (pyramid or {}).get("layers", []) if l.get("target_max") is not None]
    return {"start": first, "end": last, "end_month": ends[-1] if ends else None, "now": layers, "note": note}
