"""Quỹ mở: every open-ended fund Fmarket lists, by kind (cổ phiếu, cân bằng, trái phiếu), with Fmarket's returns over set periods
beside VN-Index over the same periods and the 12-month deposit rate; and the owner's own funds (the fund rows of Sổ tài sản) split by
kind at their latest NAV.

Returns are Fmarket's own figures, as percentages; VN-Index's are computed from its stored daily closes (close on or before the day
the period starts), blank when the history does not reach back that far. Nothing is filled in: a fund without a profile yet has no
kind and no returns, and a fund without a NAV is counted at what it cost, with its kind unknown.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .deposit_book import Bond

KINDS = ("STOCK", "BALANCED", "BOND")
PERIODS = {"m12": 1, "m36": 3, "m60": 5}  # years back
FEW_FUNDS = 3
# VN-Index began at 100 in 2000 and has not closed below it since; the stored series before 10/2022 is in thousand points rounded to
# 0.01 (1.47 for about 1,470), too coarse to rescale, so a period starting on such a close stays blank.
INDEX_FLOOR = Decimal(100)


def _s(value: Decimal) -> str:
    return format(value.normalize(), "f") if value != 0 else "0"


def _pct(new: Decimal, old: Decimal) -> str:
    return _s(((new / old - 1) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _years_back(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29/02
        return day.replace(year=day.year - years, day=28)


def index_returns(points: list[tuple[str, str]]) -> dict:
    """VN-Index's change over the year to date and over 1, 3 and 5 years, from (timestamp, close) pairs oldest first."""
    closes = [(date.fromisoformat(t[:10]), Decimal(v)) for t, v in points if v]
    if not closes:
        return {"as_of": None, "ytd": None, **{k: None for k in PERIODS}}
    last_day, last = closes[-1]

    def on_or_before(day: date) -> Decimal | None:
        if closes[0][0] > day:
            return None
        value = next(v for d, v in reversed(closes) if d <= day)
        return value if value >= INDEX_FLOOR else None
    start_ytd = on_or_before(date(last_day.year - 1, 12, 31))
    out = {"as_of": last_day.isoformat(), "ytd": _pct(last, start_ytd) if start_ytd else None}
    for key, years in PERIODS.items():
        start = on_or_before(_years_back(last_day, years))
        out[key] = _pct(last, start) if start else None
    return out


def _order(fund: dict):
    kind = KINDS.index(fund["kind"]) if fund["kind"] in KINDS else len(KINDS)
    m12 = (fund["returns"] or {}).get("m12")
    return kind, m12 is None, -Decimal(m12) if m12 is not None else 0, fund["code"]


RANKED = ("m6", "m12")


def _rank(funds: list[dict]) -> None:
    """Each fund's place among the funds of its kind by its 6- and 12-month return (1 = highest), over the funds that have one.
    run_up (Kiểm tra mua đỉnh): a positive 6-month return in the top quarter of its kind; None without a 6-month return."""
    for fund in funds:
        fund["rank"] = {key: None for key in RANKED}
    for kind in KINDS:
        same = [f for f in funds if f["kind"] == kind]
        for key in RANKED:
            known = sorted((f for f in same if (f["returns"] or {}).get(key) is not None), key=lambda f: -Decimal(f["returns"][key]))
            for place, f in enumerate(known, 1):
                f["rank"][key] = {"rank": place, "of": len(known)}
    for fund in funds:
        r6 = fund["rank"]["m6"]
        fund["run_up"] = None if r6 is None else Decimal(fund["returns"]["m6"]) > 0 and r6["rank"] <= -(-r6["of"] // 4)


def fund_board(navs: dict, profiles: dict, *, index: list[tuple[str, str]], deposit_rate: str | None, held: set[str]) -> dict:
    """navs: market.fund_nav.fund_navs(); profiles: fund_profiles(); index: VN-Index's stored daily closes; held: the owner's fund codes.
    beats_deposit: the fund's 12-month return against the 12-month deposit rate, None when either is missing."""
    funds = []
    for code, nav in navs.items():
        profile = profiles.get(code) or {}
        returns = profile.get("returns")
        m12 = (returns or {}).get("m12")
        funds.append({"code": code, "name": nav["name"], "kind": profile.get("kind"), "manager": profile.get("manager"), "fee": profile.get("fee"),
                      "nav": nav["nav"], "date": nav["date"], "returns": returns, "held": code in held,
                      "beats_deposit": Decimal(m12) > Decimal(deposit_rate) if m12 is not None and deposit_rate is not None else None})
    _rank(funds)
    funds.sort(key=_order)
    counts = {k: sum(1 for f in funds if f["kind"] == k) for k in KINDS}
    return {"funds": funds, "counts": counts, "benchmark": {"vnindex": index_returns(index), "deposit_12m": deposit_rate}}


def composition(bonds: list[Bond] | tuple[Bond, ...], navs: dict, profiles: dict) -> dict:
    """The owner's fund rows by kind: value (units × NAV; cost when the fund has no NAV), share of all their funds, the funds in each.
    notes: "fewer_than_3" (fewer than three funds) and "single_kind" (all in one kind), the two the webinar warns about."""
    values: dict[str, Decimal] = {}
    members: dict[str, set[str]] = {}
    at_cost = set()
    for b in bonds:
        if b.fund is None:
            continue
        nav = navs.get(b.fund)
        kind = (profiles.get(b.fund) or {}).get("kind") if nav else None
        kind = kind if kind in KINDS else "unknown"
        value = (b.units * Decimal(nav["nav"])).quantize(Decimal(1), ROUND_HALF_UP) if nav else b.amount
        if not nav:
            at_cost.add(b.fund)
        values[kind] = values.get(kind, Decimal(0)) + value
        members.setdefault(kind, set()).add(b.fund)
    total = sum(values.values(), Decimal(0))
    order = [*KINDS, "unknown"]
    groups = [{"kind": k, "value": _s(values[k]), "share": _s((values[k] / total).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if total else "0",
               "funds": sorted(members[k])} for k in order if k in values]
    count = len({f for m in members.values() for f in m})
    notes = [n for n, on in (("fewer_than_3", 0 < count < FEW_FUNDS), ("single_kind", len(groups) == 1)) if on]
    return {"groups": groups, "total": _s(total), "fund_count": count, "at_cost": sorted(at_cost), "notes": notes}
