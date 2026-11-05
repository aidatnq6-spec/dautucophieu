"""Vốn dành cho cổ phiếu: the owner's total financial assets (one number, `settings/equity_budget`), less the emergency reserve and
needs due within 12 months from the confirmed profile, times the equity ratio of the risk group. Personal data; never sent to a model."""

from decimal import Decimal

from investment_agent.domain.allocation import load_allocation_policy
from investment_agent.domain.asset_pyramid import asset_pyramid
from investment_agent.domain.deposit_book import totals
from investment_agent.domain.equity_budget import equity_budget
from investment_agent.domain.ledger import replay
from investment_agent.domain.profile import ConfirmedProfile
from investment_agent.services.deposit_book import read_book
from investment_agent.services.records import LedgerBook, StoredRisk, effective_risk, read_current, read_version

RECORD = ("settings", "equity_budget")
LAYERS = ("deposit", "bond", "gold", "crypto")  # entered by hand; stocks (at cost) and ledger cash come from the ledger
PROTECTED = {"emergency_reserve", "due_within_12_months"}


def protected_deductions(repo, owner) -> tuple[Decimal, Decimal, str | None]:
    """(deductions in use, the profile's figure, the figure entered by hand on Hồ sơ & rủi ro or None)."""
    stored = read_version(repo, owner, *RECORD, None)
    profile, _ = read_current(repo, owner, "profile_versions", "main")
    lines = ConfirmedProfile.model_validate(profile.payload).assessment.lines if profile else ()
    from_profile = sum((line.amount for line in lines if line.kind == "deduction" and line.reason in PROTECTED), Decimal(0))
    manual = stored.payload.get("reserve") if stored else None  # replaces the profile figure for this calculation only
    return (Decimal(manual) if manual is not None else from_profile), from_profile, manual


def budget_view(repo, owner) -> tuple[dict, int]:
    """(budget, version of the stored total); raises RepositoryUnavailable."""
    stored = read_version(repo, owner, *RECORD, None)
    if stored is None:
        return {"status": "no_total"}, 0
    risk, _ = read_current(repo, owner, "risk_versions", "main")
    deductions, from_profile, manual = protected_deductions(repo, owner)
    effective = effective_risk(repo, owner, StoredRisk.model_validate(risk.payload).assessment if risk else None)
    group = effective.group if effective else None
    state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    held_cost = sum((p.total_cost for p in state.positions if p.quantity + p.pending_quantity > 0), Decimal(0))
    ratios = dict(load_allocation_policy().baseline_equity)
    layers = stored.payload.get("layers")
    amounts, deposit_source = None, "manual"
    if layers:  # Tháp tài sản: the total is the sum of the layers, with the reserve as the bottom layer
        book, _ = read_book(repo, owner)
        from_book = totals(book) if book else {"deposits": Decimal(0), "accounts": Decimal(0)}
        deposit_source = "book" if book and book.deposits else "manual"  # the sổ replace the hand-entered figure once there is one
        amounts = {"reserve": deductions, "cash": state.cash + from_book["accounts"],
                   "deposit": from_book["deposits"] if deposit_source == "book" else Decimal(layers["deposit"]), "bond": Decimal(layers["bond"]),
                   "gold": Decimal(layers["gold"]), "stocks": held_cost, "crypto": Decimal(layers["crypto"])}
    total = sum(amounts.values(), Decimal(0)) if amounts else Decimal(stored.payload["total"])
    budget = equity_budget(total=total, deductions=deductions, group=group, ratios=ratios, held_cost=held_cost)
    if budget["status"] == "ok":
        pyramid = asset_pyramid(amounts, deductions=deductions, stock_ratio=ratios[group]) if amounts else None
        budget = {**budget, "deductions_source": "manual" if manual is not None else "profile", "profile_deductions": format(from_profile, "f"),
                  "reserve": manual, "layers": layers, "pyramid": pyramid, "deposit_source": deposit_source}
    return budget, stored.version
