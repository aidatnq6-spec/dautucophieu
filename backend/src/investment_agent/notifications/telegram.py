"""Telegram Bot API sendMessage with bounded retries. The token stays in this object only.

Outcomes: sent (message_id), retryable (rate limit or server error after the
retry budget, or connection refused before sending), unknown (timeout or
broken connection after the request may have arrived — never resent
automatically), failed (permanent 4xx such as a removed bot or unknown chat).
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable, Literal

import httpx

from investment_agent.security.redaction import redact

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendOutcome:
    status: Literal["sent", "retryable", "unknown", "failed"]
    message_id: int | None = None
    error: str | None = None


class TelegramSender:
    def __init__(self, token: str, *, client: httpx.Client, sleep: Callable[[float], None] = time.sleep, max_retries: int = 2):
        if not token:
            raise ValueError("bot token missing")
        self._token, self._client, self._sleep, self._retries = token, client, sleep, max_retries

    def __repr__(self):
        return "TelegramSender(token=***)"

    def send(self, chat_id: str, text: str) -> SendOutcome:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        body = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        for attempt in range(self._retries + 1):
            try:
                response = self._client.post(url, json=body, timeout=httpx.Timeout(20, connect=10))
            except httpx.ConnectError as exc:
                log.warning("Telegram unreachable: %s", redact(str(exc), [self._token]))
                return SendOutcome("retryable", error="connect_error")
            except httpx.HTTPError as exc:
                log.warning("Telegram outcome unknown: %s", redact(str(exc), [self._token]))
                return SendOutcome("unknown", error="timeout_or_broken_connection")
            try:
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            except ValueError:
                return SendOutcome("unknown", error="unreadable_response")
            if response.status_code == 200 and data.get("ok"):
                return SendOutcome("sent", message_id=data["result"]["message_id"])
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self._retries:
                    wait = (data.get("parameters") or {}).get("retry_after") or 2 ** attempt
                    self._sleep(wait)
                    continue
                return SendOutcome("retryable", error=f"http_{response.status_code}")
            return SendOutcome("failed", error=f"http_{response.status_code}")
        return SendOutcome("retryable", error="retries_exhausted")
