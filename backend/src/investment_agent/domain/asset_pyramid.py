"""Tháp tài sản: the owner's financial assets as layers built from the bottom up, each against a target share of what is left after
the protected reserve. Gold 10–15% (VWA), bonds up to 10%, stocks by risk group, crypto up to 5%, deposits take the remainder.

It describes and flags; it never names a ticker or tells the owner to buy or sell."""

from decimal import ROUND_HALF_UP, Decimal

ORDER = ("reserve", "deposit", "bond", "gold", "stocks", "crypto")  # bottom to top
GOLD, BOND_MAX, CRYPTO_MAX, STOCK_BAND = (Decimal("0.10"), Decimal("0.15")), Decimal("0.10"), Decimal("0.05"), Decimal("0.05")


def _r(value: Decimal) -> str:
    return "0" if value == 0 else str(value.quantize(Decimal("0.01"), ROUND_HALF_UP))


def targets(stock_ratio: Decimal) -> dict[str, tuple[Decimal, Decimal]]:
    """Target share ranges of the base (total less the protected reserve and 12-month needs)."""
    top = stock_ratio + GOLD[1] + BOND_MAX + CRYPTO_MAX
    return {"deposit": (max(Decimal(0), 1 - top), max(Decimal(0), 1 - stock_ratio - GOLD[0])),
            "bond": (Decimal(0), BOND_MAX), "gold": GOLD, "stocks": (max(Decimal(0), stock_ratio - STOCK_BAND), stock_ratio),
            "crypto": (Decimal(0), CRYPTO_MAX)}


def asset_pyramid(amounts: dict[str, Decimal], *, deductions: Decimal, stock_ratio: Decimal) -> dict:
    """amounts: đồng per layer id in ORDER (reserve is the amount set aside). Status per layer: fixed (reserve), short, ok or over;
    gap is how far outside the range, in đồng. A warning names each short layer that sits below a layer already over its target."""
    total = sum(amounts.values(), Decimal(0))
    base = max(total - deductions, Decimal(0))
    ranges = targets(stock_ratio)
    out = []
    for layer in ORDER:
        amount = amounts.get(layer, Decimal(0))
        if layer == "reserve":
            out.append({"id": layer, "amount": format(amount, "f"), "share": None, "target_min": None, "target_max": None,
                        "status": "fixed", "gap": None})
            continue
        low, high = ranges[layer]
        share = amount / base if base > 0 else None
        status, gap = "ok", None
        if share is not None and share < low:
            status, gap = "short", (low * base - amount)
        elif share is not None and share > high:
            status, gap = "over", (amount - high * base)
        out.append({"id": layer, "amount": format(amount, "f"), "share": str(share.quantize(Decimal("0.0001"), ROUND_HALF_UP)) if share is not None else None,
                    "target_min": _r(low), "target_max": _r(high), "status": status,
                    "gap": format(gap.quantize(Decimal(1), ROUND_HALF_UP), "f") if gap is not None else None})
    warnings = []
    for i, layer in enumerate(out):
        if layer["status"] == "short":
            over = [above["id"] for above in out[i + 1:] if above["status"] == "over"]
            if over:
                warnings.append({"short": layer["id"], "over": over})
    return {"total": format(total, "f"), "base": format(base, "f"), "layers": out, "warnings": warnings}
