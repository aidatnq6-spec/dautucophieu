"""Kiểm tra sức chịu đựng: what the page needs to price a shock on the holdings — each held ticker's value at the last stored close,
its beta (VNDirect), its oil and US-dollar relations where they are clear, the deepest past fall of the VN-Index, the owner's own
loss tolerance (survey question 10) and the drawdown threshold. A linear estimate from past relations, never a forecast."""

from decimal import Decimal

from investment_agent.domain.drawdown import max_drawdown
from investment_agent.notifications.render import _num

# Survey question 10: a fall of 100 million that would make the owner cut risk.
TOLERANCE = {"A": ("0.05", "Đến 5 triệu trên 100 triệu"), "B": ("0.10", "Trên 5 đến 10 triệu trên 100 triệu"),
             "C": ("0.20", "Trên 10 đến 20 triệu trên 100 triệu"), "D": (None, "Trên 20 triệu trên 100 triệu")}


def _s(value: Decimal | None) -> str | None:
    return None if value is None else format(value.normalize(), "f")


def _factor(result: dict | None, key: str) -> tuple[str | None, str | None]:
    """The factor's coefficient when the relation is clear, else None with why."""
    if not result or result.get("status") != "ok":
        return None, "Chưa đủ dữ liệu để đo"
    reading = result[key]
    return (reading["beta"], None) if reading["class"] in ("benefit", "hurt") else (None, "Quan hệ không rõ (|t| < 2)")


def _dmy(iso: str) -> str:
    return "/".join(reversed(iso.split("-")))


def stress_inputs(*, shares: dict[str, int], costs: dict[str, Decimal], prices: dict[str, Decimal | None], betas: dict[str, dict],
                  sensitivity: dict[str, dict], index: list, answer10: str | None, threshold: Decimal) -> dict:
    rows = []
    for symbol in sorted(shares, key=lambda s: -(shares[s] * (prices.get(s) or 0))):
        price = prices.get(symbol)
        oil, oil_note = _factor(sensitivity.get(symbol), "oil")
        usd, usd_note = _factor(sensitivity.get(symbol), "usd")
        rows.append({"symbol": symbol, "shares": shares[symbol], "price": _s(price), "value": _s(None if price is None else price * shares[symbol]),
                     "cost": _s(costs.get(symbol)), "beta": (betas.get(symbol) or {}).get("beta"), "oil": oil, "usd": usd,
                     "oil_note": oil_note, "usd_note": usd_note})
    deepest = max_drawdown(index)
    worst = None if deepest is None or Decimal(deepest["depth"]) >= 0 else {"depth": deepest["depth"], "peak": deepest["peak"], "trough": deepest["trough"]}
    presets = [{"id": "vn10", "label": "VN-Index −10%", "market": "-0.10", "oil": "0", "usd": "0"},
               {"id": "vn20", "label": "VN-Index −20%", "market": "-0.20", "oil": "0", "usd": "0"}]
    if worst:
        presets.append({"id": "worst", "label": f"Lặp lại đợt giảm sâu nhất của VN-Index ({_num(Decimal(worst['depth']) * 100, 1)}%, "
                        f"{_dmy(worst['peak'])} → {_dmy(worst['trough'])})", "market": worst["depth"], "oil": "0", "usd": "0"})
    presets += [{"id": "oil30", "label": "Dầu +30%", "market": "0", "oil": "0.30", "usd": "0"},
                {"id": "usd5", "label": "Đồng USD +5%", "market": "0", "oil": "0", "usd": "0.05"}]
    tolerance = None
    if answer10 in TOLERANCE:
        limit, label = TOLERANCE[answer10]
        tolerance = {"answer": answer10, "limit": limit, "label": label}
    return {"rows": rows, "presets": presets, "worst": worst, "tolerance": tolerance, "threshold": str(threshold)}
