"""Chuỗi giá trị scored on the stored macro series (moved from api/routes/value_chains.py, 28/11/2026, so the public-data MCP reads it
without the route's watchlist and personal-repository imports). held is the caller's: the MCP always passes an empty set."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.value_chain import factor_status, label, read_indicator, score
from investment_agent.market.leading import MacroStore, load_indicators
from investment_agent.market.value_chains import CHAIN_MAX_AGE_DAYS, COMMODITY_LABELS, COMMODITY_MAX_AGE_DAYS, fingerprint
from investment_agent.services import value_chain_approvals as approvals


def scored_chains(data_dir: Path, config, *, today: date, held: set[str]) -> list[dict]:
    """Each chain with its factors read from the stored macro series, its score and label (None when not approved). A chain is approved
    in the config, or in the app for its current content; an app approval of earlier content shows as stale."""
    indicators = {i["id"]: i for i in load_indicators()}
    store, readings, approved_in_app = MacroStore(data_dir), {}, approvals.read_approvals(data_dir)
    max_age = lambda series: indicators[series]["max_age_days"] if series in indicators else CHAIN_MAX_AGE_DAYS.get(series, COMMODITY_MAX_AGE_DAYS)  # noqa: E731

    def reading(series: str | None) -> dict | None:
        if series is None:
            return None
        if series not in readings:
            points = [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(series)]
            readings[series] = read_indicator(series, points, today=today, max_age_days=max_age(series))
        return readings[series]

    def missing(series: str | None, r: dict | None) -> dict | None:
        """Why a measured factor reads "chưa đánh giá được": no series in the app, no stored figure, a figure past its age, or one figure."""
        if series is None:
            return {"reason": "no_series", "max_age_days": None}
        if r is None:
            return {"reason": "no_data", "max_age_days": max_age(series)}
        if r["stale"]:
            return {"reason": "stale", "max_age_days": max_age(series)}
        if r["direction"] is None:
            return {"reason": "one_point", "max_age_days": max_age(series)}
        return None

    chains = []
    for chain in config.chains:
        factors = []
        for f in chain.factors:
            r = None if f.kind == "event" else reading(f.indicator)
            factors.append({**f.model_dump(mode="json"), "status": "event" if f.kind == "event" else factor_status(f.when_up, r), "reading": r,
                            "missing": None if f.kind == "event" else missing(f.indicator, r),
                            "indicator_label": indicators[f.indicator]["label"] if f.indicator in indicators else COMMODITY_LABELS.get(f.indicator)})
        measured = [(f["weight"], f["status"]) for f in factors if f["status"] != "event"]
        shares = score(measured)
        print_, app = fingerprint(config, chain.id), approved_in_app.get(chain.id)
        if chain.status == "approved":
            approval = {"on": None, "note": None, "by": "config", "stale": False}
        elif app:
            approval = {"on": app["on"], "note": app.get("note"), "by": "app", "stale": app["fingerprint"] != print_}
        else:
            approval = None
        approved = approval is not None and not approval["stale"]
        chains.append({**chain.model_dump(mode="json", exclude={"symbols", "factors"}), "status": "approved" if approved else "draft",
                       "fingerprint": print_, "approval": approval, "factors": factors, "score": shares, "measured": len(measured),
                       # events alone say nothing measurable: too little data, once approved
                       "label": label(shares, approved=approved) if measured else ("insufficient" if approved else None),
                       "symbols": [{"symbol": s, "held": s in held} for s in chain.symbols]})
    return chains
