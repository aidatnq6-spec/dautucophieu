"""Checks beyond the schema: numbers match the pack, weights respect policy,
sources and tickers exist, risks are stated, no integrity verdicts, inputs fresh.

Fluent text earns nothing. A failed output gets one repair attempt whose note
carries issue codes only; a second failure yields a narrative built by Python
from checked numbers. An earlier report is never relabelled for a new session.
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from .orchestrator import AnalysisRejected, run_analysis
from .payloads import AiPayload
from .prompts import load_prompt
from .schemas import AnalysisOutput
from .tools import ToolBox

SCHEMA_VERSION = "analysis-output-1"
NUMBER_TOLERANCE = Decimal("0.05")
_RATIO_PATTERNS = {"pe_ttm": re.compile(r"P/E\D{0,15}?(\d+(?:[.,]\d+)?)", re.I), "pb": re.compile(r"P/B\D{0,15}?(\d+(?:[.,]\d+)?)", re.I)}
_SENTENCE = re.compile(r"(?<!\d)[.;!?\n]|[.;!?](?!\d)")
_INTEGRITY = re.compile(r"chính trực|liêm chính|trong sạch|không có vi phạm|minh bạch tuyệt đối|\bintegrity\b", re.I)
ORDER = ("number_mismatch", "allocation_exceeds_policy", "unknown_source", "unknown_ticker", "unsupported_integrity_claim",
         "missing_risk", "stale_inputs")


def validate_output(output: AnalysisOutput, payload: AiPayload, *, max_equity_weight: Decimal, inputs_as_of: datetime, now: datetime,
                    max_input_age: timedelta) -> list[str]:
    issues = set()
    ratios = {e.ticker: e.ratios for e in payload.entities}
    for o in output.opportunities:
        for key, pattern in _RATIO_PATTERNS.items():
            for match in pattern.finditer(o.rationale):
                claimed = Decimal(match.group(1).replace(",", "."))
                actual = ratios.get(o.ticker, {}).get(key)
                if actual is None or abs(claimed - Decimal(actual)) > NUMBER_TOLERANCE:
                    issues.add("number_mismatch")
    for text in (output.summary, output.market_view, *output.risks):
        if _free_text_mismatch(text, ratios):
            issues.add("number_mismatch")
    if sum((o.target_weight or Decimal(0) for o in output.opportunities), Decimal(0)) > max_equity_weight:
        issues.add("allocation_exceeds_policy")
    evidence = {e.evidence_id for e in payload.evidence}
    if not (set(output.source_ids) | {s for o in output.opportunities for s in o.source_ids}) <= evidence:
        issues.add("unknown_source")
    known = set(ratios) | {h.ticker for h in payload.portfolio.holdings}
    if any(o.ticker not in known for o in output.opportunities):
        issues.add("unknown_ticker")
    texts = [output.summary, output.market_view, *output.risks, *(o.rationale for o in output.opportunities)]
    if any(_INTEGRITY.search(t) for t in texts):
        issues.add("unsupported_integrity_claim")
    if not any(r.strip() for r in output.risks):
        issues.add("missing_risk")
    if now - inputs_as_of > max_input_age:
        issues.add("stale_inputs")
    return [code for code in ORDER if code in issues]


def _free_text_mismatch(text: str, ratios: dict) -> bool:
    """A ratio quoted outside a rationale must belong to a ticker named in the same sentence,
    or, when the sentence names none, to some entity in the pack."""
    for sentence in _SENTENCE.split(text):
        named = [t for t in ratios if re.search(r"\b" + re.escape(t) + r"\b", sentence)] or list(ratios)
        for key, pattern in _RATIO_PATTERNS.items():
            for match in pattern.finditer(sentence):
                claimed = Decimal(match.group(1).replace(",", "."))
                actual = [Decimal(ratios[t][key]) for t in named if ratios[t].get(key) is not None]
                if not any(abs(claimed - a) <= NUMBER_TOLERANCE for a in actual):
                    return True
    return False


@dataclass(frozen=True)
class RunRecord:
    prompt_version: str
    schema_version: str
    snapshot_id: str
    latency_ms: int
    models: tuple[str, ...]
    providers: tuple[str | None, ...]
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal


@dataclass(frozen=True)
class AnalysisDraft:
    source: Literal["ai", "no_ai"]
    output: AnalysisOutput | None
    narrative: str | None
    issues: tuple[str, ...]
    repair_attempted: bool
    record: RunRecord


def _attempt(model, payload, tools, note, checks):
    try:
        run = run_analysis(model, payload, tools, extra_instructions=note)
    except AnalysisRejected as exc:
        return None, [exc.code]
    return run.output, validate_output(run.output, payload, **checks)


def no_ai_narrative(payload: AiPayload, recommendations: dict[str, dict]) -> str:
    lines = ["Bản tin số liệu đã kiểm chứng (không dùng nhận định AI cho phiên này)."]
    for e in payload.entities:
        parts = [f"P/E {e.ratios['pe_ttm']}" if "pe_ttm" in e.ratios else "P/E chưa có",
                 f"P/B {e.ratios['pb']}" if "pb" in e.ratios else "P/B chưa có", f"vùng giá: {e.zone or 'chưa có'}"]
        rec = recommendations.get(e.ticker)
        if rec:
            parts.append(f"đề xuất: {rec['action']}")
        lines.append(f"- {e.ticker}: " + ", ".join(parts))
    if payload.portfolio.data_flags:
        lines.append("Dữ liệu thiếu: " + ", ".join(payload.portfolio.data_flags))
    return "\n".join(lines)


def analyze_with_repair(model, payload: AiPayload, tools: ToolBox, *, max_equity_weight: Decimal, inputs_as_of: datetime, now: datetime,
                        max_input_age: timedelta, snapshot_id: str, recommendations: dict[str, dict]) -> AnalysisDraft:
    checks = dict(max_equity_weight=max_equity_weight, inputs_as_of=inputs_as_of, now=now, max_input_age=max_input_age)
    started = time.monotonic()
    output, issues = _attempt(model, payload, tools, None, checks)
    repaired = False
    if issues:
        repaired = True
        note = ("Bản trả lời trước bị từ chối với mã lỗi: " + ", ".join(issues) +
                ". Hãy sửa đúng các lỗi này, chỉ dùng dữ liệu trong gói và trả JSON đúng schema.")
        output, issues = _attempt(model, payload, tools, note, checks)
    completions = getattr(model, "completions", [])
    record = RunRecord(prompt_version=load_prompt("analysis").version, schema_version=SCHEMA_VERSION, snapshot_id=snapshot_id,
                       latency_ms=int((time.monotonic() - started) * 1000), models=tuple(c.model for c in completions),
                       providers=tuple(c.provider for c in completions), prompt_tokens=sum(c.prompt_tokens for c in completions),
                       completion_tokens=sum(c.completion_tokens for c in completions),
                       cost_usd=sum((c.cost_usd for c in completions), Decimal(0)))
    if issues:
        return AnalysisDraft(source="no_ai", output=None, narrative=no_ai_narrative(payload, recommendations), issues=tuple(issues),
                             repair_attempted=repaired, record=record)
    return AnalysisDraft(source="ai", output=output, narrative=None, issues=(), repair_attempted=repaired, record=record)
