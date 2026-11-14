"""Quy trình đầu tư: one card per ticker on five columns (Ý tưởng → Đang nghiên cứu → Chờ vùng giá → Đang nắm → Đã bán). The owner
moves the cards; the day a card entered its column is set by the server. The board checks the cards against the ledger (held
tickers) and the open theses and says where they disagree; it never moves a card by itself."""

import re
from datetime import date

STAGES = ("idea", "research", "waiting", "holding", "sold")
LABELS = {"idea": "Ý tưởng", "research": "Đang nghiên cứu", "waiting": "Chờ vùng giá", "holding": "Đang nắm", "sold": "Đã bán"}
MAX_CARDS = 80
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class BoardError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def merge_cards(stored: list[dict], sent: list[dict], *, today: date) -> list[dict]:
    """The cards to keep: as sent (checked), each with the day it entered its column — kept when its column did not change."""
    if len(sent) > MAX_CARDS:
        raise BoardError("too_many_cards", f"Tối đa {MAX_CARDS} thẻ.")
    before = {c["id"]: c for c in stored}
    out, symbols = [], set()
    for raw in sent:
        card_id, symbol, stage = str(raw.get("id") or ""), str(raw.get("symbol") or "").strip().upper(), raw.get("stage")
        if not _ID.fullmatch(card_id) or not _SYMBOL.fullmatch(symbol):
            raise BoardError("invalid_card", "Mỗi thẻ cần một mã cổ phiếu hợp lệ.")
        if stage not in STAGES:
            raise BoardError("invalid_stage", "Cột không hợp lệ.")
        if symbol in symbols:
            raise BoardError("duplicate_symbol", f"{symbol} đã có thẻ.")
        symbols.add(symbol)
        note, lesson = str(raw.get("note") or "").strip()[:300], str(raw.get("lesson") or "").strip()[:500]
        old = before.get(card_id)
        moved = old["moved_on"] if old and old["stage"] == stage and old["symbol"] == symbol else today.isoformat()
        out.append({"id": card_id, "symbol": symbol, "stage": stage, "note": note, "lesson": lesson, "moved_on": moved})
    return out


def board_view(cards: list[dict], *, held: set[str], theses: set[str], today: date) -> dict:
    """Columns in order, each card with how many days it has been there and where the ledger or the theses disagree."""
    columns = {s: [] for s in STAGES}
    for c in cards:
        hints = []
        if c["symbol"] in held and c["stage"] not in ("holding",):
            hints.append("Sổ lệnh đang có mã này: chuyển sang Đang nắm?")
        if c["stage"] == "holding" and c["symbol"] not in held:
            hints.append("Sổ lệnh không còn mã này: chuyển sang Đã bán?")
        if c["stage"] == "holding" and c["symbol"] not in theses:
            hints.append("Chưa có luận điểm đang mở")
        columns[c["stage"]].append({**c, "days": (today - date.fromisoformat(c["moved_on"])).days, "hints": hints})
    for s in STAGES:
        columns[s].sort(key=lambda c: (-c["days"], c["symbol"]))
    carded = {c["symbol"] for c in cards}
    return {"columns": [{"stage": s, "label": LABELS[s], "cards": columns[s]} for s in STAGES], "held_without_card": sorted(held - carded)}
