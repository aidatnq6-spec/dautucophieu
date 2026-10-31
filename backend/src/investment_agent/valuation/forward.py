"""Định giá dự phóng: the owner's growth scenario for the next one to three years turned into forward EPS and book value per
share, priced at the ticker's own monthly P/E and P/B median ± 1, 2, 3 standard deviations. A scenario the owner sets, not
a forecast of the application and not a recommendation.

Base = the latest fiscal year with parent profit and equity, and today's share count (the reference valuation's). A band
whose multiple is not positive, or a loss year for P/E, has no price; missing base figures give a reason, never a guess.
"""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import Field, field_validator, model_validator

from investment_agent.domain.models import ContractModel

BANDS_K = (-3, -2, -1, 0, 1, 2, 3)
_P2, _P4 = Decimal("0.01"), Decimal("0.0001")


def _rate(value: str, low: Decimal, high: Decimal) -> str:
    d = Decimal(value)
    if not d.is_finite() or not low <= d <= high:
        raise ValueError(f"must be between {low} and {high}")
    return format(d.normalize(), "f")


class Assumptions(ContractModel):
    """Yearly rates as decimal strings: profit and equity growth −0.9…3, share dilution 0…1; one to three years, same length."""
    profit_growth: list[str] = Field(min_length=1, max_length=3)
    equity_growth: list[str] = Field(min_length=1, max_length=3)
    dilution: list[str] = Field(min_length=1, max_length=3)

    @field_validator("profit_growth", "equity_growth")
    @classmethod
    def _growth(cls, v):
        return [_rate(x, Decimal("-0.9"), Decimal(3)) for x in v]

    @field_validator("dilution")
    @classmethod
    def _dilution(cls, v):
        return [_rate(x, Decimal(0), Decimal(1)) for x in v]

    @model_validator(mode="after")
    def _same_length(self):
        if not len(self.profit_growth) == len(self.equity_growth) == len(self.dilution):
            raise ValueError("one rate per year for each line")
        return self


def _q(x: Decimal, q: Decimal = _P2) -> str:
    return str(x.quantize(q, ROUND_HALF_UP))


def _bands(per_share: Decimal, band: dict, price: Decimal | None) -> list[dict]:
    if band.get("median") is None or band.get("sd") is None or per_share <= 0:
        return []
    median, sd = Decimal(band["median"]), Decimal(band["sd"])
    out = []
    for k in BANDS_K:
        multiple = median + k * sd
        if multiple <= 0:
            out.append({"k": k, "multiple": None, "price": None, "gap": None})
            continue
        value = per_share * multiple
        out.append({"k": k, "multiple": _q(multiple), "price": _q(value), "gap": _q(value / price - 1, _P4) if price else None})
    return out


def forward_valuation(base: dict, bands: dict, a: Assumptions, *, custom: dict | None = None) -> dict:
    """base: {year, profit, equity, shares, price} (Decimals, price may be None); bands: {pe|pb: {median, sd}} as strings."""
    for key, reason in (("profit", "Chưa có lợi nhuận công ty mẹ năm gần nhất"), ("equity", "Chưa có vốn chủ sở hữu năm gần nhất"),
                        ("shares", "Chưa ước tính được số cổ phiếu")):
        if base.get(key) is None:
            return {"reason": reason, "base": None, "years": [], "notes": []}
    profit, equity, shares, price = base["profit"], base["equity"], base["shares"], base.get("price")
    notes = [f"Chưa đủ lịch sử {name} theo tháng để tính các mức" for key, name in (("pe", "P/E"), ("pb", "P/B"))
             if bands.get(key, {}).get("median") is None or bands.get(key, {}).get("sd") is None]
    years = []
    for i, (gp, ge, dl) in enumerate(zip(a.profit_growth, a.equity_growth, a.dilution), start=1):
        profit, equity, shares = profit * (1 + Decimal(gp)), equity * (1 + Decimal(ge)), shares * (1 + Decimal(dl))
        eps, bvps = profit / shares, equity / shares
        row = {"year": str(int(base["year"]) + i), "eps": _q(eps), "bvps": _q(bvps),
               "pe": _bands(eps, bands.get("pe", {}), price), "pb": _bands(bvps, bands.get("pb", {}), price)}
        if custom:
            row["custom"] = {key: (_q(per * Decimal(custom[key])) if custom.get(key) and per > 0 else None)
                             for key, per in (("pe", eps), ("pb", bvps))}
        years.append(row)
    return {"reason": None, "notes": notes, "years": years,
            "base": {"year": base["year"], "eps": _q(base["profit"] / base["shares"]), "bvps": _q(base["equity"] / base["shares"]),
                     "price": format(price.normalize(), "f") if price is not None else None}}
