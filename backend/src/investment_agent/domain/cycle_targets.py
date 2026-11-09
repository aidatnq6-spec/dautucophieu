"""Tháp tài sản theo chu kỳ: the mix the owner sets for each phase of Mốc chu kỳ lãi suất, against what the layers of Tháp tài sản hold now. The mixes are the
owner's own: nothing is suggested, and Tháp tài sản's own targets are not changed. Personal data; never sent to a model."""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import Field, model_validator

from .models import ContractModel

LAYERS = ("deposit", "bond", "gold", "stocks", "crypto")
_Q4 = Decimal("0.0001")
_Percent = Field(ge=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)


class Mix(ContractModel):
    """Percent of the base (total less the protected reserve), deposits counted with cash as in Tháp tài sản."""
    deposit: Decimal = _Percent
    bond: Decimal = _Percent
    gold: Decimal = _Percent
    stocks: Decimal = _Percent
    crypto: Decimal = _Percent

    @model_validator(mode="after")
    def _whole(self):
        if sum(getattr(self, k) for k in LAYERS) != 100:
            raise ValueError("a mix must come to 100%")
        return self


class CycleTargets(ContractModel):
    up: Mix | None = None
    down: Mix | None = None
    flat: Mix | None = None


def compare_mix(layers: list[dict], *, base: Decimal, mix: Mix) -> list[dict]:
    """layers: Tháp tài sản's. gap: the target less what is held, in đồng: above 0 the layer is short of the mix, below 0 past it. None with no base."""
    amount = {l["id"]: Decimal(l["amount"]) for l in layers}
    out = []
    for layer in LAYERS:
        held = amount.get(layer, Decimal(0)) + (amount.get("cash", Decimal(0)) if layer == "deposit" else 0)
        target = getattr(mix, layer) / 100
        out.append({"id": layer, "held": format(held, "f"), "share": format((held / base).quantize(_Q4, ROUND_HALF_UP), "f") if base > 0 else None,
                    "target": format(target.quantize(_Q4), "f"), "gap": format((target * base - held).quantize(Decimal(1), ROUND_HALF_UP), "f") if base > 0 else None})
    return out
