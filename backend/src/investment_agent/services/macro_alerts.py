"""Nhắc vĩ mô (owner, 21/11/2026): Đèn tín hiệu rủi ro vĩ mô and Nhắc thanh khoản và tỷ giá in one Telegram message when both have
something new on the same run (they often speak of the same overnight rate). Each part keeps its own state; a message Telegram did not
take leaves both as they were, so the next run sends it again whole. Public figures only."""

from datetime import date
from pathlib import Path

from investment_agent.services.liquidity_alerts import liquidity_note
from investment_agent.services.macro_signals import FOOTER, signals_note


def macro_alerts_run(data_dir: Path, *, send, today: date) -> dict:
    notes = {"signals": signals_note(Path(data_dir), today=today), "liquidity": liquidity_note(Path(data_dir), today=today)}
    parts = [k for k, (text, _) in notes.items() if text]
    sent = bool(send("\n\n".join(notes[k][0] for k in parts) + "\n" + FOOTER)) if parts else False
    return {"parts": parts, "sent": sent, **{k: commit(sent) for k, (_, commit) in notes.items()}}
