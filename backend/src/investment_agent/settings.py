"""Server-side secrets read from the process environment; never logged, never sent to the browser."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str | None = field(default=None, repr=False)
    telegram_bot_token: str | None = field(default=None, repr=False)
    telegram_chat_id: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(os.environ.get("OPENROUTER_API_KEY") or None, os.environ.get("TELEGRAM_BOT_TOKEN") or None,
                   os.environ.get("TELEGRAM_CHAT_ID") or None)

    def key_hint(self) -> str | None:
        """Last four characters only, for status display."""
        return None if not self.openrouter_api_key else "…" + self.openrouter_api_key[-4:]

    def secrets(self) -> list[str]:
        return [s for s in (self.openrouter_api_key, self.telegram_bot_token) if s]
