"""Conservative source coverage audit; fixture evidence never becomes live evidence."""

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from .base import CapabilityState, ProviderCapabilities


@dataclass(frozen=True)
class AuditReport:
    name: str
    entity_id: str
    evidence_kind: str
    eligible: bool
    live_eligible: bool
    gaps: list[str]
    coverage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [f"## {self.name}", f"Entity: `{self.entity_id}`", f"Evidence: {self.evidence_kind}",
                 f"Coverage eligible: {str(self.eligible).lower()}",
                 f"Live eligible: {str(self.live_eligible).lower()}", "", "| Area | Evidence |", "| --- | --- |"]
        for area, value in self.coverage.items():
            lines.append(f"| {area} | {value} |")
        lines.extend(["", "Gaps: " + (", ".join(self.gaps) if self.gaps else "none")])
        return "\n".join(lines)


def _years(start: str, end: str) -> bool:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    try:
        threshold = first.replace(year=first.year + 10)
    except ValueError:  # Leap day
        threshold = first.replace(year=first.year + 10, day=28)
    return last >= threshold


def _periods_contiguous(periods: list[str], count: int, quarterly: bool) -> bool:
    try:
        numbers = [int(p[:4]) * 4 + int(p[5]) - 1 if quarterly else int(p) for p in periods]
        valid = all(len(p) == 6 and p[4] == "Q" and 1 <= int(p[5]) <= 4 for p in periods) if quarterly else all(len(p) == 4 for p in periods)
    except (ValueError, IndexError):
        return False
    distinct = sorted(set(numbers))
    return valid and len(distinct) >= count and all(b - a == 1 for a, b in zip(distinct, distinct[1:]))


def _identity_covers(case: dict[str, Any], start: str, end: str) -> bool:
    segments = sorted(case.get("identity_segments", []), key=lambda row: row["start"])
    if not segments or any(s["entity_id"] != case["entity_id"] for s in segments):
        return False
    if segments[-1]["exchange"] != "HOSE" or segments[-1]["ticker"] != case["current_ticker"]:
        return False
    if segments[0]["start"] > start or segments[-1]["end"] < end:
        return False
    return all(date.fromisoformat(b["start"]).toordinal() <= date.fromisoformat(a["end"]).toordinal() + 1
               for a, b in zip(segments, segments[1:]))


def audit_case(case: dict[str, Any]) -> AuditReport:
    """Assess explicit evidence; absent assertions remain gaps rather than inferred facts."""
    gaps: list[str] = []
    def require(condition: bool, code: str) -> None:
        if not condition:
            gaps.append(code)

    caps = ProviderCapabilities(**{k: CapabilityState(v) for k, v in case.get("capabilities", {}).items()})
    for key, value in asdict(caps).items():
        require(value == CapabilityState.VERIFIED, f"capability_{key}")

    prices = case.get("prices", {})
    financials = case.get("financials", {})
    ratios = case.get("ratios", {})
    actions = case.get("actions", {})
    disclosures = case.get("disclosures", {})
    rights = case.get("rights", {})

    require(case.get("current_exchange") == "HOSE", "current_hose")
    if prices.get("start") and prices.get("end"):
        require(_identity_covers(case, prices["start"], prices["end"]), "entity_continuity")
        require(_years(prices["start"], prices["end"]), "price_years")
    else:
        gaps.extend(["entity_continuity", "price_years"])
    require(prices.get("continuity_verified") is True and not prices.get("gaps"), "price_continuity")
    require(prices.get("raw") is True, "raw_prices")
    require(prices.get("adjusted") is True and bool(prices.get("adjustment_method")), "adjusted_prices")

    require(_periods_contiguous(financials.get("annual_periods", []), 10, False), "annual_periods")
    require(_periods_contiguous(financials.get("quarter_periods", []), 40, True), "quarter_periods")
    for field in ("consolidated", "notes", "revisions"):
        require(financials.get(field) is True, f"financial_{field}")

    for metric in ("pe", "pb"):
        if ratios.get(f"{metric}_start") and ratios.get(f"{metric}_end"):
            require(_years(ratios[f"{metric}_start"], ratios[f"{metric}_end"]), f"{metric}_years")
        else:
            gaps.append(f"{metric}_years")
    require(ratios.get("continuity_verified") is True, "ratio_continuity")
    # An invalid interval is acceptable only when explicitly bounded and explained.
    for interval in ratios.get("invalid_intervals", []):
        require(bool(interval.get("start") and interval.get("end") and interval.get("reason")), "ratio_invalid_interval_unexplained")
    require(actions.get("history_verified") is True, "actions_history")
    require(disclosures.get("published_at_verified") is True, "publication_timestamps")
    require(disclosures.get("historical_revisions") is True, "as_reported_revisions")
    require(rights.get("personal_analysis") == "verified" and bool(rights.get("evidence")), "usage_rights")

    kind = case.get("evidence_kind", "unknown")
    require(kind in {"synthetic", "live"}, "evidence_kind")
    coverage = {"prices": prices, "financials": financials, "ratios": ratios,
                "actions": actions, "publication": disclosures, "rights": rights,
                "capabilities": {k: v.value for k, v in asdict(caps).items()}}
    eligible = not gaps
    return AuditReport(case.get("name", "unnamed"), case["entity_id"], kind,
                       eligible, eligible and kind == "live", gaps, coverage)
