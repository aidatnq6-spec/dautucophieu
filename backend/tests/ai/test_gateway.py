import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest

from investment_agent.ai.budget import BudgetError, SpendLedger
from investment_agent.ai.catalog import parse_catalog
from investment_agent.ai.openrouter import AIUnavailable, AiPolicy, OpenRouterGateway, load_ai_policy
from investment_agent.security.redaction import RedactingFilter, redact
from investment_agent.settings import Settings

NOW = datetime(2026, 10, 25, 9, tzinfo=timezone.utc)
KEY = "sk-or-v1-" + "a" * 64
TELEGRAM = "123456789:" + "B" * 35


def catalog_json(**overrides):
    models = [
        {"id": "example/model-a", "pricing": {"prompt": "0.000001", "completion": "0.000002"},
         "supported_parameters": ["tools", "response_format", "max_tokens"], "context_length": 128000},
        {"id": "example/model-b", "pricing": {"prompt": "0.0000005", "completion": "0.000001"},
         "supported_parameters": ["response_format", "max_tokens"], "context_length": 64000},
        {"id": "other/not-allowed", "pricing": {"prompt": "0", "completion": "0"}, "supported_parameters": ["tools", "response_format"],
         "context_length": 1000},
    ]
    for m in models:
        m.update(overrides.get(m["id"], {}))
    return {"data": models}


def policy(monthly="10", **changes):
    data = json.loads(open("config/ai-policy.example.json", encoding="utf-8").read())
    data["budget"]["monthly_usd"] = monthly
    data["status"] = "approved"
    for k, v in changes.items():
        data[k] = v
    return AiPolicy.model_validate(data)


class Recorder:
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []

    def __call__(self, request):
        self.requests.append(json.loads(request.content))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def ok(cost="0.0012", model="example/model-b"):
    return httpx.Response(200, json={"id": "gen-1", "model": model, "provider": "ProviderX",
                                     "choices": [{"message": {"content": "{\"summary\": \"ok\"}"}}],
                                     "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": cost}})


def gateway(tmp_path, recorder, *, key=KEY, pol=None, catalog=None, fetched=NOW):
    transport = httpx.MockTransport(recorder)
    return OpenRouterGateway(Settings(openrouter_api_key=key, telegram_bot_token=None, telegram_chat_id=None),
                             pol or policy(), parse_catalog(catalog or catalog_json(), fetched_at=fetched),
                             SpendLedger(tmp_path / "spend.sqlite"), client=httpx.Client(transport=transport), clock=lambda: NOW,
                             sleep=lambda s: None)


MESSAGES = [{"role": "user", "content": "Tóm tắt thị trường"}]


def test_no_network_without_key_or_budget(tmp_path):
    rec = Recorder()
    with pytest.raises(AIUnavailable) as e1:
        gateway(tmp_path, rec, key=None).complete("brief", MESSAGES, job_id="j1")
    with pytest.raises(AIUnavailable) as e2:
        gateway(tmp_path, rec, pol=policy(monthly="0")).complete("brief", MESSAGES, job_id="j1")
    assert (e1.value.code, e2.value.code) == ("key_missing", "budget_not_configured") and rec.requests == []


def test_unapproved_policy_blocks(tmp_path):
    rec = Recorder()
    with pytest.raises(AIUnavailable) as e:
        gateway(tmp_path, rec, pol=policy(status="example_unapproved")).complete("brief", MESSAGES, job_id="j1")
    assert e.value.code == "policy_not_approved" and rec.requests == []


def test_request_carries_privacy_and_parameter_requirements(tmp_path):
    rec = Recorder(ok(model="example/model-a"))
    result = gateway(tmp_path, rec).complete("brief", MESSAGES, job_id="j1")
    body = rec.requests[0]
    assert body["provider"] == {"data_collection": "deny", "zdr": True, "require_parameters": True}
    assert body["model"] == "example/model-a" and body["max_tokens"] == 2000 and "models" not in body
    assert result.model == "example/model-a" and result.provider == "ProviderX" and result.cost_usd == Decimal("0.0012")


def test_model_missing_required_capability_is_skipped(tmp_path):
    # deep needs tools: model-b lacks it and is not in deep's allowlist anyway; strip tools from model-a
    rec = Recorder()
    cat = catalog_json(**{"example/model-a": {"supported_parameters": ["response_format"]}})
    with pytest.raises(AIUnavailable) as e:
        gateway(tmp_path, rec, catalog=cat).complete("deep", MESSAGES, job_id="j1")
    assert e.value.code == "no_eligible_model" and rec.requests == []


def test_missing_or_stale_price_is_never_free(tmp_path):
    rec = Recorder(ok())
    cat = catalog_json(**{"example/model-a": {"pricing": {"prompt": "", "completion": "0.000002"}}})
    gateway(tmp_path, rec, catalog=cat).complete("brief", MESSAGES, job_id="j1")
    assert rec.requests[0]["model"] == "example/model-b"  # model-a skipped for unknown price
    with pytest.raises(AIUnavailable) as e:
        gateway(tmp_path, Recorder(), fetched=NOW - timedelta(days=8)).complete("brief", MESSAGES, job_id="j1")
    assert e.value.code == "catalog_stale"


def test_fallback_stays_inside_allowlist_and_privacy(tmp_path):
    rec = Recorder(httpx.Response(404, json={"error": {"message": "No endpoints found matching your data policy"}}), ok())
    result = gateway(tmp_path, rec).complete("brief", MESSAGES, job_id="j1")
    assert [r["model"] for r in rec.requests] == ["example/model-a", "example/model-b"]
    assert all(r["provider"]["zdr"] is True for r in rec.requests) and result.model == "example/model-b"


def test_exhausted_allowlist_does_not_downgrade_privacy(tmp_path):
    no_route = httpx.Response(404, json={"error": {"message": "No endpoints found"}})
    rec = Recorder(no_route, httpx.Response(404, json={"error": {"message": "No endpoints found"}}))
    with pytest.raises(AIUnavailable) as e:
        gateway(tmp_path, rec).complete("brief", MESSAGES, job_id="j1")
    assert e.value.code == "no_compliant_route" and len(rec.requests) == 2


def test_rate_limit_retries_are_bounded(tmp_path):
    limited = httpx.Response(429, json={"error": {"message": "rate"}})
    rec = Recorder(limited, limited, limited)
    with pytest.raises(AIUnavailable) as e:
        gateway(tmp_path, rec, pol=policy(tasks={"brief": {"models": ["example/model-b"], "required_parameters": [], "max_tokens": 100}})).complete("brief", MESSAGES, job_id="j1")
    assert e.value.code == "rate_limited" and len(rec.requests) == 3


def test_timeout_marks_spend_uncertain_and_does_not_resend(tmp_path):
    rec = Recorder(httpx.ReadTimeout("slow"))
    gw = gateway(tmp_path, rec)
    with pytest.raises(AIUnavailable) as e:
        gw.complete("brief", MESSAGES, job_id="j1")
    assert e.value.code == "outcome_unknown" and len(rec.requests) == 1
    summary = gw.ledger.summary(NOW)
    assert summary.uncertain_usd > 0 and summary.settled_usd == 0


def test_reservation_counts_until_reconciled_and_no_double_count(tmp_path):
    ledger = SpendLedger(tmp_path / "s.sqlite")
    r = ledger.reserve("j1", Decimal("0.4"), monthly=Decimal("1"), per_request=Decimal("0.5"), per_job=Decimal("2"), now=NOW)
    with pytest.raises(BudgetError):
        ledger.reserve("j1", Decimal("0.7"), monthly=Decimal("1"), per_request=Decimal("0.9"), per_job=Decimal("2"), now=NOW)
    ledger.settle(r, Decimal("0.1"))
    ledger.settle(r, Decimal("0.1"))
    assert ledger.summary(NOW).settled_usd == Decimal("0.1") and ledger.summary(NOW).reserved_usd == 0


def test_per_request_and_per_job_caps(tmp_path):
    ledger = SpendLedger(tmp_path / "s.sqlite")
    with pytest.raises(BudgetError):
        ledger.reserve("j1", Decimal("0.6"), monthly=Decimal("10"), per_request=Decimal("0.5"), per_job=Decimal("2"), now=NOW)
    for _ in range(4):
        ledger.settle(ledger.reserve("j2", Decimal("0.5"), monthly=Decimal("10"), per_request=Decimal("0.5"), per_job=Decimal("2"), now=NOW), Decimal("0.5"))
    with pytest.raises(BudgetError):
        ledger.reserve("j2", Decimal("0.01"), monthly=Decimal("10"), per_request=Decimal("0.5"), per_job=Decimal("2"), now=NOW)


def test_estimate_too_expensive_blocks_before_network(tmp_path):
    rec = Recorder()
    cat = catalog_json(**{"example/model-a": {"pricing": {"prompt": "0.01", "completion": "0.01"}},
                          "example/model-b": {"pricing": {"prompt": "0.01", "completion": "0.01"}}})
    with pytest.raises(AIUnavailable) as e:
        gateway(tmp_path, rec, catalog=cat).complete("brief", MESSAGES, job_id="j1")
    assert e.value.code == "budget_exceeded" and rec.requests == []


def test_redaction_masks_keys_and_telegram_urls():
    text = f"POST https://api.telegram.org/bot{TELEGRAM}/sendMessage failed; Authorization: Bearer {KEY}"
    clean = redact(text, secrets=[KEY, TELEGRAM])
    assert KEY not in clean and TELEGRAM not in clean and "bot***" in clean


def test_logging_filter_redacts_records(caplog):
    logger = logging.getLogger("investment_agent.test")
    logger.addFilter(RedactingFilter([KEY]))
    with caplog.at_level(logging.INFO):
        logger.info("calling with %s", KEY)
    assert KEY not in caplog.text


def test_settings_repr_hides_secrets():
    s = Settings(openrouter_api_key=KEY, telegram_bot_token=TELEGRAM, telegram_chat_id="-100123")
    assert KEY not in repr(s) and TELEGRAM not in repr(s) and s.key_hint() == "…aaaa"


def test_load_policy_from_example_file():
    assert load_ai_policy().status == "example_unapproved"


def test_tools_are_sent_and_tool_calls_returned(tmp_path):
    reply = httpx.Response(200, json={"id": "g", "model": "example/model-a", "choices": [{"message": {"content": None,
        "tool_calls": [{"id": "c1", "function": {"name": "get_evidence", "arguments": "{}"}}]}}], "usage": {"cost": "0.001"}})
    rec = Recorder(reply)
    tools = [{"type": "function", "function": {"name": "get_evidence", "parameters": {"type": "object"}}}]
    result = gateway(tmp_path, rec).complete("deep", MESSAGES, job_id="j1", tools=tools)
    assert rec.requests[0]["tools"] == tools and result.tool_calls[0]["function"]["name"] == "get_evidence" and result.content is None
