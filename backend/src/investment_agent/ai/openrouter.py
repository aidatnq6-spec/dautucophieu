"""OpenRouter chat gateway under an owner-approved policy.

Every request pins one allowlisted model and sends provider preferences
{data_collection: deny, zdr: true, require_parameters: true}; the policy schema
cannot weaken them. Fallback walks the task's allowlist only. A model is
eligible when the catalog is fresh, both prices are known and it supports the
task's required parameters. The worst-case cost is reserved before sending;
a timeout after sending marks the spend uncertain and is not resent.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal

import httpx
from pydantic import Field

from investment_agent.domain.models import ContractModel, UnsignedAmount
from investment_agent.domain.pinned import CONFIG_DIR
from investment_agent.security.redaction import redact
from investment_agent.settings import Settings

from .budget import BudgetError, SpendLedger
from .catalog import Catalog

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
log = logging.getLogger(__name__)


class AIUnavailable(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class ProviderPolicy(ContractModel):
    data_collection: Literal["deny"]
    zdr: Literal[True]
    require_parameters: Literal[True]


class TaskPolicy(ContractModel):
    models: tuple[str, ...] = Field(min_length=1)
    required_parameters: tuple[str, ...]
    max_tokens: int = Field(strict=True, gt=0)


class BudgetPolicy(ContractModel):
    monthly_usd: UnsignedAmount
    per_request_max_usd: UnsignedAmount
    per_job_max_usd: UnsignedAmount
    max_concurrency: int = Field(strict=True, ge=1)
    price_max_age_days: int = Field(strict=True, ge=1)
    on_missing_price: Literal["block"]


class Timeouts(ContractModel):
    connect_seconds: int
    read_seconds: int
    max_retries: int = Field(strict=True, ge=0, le=3)


class AiPolicy(ContractModel):
    version: str
    status: Literal["example_unapproved", "approved"]
    notice: str
    provider: ProviderPolicy
    tasks: dict[str, TaskPolicy]
    budget: BudgetPolicy
    timeouts: Timeouts


def load_ai_policy(path: Path = CONFIG_DIR / "ai-policy.example.json") -> AiPolicy:
    return AiPolicy.model_validate(json.loads(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Completion:
    model: str
    provider: str | None
    content: str | None
    tool_calls: tuple[dict, ...]
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    cost_basis: Literal["reported", "estimated"]
    generation_id: str | None
    policy_version: str


class OpenRouterGateway:
    def __init__(self, settings: Settings, policy: AiPolicy, catalog: Catalog, ledger: SpendLedger, *, client: httpx.Client,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc), sleep: Callable[[float], None] = time.sleep):
        self.settings, self.policy, self.catalog, self.ledger = settings, policy, catalog, ledger
        self.client, self.clock, self.sleep = client, clock, sleep

    def _eligible(self, task: TaskPolicy):
        for model_id in task.models:
            m = self.catalog.models.get(model_id)
            if m and m.prompt_price is not None and m.completion_price is not None and set(task.required_parameters) <= m.supported_parameters:
                yield m

    def complete(self, task_name: str, messages: list[dict], *, job_id: str, response_format: dict | None = None,
                 tools: list[dict] | None = None) -> Completion:
        if not self.settings.openrouter_api_key:
            raise AIUnavailable("key_missing")
        if self.policy.status != "approved":
            raise AIUnavailable("policy_not_approved")
        budget = self.policy.budget
        if budget.monthly_usd <= 0:
            raise AIUnavailable("budget_not_configured")
        now = self.clock()
        if now - self.catalog.fetched_at > timedelta(days=budget.price_max_age_days):
            raise AIUnavailable("catalog_stale")
        task = self.policy.tasks.get(task_name)
        if task is None:
            raise AIUnavailable("unknown_task")
        candidates = list(self._eligible(task))
        if not candidates:
            raise AIUnavailable("no_eligible_model")
        # Conservative prompt estimate: one token per two characters of serialised messages.
        prompt_estimate = len(json.dumps(messages, ensure_ascii=False)) // 2 + 1
        last = "no_compliant_route"
        for model in candidates:
            estimate = prompt_estimate * model.prompt_price + task.max_tokens * model.completion_price
            try:
                rid = self.ledger.reserve(job_id, estimate, monthly=budget.monthly_usd, per_request=budget.per_request_max_usd,
                                          per_job=budget.per_job_max_usd, now=now, max_concurrency=budget.max_concurrency)
            except BudgetError as exc:
                # Only the monthly cap means the budget is gone; a too-large request or job is that request's problem.
                last = {"monthly_cap": "budget_exceeded", "concurrency_cap": "concurrency_cap"}.get(exc.code, "request_over_budget")
                continue
            body = {"model": model.id, "messages": messages, "max_tokens": task.max_tokens,
                    "provider": self.policy.provider.model_dump(), "usage": {"include": True}}
            if response_format is not None:
                body["response_format"] = response_format
            if tools:
                body["tools"] = tools
            outcome = self._send(body, rid, model, prompt_estimate, task)
            if isinstance(outcome, Completion):
                return outcome
            last = outcome
            if outcome in {"outcome_unknown", "rate_limited"}:
                break
        raise AIUnavailable(last)

    def _send(self, body, rid, model, prompt_estimate, task):
        headers = {"Authorization": f"Bearer {self.settings.openrouter_api_key}"}
        timeout = httpx.Timeout(self.policy.timeouts.read_seconds, connect=self.policy.timeouts.connect_seconds)
        for attempt in range(self.policy.timeouts.max_retries + 1):
            try:
                response = self.client.post(CHAT_URL, json=body, headers=headers, timeout=timeout)
            except httpx.ConnectError:
                self.ledger.release(rid)  # never reached the provider
                return "network_unavailable"
            except httpx.HTTPError as exc:
                self.ledger.mark_uncertain(rid)
                log.warning("OpenRouter outcome unknown: %s", redact(str(exc), self.settings.secrets()))
                return "outcome_unknown"
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.policy.timeouts.max_retries:
                    self.sleep(2 ** attempt)
                    continue
                self.ledger.release(rid)
                return "rate_limited" if response.status_code == 429 else "provider_error"
            if response.status_code != 200:
                self.ledger.release(rid)
                return "no_compliant_route" if response.status_code == 404 else f"http_{response.status_code}"
            try:
                return self._settle(response.json(), rid, model, prompt_estimate, task)
            except (ValueError, KeyError, TypeError, IndexError):
                self.ledger.mark_uncertain(rid)  # charged or not is unknown; keep it counted
                return "outcome_unknown"
        return "rate_limited"

    def _settle(self, data, rid, model, prompt_estimate, task) -> Completion:
        """Parse fully before settling, so a malformed body leaves the spend uncertain rather than settled."""
        message = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        p_tokens, c_tokens = int(usage.get("prompt_tokens") or prompt_estimate), int(usage.get("completion_tokens") or task.max_tokens)
        reported = usage.get("cost")
        if reported is not None:
            cost, basis = Decimal(str(reported)), "reported"
        else:
            cost, basis = p_tokens * model.prompt_price + c_tokens * model.completion_price, "estimated"
        completion = Completion(model=data.get("model", model.id), provider=data.get("provider"), content=message.get("content"),
                                tool_calls=tuple(message.get("tool_calls") or ()), prompt_tokens=p_tokens, completion_tokens=c_tokens,
                                cost_usd=cost, cost_basis=basis, generation_id=data.get("id"), policy_version=self.policy.version)
        self.ledger.settle(rid, cost)
        return completion
