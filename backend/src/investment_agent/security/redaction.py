"""Mask secrets in text and log records: known values plus key/URL patterns."""

import logging
import re

_PATTERNS = (
    (re.compile(r"(api\.telegram\.org/bot)[^/\s]+"), r"\1***"),
    (re.compile(r"\bsk-or-[A-Za-z0-9_-]{8,}"), "sk-or-***"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]{8,}=*"), r"\1***"),
    (re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"), "***telegram-token***"),
)


def redact(text: str, secrets: list[str] = ()) -> str:
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        text = text.replace(secret, "***")
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: list[str] = ()):
        super().__init__()
        self.secrets = list(secrets)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage(), self.secrets)
        record.args = ()
        return True
