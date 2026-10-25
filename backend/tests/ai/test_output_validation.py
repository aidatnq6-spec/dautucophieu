import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_agent.ai.payloads import AiPayload
from investment_agent.ai.prompts import load_prompt
from investment_agent.ai.schemas import AnalysisOutput
from investment_agent.ai.tools import ToolBox
from investment_agent.ai.validation import analyze_with_repair, validate_output

NOW = datetime(2026, 10, 25, 11, tzinfo=timezone.utc)
CASES = json.loads((Path(__file__).resolve().parents[3] / "tests/fixtures/ai/evaluation_cases.json").read_text(encoding="utf-8"))

PAYLOAD = AiPayload.model_validate({
    "portfolio": {"holdings": [{"ticker": "FPT", "weight": "0.1000"}], "cash_weight": "0.5000", "risk_group": "growth",
                  "horizon_bucket": "5y_plus", "capacity_flags": [], "data_flags": []},
    "entities": [{"ticker": "FPT", "ratios": {"pe_ttm": "18.2", "pb": "4.1"}, "zone": "between_buy_and_fair"},
                 {"ticker": "VCB", "ratios": {"pe_ttm": "14.0", "pb": "2.3"}, "zone": "above_fair"}],
    "evidence": [{"evidence_id": "doc-1", "kind": "financial_statement", "ticker": "FPT", "source_url": "https://e.vn/1", "excerpt": "LN tăng"},
                 {"evidence_id": "doc-2", "kind": "financial_statement", "ticker": "VCB", "source_url": "https://e.vn/2", "excerpt": "NIM"}]})


def check(output, **kw):
    return validate_output(AnalysisOutput.model_validate(output), PAYLOAD, max_equity_weight=Decimal("0.90"), inputs_as_of=NOW,
                           now=kw.get("now", NOW), max_input_age=timedelta(hours=24))


@pytest.mark.parametrize("case", CASES["cases"], ids=[c["id"] for c in CASES["cases"]])
def test_evaluation_cases(case):
    assert check(case["output"]) == case["expected_issues"]


def test_fixture_is_labelled_synthetic():
    assert CASES["label"] == "synthetic"


def test_stale_inputs_are_flagged():
    good = CASES["cases"][0]["output"]
    assert check(good, now=NOW + timedelta(days=2)) == ["stale_inputs"]


def test_numbers_within_rounding_tolerance_pass():
    out = json.loads(json.dumps(CASES["cases"][0]["output"]))
    out["opportunities"][0]["rationale"] = "P/E khoảng 18,2 lần"
    assert check(out) == []


class Script:
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, messages, tools):
        self.prompts.append(messages)
        return self.replies.pop(0)


def reply(output):
    return {"content": json.dumps(output, ensure_ascii=False), "tool_calls": []}


def run(model):
    return analyze_with_repair(model, PAYLOAD, ToolBox(PAYLOAD), max_equity_weight=Decimal("0.90"), inputs_as_of=NOW, now=NOW,
                               max_input_age=timedelta(hours=24), snapshot_id="snap-1", recommendations={})


def test_valid_output_is_used_without_repair():
    model = Script(reply(CASES["cases"][0]["output"]))
    result = run(model)
    assert result.source == "ai" and result.repair_attempted is False and len(model.prompts) == 1


def test_one_repair_with_issue_codes_only():
    model = Script(reply(CASES["cases"][1]["output"]), reply(CASES["cases"][0]["output"]))
    result = run(model)
    assert result.source == "ai" and result.repair_attempted is True
    repair_note = model.prompts[1][-1]["content"]
    assert "number_mismatch" in repair_note and "9.5" not in repair_note


def test_second_failure_falls_back_to_checked_numbers_without_ai():
    model = Script(reply(CASES["cases"][1]["output"]), reply(CASES["cases"][1]["output"]))
    result = run(model)
    assert result.source == "no_ai" and result.output is None and result.issues == ("number_mismatch",)
    assert "FPT" in result.narrative and "P/E 18.2" in result.narrative
    assert len(model.prompts) == 2  # never a third attempt


def test_unparseable_output_counts_as_failure():
    model = Script({"content": "xin chào", "tool_calls": []}, {"content": "vẫn sai", "tool_calls": []})
    assert run(model).source == "no_ai"


def test_run_record_carries_versions_and_snapshot():
    result = run(Script(reply(CASES["cases"][0]["output"])))
    assert result.record.prompt_version == load_prompt("analysis").version == "analysis-vi-1"
    assert result.record.schema_version == "analysis-output-1" and result.record.snapshot_id == "snap-1"
    assert result.record.latency_ms >= 0


@pytest.mark.parametrize(("field", "text", "expected"), [
    ("summary", "Danh mục ổn; FPT có P/E 18,2 lần.", []),
    ("summary", "FPT đang có P/E 25 lần.", ["number_mismatch"]),
    ("market_view", "Ngân hàng rẻ: VCB P/B 2.3.", []),
    ("market_view", "VCB có P/B 4.1, đắt hơn mặt bằng.", ["number_mismatch"]),
    ("market_view", "Mặt bằng P/E quanh 14 lần.", []),
    ("market_view", "Mặt bằng P/E quanh 9,5 lần.", ["number_mismatch"]),
    ("risks", "Rủi ro định giá: FPT P/E 30.", ["number_mismatch"]),
])
def test_ratio_numbers_in_free_text_must_match_the_pack(field, text, expected):
    out = json.loads(json.dumps(CASES["cases"][0]["output"]))
    out[field] = [text] if field == "risks" else text
    assert check(out) == expected
