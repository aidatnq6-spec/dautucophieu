"""Conservative source coverage audit; fixture evidence never becomes live evidence."""

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from .base import CapabilityState, ProviderCapabilities


@dataclass(frozen=True)
class AuditReport:
    name: str
    entity_id: str
    current_exchange: str
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
            if isinstance(value, dict):
                brief = {key: f"{len(item)} dated/period rows" if isinstance(item, list) and key.endswith(("sessions", "periods")) else item
                         for key, item in value.items()}
            else:
                brief = value
            lines.append(f"| {area} | {json.dumps(brief, ensure_ascii=False, default=str)} |")
        lines.extend(["", "Gaps: " + (", ".join(self.gaps) if self.gaps else "none")])
        return "\n".join(lines)


@dataclass(frozen=True)
class UniverseAudit:
    target_issuers: int
    distinct_structural_issuers: int
    distinct_eligible_issuers: int
    live_eligible: bool
    gaps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        return (f"## Aggregate target\n\nDistinct synthetic structural HOSE issuers: "
                f"{self.distinct_structural_issuers}\n\nDistinct live eligible HOSE issuers: "
                f"{self.distinct_eligible_issuers}/{self.target_issuers}\n\n"
                f"Live eligible: {str(self.live_eligible).lower()}\n\n"
                f"Gaps: {', '.join(self.gaps) if self.gaps else 'none'}")


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
    return valid and len(numbers) == len(distinct) and len(distinct) >= count and all(b - a == 1 for a, b in zip(distinct, distinct[1:]))


def _period_end(label: str) -> date:
    if len(label) == 4:
        return date(int(label), 12, 31)
    year, quarter = int(label[:4]), int(label[5])
    return date(year, quarter * 3 + 1, 1) - timedelta(days=1) if quarter < 4 else date(year, 12, 31)


def _sessions_match(section: dict[str, Any], as_of: date) -> bool:
    """Compare dated observations with the explicit expected session calendar."""
    try:
        expected = [date.fromisoformat(d) for d in section["expected_sessions"]]
        observed = [date.fromisoformat(d) for d in section["observed_sessions"]]
        start = date.fromisoformat(section["start"])
        end = date.fromisoformat(section["end"])
    except (KeyError, TypeError, ValueError):
        return False
    if section.get("calendar_kind") != "synthetic_weekdays":
        return False
    calendar = []
    day = start
    while day <= as_of:
        if day.weekday() < 5:
            calendar.append(day)
        day += timedelta(days=1)
    return (bool(expected) and len(expected) == len(set(expected))
            and len(observed) == len(set(observed))
            and expected == calendar and set(expected) == set(observed)
            and min(expected) == start and max(expected) == end
            and end <= as_of and _years(start.isoformat(), end.isoformat()))


def _rights_record_valid(rights: dict[str, Any], as_of: date) -> bool:
    evidence = rights.get("evidence")
    if rights.get("personal_analysis") != "verified" or not isinstance(evidence, dict):
        return False
    if not all(isinstance(evidence.get(key), str) and evidence[key].strip()
               for key in ("document_id", "uri", "inspected_at", "scope")):
        return False
    try:
        inspected_at = date.fromisoformat(evidence["inspected_at"])
    except ValueError:
        return False
    return evidence["scope"] == "personal_analysis" and inspected_at <= as_of


def load_fixture_cases(path: Path) -> list[dict[str, Any]]:
    """Expand the compact synthetic weekday schedule into dated sample rows."""
    cases = json.loads(path.read_text(encoding="utf-8"))
    for case in cases:
        schedule = case.pop("fixture_schedule", None)
        if schedule is None:
            continue
        start, end = date.fromisoformat(schedule["start"]), date.fromisoformat(schedule["end"])
        dates = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                dates.append(day.isoformat())
            day += timedelta(days=1)
        case["prices"].update(start=dates[0], end=dates[-1], calendar_kind="synthetic_weekdays",
                              expected_sessions=dates, observed_sessions=dates)
        case["ratios"].update(pe_start=dates[0], pe_end=dates[-1], pb_start=dates[0], pb_end=dates[-1],
                              pe_observed_sessions=dates, pb_observed_sessions=dates)
    return cases


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
    as_of = date.fromisoformat(case["as_of"])

    require(case.get("current_exchange") == "HOSE", "current_hose")
    if prices.get("start") and prices.get("end"):
        require(_identity_covers(case, prices["start"], prices["end"]), "entity_continuity")
        require(_years(prices["start"], prices["end"]), "price_years")
    else:
        gaps.extend(["entity_continuity", "price_years"])
    require(_sessions_match(prices, as_of), "price_continuity")
    require(prices.get("raw") is True, "raw_prices")
    require(prices.get("adjusted") is True and bool(prices.get("adjustment_method")), "adjusted_prices")

    for key, count, quarterly in (("annual_periods", 10, False), ("quarter_periods", 40, True)):
        periods = financials.get(key, [])
        require(_periods_contiguous(periods, count, quarterly)
                and bool(prices.get("start"))
                and all(date.fromisoformat(prices["start"]) <= _period_end(p) <= as_of for p in periods)
                and (max(periods, default=None) == financials.get("latest_expected_quarter" if quarterly else "latest_expected_annual")), key)
    for field in ("consolidated", "notes", "revisions"):
        require(financials.get(field) is True, f"financial_{field}")

    for metric in ("pe", "pb"):
        if ratios.get(f"{metric}_start") and ratios.get(f"{metric}_end"):
            require(_years(ratios[f"{metric}_start"], ratios[f"{metric}_end"]), f"{metric}_years")
        else:
            gaps.append(f"{metric}_years")
        require(_sessions_match({"start": ratios.get(f"{metric}_start"), "end": ratios.get(f"{metric}_end"),
                                 "calendar_kind": prices.get("calendar_kind"),
                                 "expected_sessions": prices.get("expected_sessions"),
                                 "observed_sessions": ratios.get(f"{metric}_observed_sessions")}, as_of), f"{metric}_freshness")
    # An invalid interval is acceptable only when explicitly bounded and explained.
    for interval in ratios.get("invalid_intervals", []):
        try:
            bounded = date.fromisoformat(interval["start"]) <= date.fromisoformat(interval["end"]) <= as_of
        except (KeyError, TypeError, ValueError):
            bounded = False
        require(bounded and bool(interval.get("reason")), "ratio_invalid_interval_unexplained")
    require(actions.get("history_verified") is True, "actions_history")
    require(disclosures.get("published_at_verified") is True, "publication_timestamps")
    require(disclosures.get("historical_revisions") is True, "as_reported_revisions")
    require(_rights_record_valid(rights, as_of), "usage_rights")

    # This entrypoint consumes untrusted fixture/caller data. A future live
    # workflow must supply verified provenance through a separate trusted path.
    kind = "synthetic" if case.get("evidence_kind") == "synthetic" else "unverified"
    if kind != "synthetic":
        gaps.append("live_provenance_unverified")
    coverage = {"prices": prices, "financials": financials, "ratios": ratios,
                "actions": actions, "publication": disclosures, "rights": rights,
                "capabilities": {k: v.value for k, v in asdict(caps).items()}}
    eligible = not gaps
    return AuditReport(case.get("name", "unnamed"), case["entity_id"], case.get("current_exchange", "unknown"), kind,
                       eligible, False, gaps, coverage)


def audit_universe(reports: list[AuditReport], target_issuers: int = 50) -> UniverseAudit:
    structural = {r.entity_id for r in reports if r.eligible and r.current_exchange == "HOSE"}
    # There is no trusted live provenance workflow in Task 4. Caller-created
    # reports must not be able to activate a universe by setting a flag.
    return UniverseAudit(target_issuers, len(structural), 0, False, ["target_50", "live_provenance_unverified"])
