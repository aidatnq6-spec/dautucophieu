"""Nhắc đóng phí: insurance premiums and the yearly fees of Góp vốn và đầu tư riêng, from 30 days before each is due, in Việc cần xem while the window
lasts and in one Telegram note per row and date. Which (row, date) was reminded is kept in data/alerts/insurance.json: ids and dates only, no amounts.
Personal data; never sent to a model."""

import json
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from investment_agent.domain.property_book import PropertyBook, next_due, next_fee
from investment_agent.notifications.render import vnd

AHEAD = timedelta(days=30)
FOOTER = "Ứng dụng chỉ nhắc, không đóng phí hộ. Không phải khuyến nghị."


def _due(book: PropertyBook | None, today: date) -> list[tuple[str, str, str, Decimal | None, date]]:
    """(kind, id, name, amount, date) due within the window, soonest first."""
    if book is None:
        return []
    rows = [("insurance_due", p.id, p.name, p.premium, d) for p in book.policies if (d := next_due(p, today)) is not None]
    rows += [("venture_fee", v.id, v.name, v.annual_fee, d) for v in book.ventures if (d := next_fee(v, today)) is not None]
    return sorted((r for r in rows if r[4] <= today + AHEAD), key=lambda r: (r[4], r[2]))


def _line(kind: str, name: str, amount: Decimal | None, due: date, today: date) -> str:
    what = "đóng phí thường niên" if kind == "venture_fee" else "đóng phí"
    money = f" {vnd(format(amount, 'f'))}" if amount is not None else ""
    when = f"hôm nay ({due:%d/%m/%Y})" if due == today else f"ngày {due:%d/%m/%Y}, còn {(due - today).days} ngày"
    return f"{name}: {what}{money} {when}" + ("" if amount is not None else " (chưa nhập số phí)")


def due_items(book: PropertyBook | None, today: date) -> list[tuple[str, str]]:
    """(kind, line) for Việc cần xem."""
    return [(k, _line(k, name, amount, d, today)) for k, _, name, amount, d in _due(book, today)]


def due_lines(book: PropertyBook | None, today: date) -> list[str]:
    return [line for _, line in due_items(book, today)]


def insurance_alerts_run(data_dir: Path, *, book: PropertyBook | None, send: Callable[[str], bool], today: date) -> dict:
    path = Path(data_dir) / "alerts" / "insurance.json"
    marks = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current = {x.id for x in (*book.policies, *book.ventures)} if book else set()
    kept = {k: v for k, v in marks.items() if k in current}
    due = [r for r in _due(book, today) if kept.get(r[1]) != r[4].isoformat()]
    sent = bool(due) and bool(send("\n".join(["Sắp đến hạn đóng phí", *(f"• {_line(k, name, amount, d, today)}" for k, _, name, amount, d in due), FOOTER])))
    if sent:
        kept |= {r[1]: r[4].isoformat() for r in due}
    if kept != marks:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(sorted(kept.items()))), encoding="utf-8")
        os.replace(tmp, path)
    return {"alerts": len(due), "sent": sent}
