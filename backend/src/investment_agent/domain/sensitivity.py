"""Độ nhạy với giá dầu và đồng USD: how a stock's weekly return moved with oil (WTI) and with the broad US dollar index, beyond what
the VN-Index explains, over the last three years. Weekly, so the US and Vietnamese closes and holidays line up. A past relation,
measured locally on public prices; it describes, never recommends."""

import math
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

WEEKS, MIN_WEEKS = 156, 52
T_CLEAR = 2.0  # |t| at or above this counts as a clear relation; below it may be chance

Points = list[tuple[date, Decimal]]


def _weekly(points: Points) -> dict[tuple[int, int], Decimal]:
    """Last close of each ISO week."""
    out: dict[tuple[int, int], Decimal] = {}
    for day, close in sorted(points):
        iso = day.isocalendar()
        out[(iso[0], iso[1])] = Decimal(close)
    return out


def _fit(y: list[float], x1: list[float], x2: list[float]) -> tuple[float, float]:
    """OLS of y on a constant, x1 (the market) and x2 (the factor); the factor's coefficient and its t statistic."""
    n = len(y)
    my, m1, m2 = sum(y) / n, sum(x1) / n, sum(x2) / n
    a = [v - m1 for v in x1]
    b = [v - m2 for v in x2]
    c = [v - my for v in y]
    s11, s22, s12 = sum(v * v for v in a), sum(v * v for v in b), sum(p * q for p, q in zip(a, b))
    s1y, s2y = sum(p * q for p, q in zip(a, c)), sum(p * q for p, q in zip(b, c))
    det = s11 * s22 - s12 * s12
    if det <= 0:
        return 0.0, 0.0
    b1 = (s22 * s1y - s12 * s2y) / det
    b2 = (s11 * s2y - s12 * s1y) / det
    ssr = sum((cy - b1 * p - b2 * q) ** 2 for cy, p, q in zip(c, a, b))
    se = math.sqrt(ssr / (n - 3) * s11 / det) if n > 3 else 0.0
    return b2, (b2 / se if se > 0 else 0.0)


def _reading(beta: float, t: float) -> dict:
    cls = "benefit" if t >= T_CLEAR else "hurt" if t <= -T_CLEAR else "unclear"
    return {"beta": f"{beta:.3f}", "t": f"{t:.1f}", "class": cls}


def sensitivity(stock: Points, *, index: Points, oil: Points, usd: Points) -> dict:
    """Closes (daily or weekly) oldest first. ok: weeks used, and per factor the extra weekly return per unit of factor return
    (0.15 = +1,5% when the factor rises 10%), its t statistic and class; insufficient when under a year of common weeks."""
    series = [_weekly(s) for s in (stock, index, oil, usd)]
    common = sorted(set.intersection(*(set(s) for s in series)))
    returns = [[float(s[w] / s[p] - 1) for p, w in zip(common, common[1:])] for s in series]
    returns = [r[-WEEKS:] for r in returns]
    weeks = len(returns[0])
    if weeks < MIN_WEEKS:
        return {"status": "insufficient", "weeks": weeks}
    y, market, f_oil, f_usd = returns
    return {"status": "ok", "weeks": weeks, "oil": _reading(*_fit(y, market, f_oil)), "usd": _reading(*_fit(y, market, f_usd))}


def _share(part: Decimal, total: Decimal) -> str:
    value = (part / total).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    return "0" if value == 0 else format(value.normalize(), "f")


def exposure(results: dict[str, dict], costs: dict[str, Decimal]) -> dict | None:
    """Share of held cost in tickers that benefit from or are hurt by each factor; None with nothing held."""
    total = sum(costs.values(), Decimal(0))
    if total <= 0:
        return None
    out: dict = {"total": format(total.normalize(), "f")}
    for factor in ("oil", "usd"):
        out[factor] = {cls: _share(sum((c for s, c in costs.items() if (results.get(s) or {}).get(factor, {}).get("class") == cls), Decimal(0)), total)
                       for cls in ("benefit", "hurt")}
    out["insufficient"] = _share(sum((c for s, c in costs.items() if (results.get(s) or {}).get("status") != "ok"), Decimal(0)), total)
    return out
