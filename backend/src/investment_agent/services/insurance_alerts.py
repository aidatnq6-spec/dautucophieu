"""Nhắc đóng phí bảo hiểm: from 30 days before a premium is due, in Việc cần xem while the window lasts and in one Telegram note per policy and date.
Which (policy, date) was reminded is kept in data/alerts/insurance.json: ids and dates only, no amounts. Personal data; never sent to a model."""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from investment_agent.domain.property_book import Policy, PropertyBook, next_due
from investment_agent.notifications.render import vnd

AHEAD = timedelta(days=30)
FOOTER = "Ứng dụng chỉ nhắc, không đóng phí hộ. Không phải khuyến nghị."


def _due(book: PropertyBook | None, today: date) -> list[tuple[Policy, date]]:
    if book is None:
        return []
    found = [(p, d) for p in book.policies if (d := next_due(p, today)) is not None and d <= today + AHEAD]
    return sorted(found, key=lambda x: (x[1], x[0].name))


def _line(policy: Policy, due: date, today: date) -> str:
    amount = f" {vnd(format(policy.premium, 'f'))}" if policy.premium is not None else ""
    when = f"hôm nay ({due:%d/%m/%Y})" if due == today else f"ngày {due:%d/%m/%Y}, còn {(due - today).days} ngày"
    return f"{policy.name}: đóng phí{amount} {when}" + ("" if policy.premium is not None else " (chưa nhập số phí)")


def due_lines(book: PropertyBook | None, today: date) -> list[str]:
    return [_line(p, d, today) for p, d in _due(book, today)]


def insurance_alerts_run(data_dir: Path, *, book: PropertyBook | None, send: Callable[[str], bool], today: date) -> dict:
    path = Path(data_dir) / "alerts" / "insurance.json"
    marks = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current = {p.id for p in book.policies} if book else set()
    kept = {k: v for k, v in marks.items() if k in current}
    due = [(p, d) for p, d in _due(book, today) if kept.get(p.id) != d.isoformat()]
    sent = bool(due) and bool(send("\n".join(["Sắp đến hạn đóng phí bảo hiểm", *(f"• {_line(p, d, today)}" for p, d in due), FOOTER])))
    if sent:
        kept |= {p.id: d.isoformat() for p, d in due}
    if kept != marks:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(sorted(kept.items()))), encoding="utf-8")
        os.replace(tmp, path)
    return {"alerts": len(due), "sent": sent}
