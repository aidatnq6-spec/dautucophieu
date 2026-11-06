"""Nhắc sổ tiết kiệm đáo hạn: one Telegram note per sổ, from the day before it matures (catching up at most 7 days after), so the
owner can roll it over, close it or move the money. Nothing is done to the sổ and nothing is advised.

Which (sổ, maturity date) was reminded is kept in data/alerts/deposits.json — row ids and dates only, no amounts. A new date (after
a roll-over) is reminded again; a deleted row drops its mark. A sổ is marked only after the note went out. Personal data; never sent
to a model."""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from investment_agent.domain.deposit_book import Deposit, DepositBook
from investment_agent.notifications.render import vnd

BEFORE, CATCH_UP = timedelta(days=1), timedelta(days=7)
FOOTER = "Phần mềm không tự tái tục hay tất toán. Xử lý xong, sửa ngày đáo hạn hoặc xóa sổ ở Sổ tài sản. Không phải khuyến nghị."


def _state_path(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "deposits.json"


def _save_state(data_dir: Path, marks: dict[str, str]) -> None:
    path = _state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(marks.items()))), encoding="utf-8")
    os.replace(tmp, path)


def _when(d: Deposit, today: date) -> str:
    day = d.matures.strftime("%d/%m/%Y")
    if d.matures > today:
        return f"đến hạn ngày mai {day}"
    if d.matures == today:
        return f"đến hạn hôm nay {day}"
    return f"đã đến hạn {day} ({(today - d.matures).days} ngày trước)"


def _line(d: Deposit, today: date) -> str:
    if d.payout == "upfront":
        interest = "lãi đầu kỳ, đã nhận"
    elif d.interest is None:
        interest = "lãi chưa nhập"
    else:
        interest = f"lãi khi đáo hạn {vnd(format(d.interest, 'f'))}"
    parts = [d.bank, _when(d, today), f"gốc {vnd(format(d.principal, 'f'))}", interest] + (["phong tỏa"] if d.locked else [])
    return "• " + " · ".join(parts)


def render(deposits: list[Deposit], today: date) -> str:
    return "\n".join(["Sổ tiết kiệm đến hạn", *(_line(d, today) for d in deposits), FOOTER])


def deposit_alerts_run(data_dir: Path, *, book: DepositBook | None, send: Callable[[str], bool], today: date) -> dict:
    if book is None:
        return {"alerts": 0, "sent": False}
    path = _state_path(data_dir)
    marks = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current = {d.id: d.matures.isoformat() for d in book.deposits}
    kept = {k: v for k, v in marks.items() if current.get(k) == v}  # a deleted row or a new date drops the old mark
    due = sorted((d for d in book.deposits if d.matures - BEFORE <= today <= d.matures + CATCH_UP and kept.get(d.id) != d.matures.isoformat()),
                 key=lambda d: (d.matures, d.bank))
    sent = bool(due) and bool(send(render(due, today)))
    if sent:
        kept |= {d.id: d.matures.isoformat() for d in due}
    if kept != marks:
        _save_state(data_dir, kept)
    return {"alerts": len(due), "sent": sent}
