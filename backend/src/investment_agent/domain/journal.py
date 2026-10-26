"""Investment journal: why a decision was made and how it felt, with the market context at that moment.

An entry is never rewritten; later thoughts are appended as notes. A review reminder fires once for each further
`threshold` move of the price away from the price recorded with the entry (up or down)."""

from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import Field

from .models import ContractModel

EMOTIONS = ("calm", "excited", "fomo", "anxious", "panic", "regret")
EMOTION_VI = {"calm": "Bình tĩnh", "excited": "Hào hứng", "fomo": "Sợ bỏ lỡ (FOMO)", "anxious": "Lo lắng", "panic": "Hoảng sợ", "regret": "Tiếc nuối"}


class JournalNote(ContractModel):
    on: date
    text: str = Field(min_length=1, max_length=2000)


class JournalEntry(ContractModel):
    entry_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    symbol: str = Field(pattern=r"^[A-Z0-9]{2,10}$")
    kind: Literal["buy", "sell", "hold"]
    created_on: date
    reason: str = Field(max_length=4000)
    emotion: Literal["calm", "excited", "fomo", "anxious", "panic", "regret"] | None = None
    emotion_note: str = Field(default="", max_length=500)
    context: dict = Field(default_factory=dict)  # price, pe, verdict, macd_d1, rsi_d1, vnindex at the time (each may be missing)
    ledger_event_id: str | None = None
    notes: tuple[JournalNote, ...] = ()
    reviewed_levels: tuple[int, ...] = ()


def add_note(entry: JournalEntry, *, text: str, on: str | date) -> JournalEntry:
    return entry.model_copy(update={"notes": (*entry.notes, JournalNote(on=on, text=text))})


def mark_reviewed(entry: JournalEntry, *, level: int) -> JournalEntry:
    return entry.model_copy(update={"reviewed_levels": tuple(sorted({*entry.reviewed_levels, level}))})


def due_reviews(entries: list[JournalEntry], *, prices: dict[str, Decimal], threshold: Decimal) -> list[dict]:
    """Entries whose price has moved another `threshold` (±) since the last reminder; level = whole steps moved."""
    due = []
    for e in entries:
        recorded, now = e.context.get("price"), prices.get(e.symbol)
        if recorded in (None, "", "0") or now is None:
            continue
        change = Decimal(str(now)) / Decimal(str(recorded)) - 1
        level = int((change / threshold).to_integral_value(rounding=ROUND_DOWN))
        if level != 0 and level not in e.reviewed_levels:
            due.append({"entry": e, "level": level, "change": str(change.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "price": str(now)})
    return due
