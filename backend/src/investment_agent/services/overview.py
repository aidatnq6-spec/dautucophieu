"""Overview composition shared by the HTTP route and scheduled jobs.

Read-only composition of stored personal records with the configured MarketView.
Every number comes from domain functions; missing inputs surface as quality notes
and insufficient-basis recommendations, never as zeros or invented values.
"""

from decimal import Decimal
from zoneinfo import ZoneInfo

from investment_agent.domain.allocation import Position
from investment_agent.domain.market_rules import load_market_rules
from investment_agent.domain.ledger import replay
from investment_agent.domain.profile import ConfirmedProfile, profile_freshness
from investment_agent.domain.recommendations import RecommendationInputs, ValuationSummary, recommend
from investment_agent.domain.settlement import availability
from investment_agent.market.universe import UniverseVersion, research_scope
from investment_agent.valuation.assumptions import ValuationAssumptions
from investment_agent.valuation.dcf import value_assumptions
from investment_agent.repositories.personal import prefetch
from investment_agent.services.records import LedgerBook, StoredRisk, effective_risk, read_current, read_version, trading_settings

VN = ZoneInfo("Asia/Ho_Chi_Minh")
HEADLINES = {"buy_tranche": "Có đề xuất mua từng phần", "reduce": "Cân nhắc giảm tỷ trọng", "hold": "Giữ phân bổ hiện tại",
             "wait": "Chờ thêm điều kiện", "insufficient_basis": "Chưa đủ cơ sở để khuyến nghị"}


def _s(value):
    return None if value is None else format(value, "f")


def _approved_valuation(repo, owner, entity_id):
    head = read_version(repo, owner, "valuation_assumptions", entity_id, None)
    if head is None:
        return None, None
    a = ValuationAssumptions.model_validate(head.payload["assumptions"])
    if a.status == "approved":
        return a, head.version
    version = head.payload.get("last_approved_version")
    if version:
        record = read_version(repo, owner, "valuation_assumptions", entity_id, version)
        return ValuationAssumptions.model_validate(record.payload["assumptions"]), version
    return a, head.version  # draft only


def _summary(entity_id, assumptions, version) -> ValuationSummary:
    if assumptions is None:
        return ValuationSummary(entity_id=entity_id, status="unavailable", buy_zone_active=False, assumption_version=None,
                                per_share={"down": None, "base": None, "up": None}, required_margin=None, tranche_fraction=None, source_ids=())
    result = value_assumptions(assumptions)
    per_share = {k: (_s(v.per_share) if (v := result.scenarios.get(k)) else None) for k in ("down", "base", "up")}
    return ValuationSummary(entity_id=entity_id, status=result.status, buy_zone_active=result.buy_zone_active, assumption_version=version,
                            per_share=per_share, required_margin=_s(assumptions.required_margin), tranche_fraction=_s(assumptions.tranche_fraction),
                            source_ids=assumptions.sources)


# Records every overview needs; read together up front (in parallel) instead of one Firestore round trip at a time.
OVERVIEW_RECORDS = [("profile_versions", "main"), ("risk_versions", "main"), ("ledger_events", "main"), ("approvals", "universe"),
                    ("settings", "trading"), ("settings", "risk_override")]


def _load(repo, owner):
    prefetch(getattr(repo, "authoritative", repo), owner, OVERVIEW_RECORDS)
    profile, profile_stale = read_current(repo, owner, "profile_versions", "main")
    risk, _ = read_current(repo, owner, "risk_versions", "main")
    ledger = read_version(repo, owner, "ledger_events", "main", None)
    universe = read_version(repo, owner, "approvals", "universe", None)
    return profile, profile_stale, risk, ledger, universe


def compose_overview(repo, owner, market, now) -> dict:
    """Raises RepositoryUnavailable; never substitutes missing inputs."""
    profile_rec, profile_stale, risk_rec, ledger_rec, universe_rec = _load(repo, owner)
    book = LedgerBook(ledger_rec)
    events = list(book.effective().events)
    state = replay(events)
    universe = UniverseVersion.model_validate(universe_rec.payload) if universe_rec else None
    profile = ConfirmedProfile.model_validate(profile_rec.payload) if profile_rec else None
    risk = effective_risk(repo, owner, StoredRisk.model_validate(risk_rec.payload).assessment if risk_rec else None)
    capital = profile.assessment if profile else None
    total = capital.investable_capital if capital and capital.status == "ready" else None

    notes, holdings, positions = [], [], []
    held = {h.security_id: h for h in state.positions}
    scope = research_scope(universe, holdings=list(held))
    for h in state.positions:
        point = market.price(h.security_id)
        shares = h.quantity + h.pending_quantity
        value = None if point is None else shares * point.price
        if point is None:
            notes.append(f"price_missing:{h.security_id}")
        else:
            positions.append(Position(issuer_id=h.security_id, control_group_id=None, industry=market.industry(h.security_id), market_value=_s(value)))
        holdings.append({"security_id": h.security_id, "quantity": h.quantity, "pending_quantity": h.pending_quantity, "total_cost": _s(h.total_cost),
                         "average_cost": _s(h.average_cost), "price": _s(point.price) if point else None,
                         "price_date": point.session_date.isoformat() if point else None, "market_value": _s(value),
                         "unrealized_gain": _s(value - h.total_cost) if value is not None else None,
                         "weight_of_capital": _s(value / total) if value is not None and total else None,
                         "scope": scope[h.security_id], "quality_status": "verified" if point else "missing", "blocked_by": list(h.blocked_by)})
    trading = trading_settings(repo, owner)
    setup = {"fee_rate_configured": trading is not None, "profile": profile is not None, "risk": risk is not None, "ledger_version": ledger_rec.version if ledger_rec else 0,
             "universe_version": universe_rec.version if universe_rec else 0, "universe_status": universe.status if universe else None}
    items = []
    if profile is None or risk is None:
        decision = {"action": "insufficient_basis", "headline": HEADLINES["insufficient_basis"], "reasons": ["setup_incomplete"]}
    else:
        freshness = profile_freshness(profile.confirmed_at, now)
        if profile_stale:
            freshness = freshness.model_copy(update={"allows_new_recommendations": False})
        power = availability(events, as_of=now.astimezone(VN).date()) if events else None
        entities = sorted(set(held) | set(universe.members if universe else ()))
        prefetch(getattr(repo, "authoritative", repo), owner, [("valuation_assumptions", e) for e in entities])
        for entity_id in entities:
            assumptions, version = _approved_valuation(repo, owner, entity_id)
            point = market.price(entity_id)
            gaps = [*(["evidence_missing"] if not market.evidence(entity_id) else []),
                    *(["portfolio_price_missing"] if any(n.startswith("price_missing") for n in notes) else []),
                    *(["fee_rate_missing"] if trading is None else [])]
            rec = recommend(RecommendationInputs(
                entity_id=entity_id, industry=market.industry(entity_id), control_group_id=None,
                scope=scope.get(entity_id, "research"), valuation=_summary(entity_id, assumptions, version),
                price=point.price if point else None, price_date=point.session_date if point else None, pb=None,
                analysis_gaps=tuple(gaps), governance_status="not_checked", capital=capital, risk=risk, freshness=freshness,
                holdings=positions, held_quantity=held[entity_id].quantity if entity_id in held else 0,
                buying_power=None if power is None or power.buying_power is None else power.buying_power,
                buying_power_basis=power.buying_power_basis if power else "unknown", fee_rate=trading.fee_rate if trading else Decimal(0), now=now,
                market_rules=load_market_rules()))
            items.append(rec.model_dump(mode="json"))
        actions = [i["action"] for i in items]
        headline = next((a for a in ("buy_tranche", "reduce", "insufficient_basis", "wait") if a in actions), "hold")
        decision = {"action": headline, "headline": HEADLINES[headline],
                    "reasons": sorted({r for i in items if i["action"] == headline for r in i["reasons"]})}
    return {"provenance": market.provenance, "as_of": now.isoformat(), "setup": setup, "decision": decision, "risk_group": risk.group if risk else None,
            "capital": capital.model_dump(mode="json") if capital else None, "ledger": state.model_dump(mode="json"),
            "holdings": holdings, "items": items, "quality_notes": notes,
            "input_versions": {"profile_versions/main": profile_rec.version if profile_rec else 0, "risk_versions/main": risk_rec.version if risk_rec else 0,
                               "ledger_events/main": ledger_rec.version if ledger_rec else 0, "approvals/universe": universe_rec.version if universe_rec else 0}}
