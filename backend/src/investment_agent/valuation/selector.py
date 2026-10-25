"""Choose the valuation model from an issuer's economics, not from its industry tag.

Comparables are a cross-check: each row records its source and how the peer
differs (ROE, growth, risk). Outputs on different bases are never averaged.
"""

from decimal import Decimal

from investment_agent.domain.models import ContractModel, NonemptyId, SignedAmount, UnsignedAmount

CROSS_CHECKS = {
    "residual_income": ("pb_vs_roe_peers", "pe"),
    "nav": ("project_cash_flows", "peers"),
    "cyclical_normalized": ("normalized_multiples",),
    "fcff_dcf": ("pe_peers", "ev_ebitda_peers"),
    "ddm": ("fcff_dcf", "pe"),
}


class IssuerEconomics(ContractModel):
    industry_tag: str
    regulated_deposit_taker: bool
    project_based_assets: bool
    commodity_cyclical: bool
    stable_dividend_capacity: bool
    predictable_free_cash_flow: bool


class ModelChoice(ContractModel):
    primary: str | None
    cross_checks: tuple[str, ...]
    reason: str


def select_model(e: IssuerEconomics) -> ModelChoice:
    for flag, model in (("regulated_deposit_taker", "residual_income"), ("project_based_assets", "nav"),
                        ("commodity_cyclical", "cyclical_normalized"), ("predictable_free_cash_flow", "fcff_dcf"),
                        ("stable_dividend_capacity", "ddm")):
        if getattr(e, flag):
            return ModelChoice(primary=model, cross_checks=CROSS_CHECKS[model], reason=flag)
    return ModelChoice(primary=None, cross_checks=(), reason="no_model_fits_economics")


class Comparable(ContractModel):
    entity_id: NonemptyId
    multiple_name: NonemptyId
    multiple: UnsignedAmount
    source_id: NonemptyId
    roe: SignedAmount
    growth: SignedAmount
    note: str


class CrossCheckRow(ContractModel):
    entity_id: NonemptyId
    multiple_name: NonemptyId
    multiple: UnsignedAmount
    source_id: NonemptyId
    roe_gap: SignedAmount  # peer ROE − subject ROE
    growth: SignedAmount
    note: str


class CrossCheck(ContractModel):
    primary_model: str
    primary_per_share: SignedAmount
    rows: tuple[CrossCheckRow, ...]
    basis_note: str = "Đối chiếu, không bình quân: bội số nhóm tương đồng khác ROE, tăng trưởng và rủi ro."


def cross_check(*, primary_model: str, primary_per_share: Decimal, comparables: list[Comparable], subject_roe: Decimal) -> CrossCheck:
    rows = tuple(CrossCheckRow(entity_id=c.entity_id, multiple_name=c.multiple_name, multiple=format(c.multiple, "f"), source_id=c.source_id,
                               roe_gap=format(c.roe - subject_roe, "f"), growth=format(c.growth, "f"), note=c.note) for c in comparables)
    return CrossCheck(primary_model=primary_model, primary_per_share=format(primary_per_share, "f"), rows=rows)
