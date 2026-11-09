"""Nhắc hết lãi ưu đãi: 90 days before a loan's promotion ends, in Việc cần xem while the window lasts and in one Telegram note per loan and date.
The payments are at today's balance, so nothing about the months between is assumed. Which (loan, date) was reminded is kept in data/alerts/loans.json:
ids and dates only, no amounts. Personal data; never sent to a model."""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from investment_agent.domain.property_book import Loan, PropertyBook, loan_payment
from investment_agent.notifications.render import vnd
from investment_agent.services.property_book import RECORD
from investment_agent.services.records import read_version

AHEAD = timedelta(days=90)
FOOTER = "Khoản trả tính theo dư nợ hiện tại. Phần mềm không tự đổi gì; cập nhật lãi và dư nợ ở Hồ sơ & rủi ro. Không phải khuyến nghị."


def read_property_book(repo, owner) -> PropertyBook | None:
    stored = read_version(repo, owner, *RECORD, None)
    return PropertyBook.model_validate(stored.payload) if stored else None


def _ending(book: PropertyBook, today: date) -> list[Loan]:
    return sorted((x for x in book.loans if x.promo_ends is not None and today <= x.promo_ends <= today + AHEAD), key=lambda x: (x.promo_ends, x.name))


def _line(loan: Loan, today: date) -> str:
    left = (loan.promo_ends - today).days
    when = f"hết ưu đãi hôm nay ({loan.promo_ends:%d/%m/%Y})" if left == 0 else f"hết ưu đãi sau {left} ngày ({loan.promo_ends:%d/%m/%Y})"
    now_pay = loan_payment(loan)
    after_pay = loan_payment(loan.model_copy(update={"rate": loan.after_rate})) if loan.after_rate is not None else None
    if now_pay is None or after_pay is None:
        return f"{loan.name}: {when}, chưa nhập đủ số để tính khoản trả sau ưu đãi"
    return f"{loan.name}: {when}, khoản trả {vnd(format(now_pay, 'f'))} lên {vnd(format(after_pay, 'f'))}"


def promo_lines(book: PropertyBook | None, today: date) -> list[str]:
    return [_line(x, today) for x in _ending(book, today)] if book else []


def _state_path(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "loans.json"


def loan_alerts_run(data_dir: Path, *, book: PropertyBook | None, send: Callable[[str], bool], today: date) -> dict:
    if book is None:
        return {"alerts": 0, "sent": False}
    path = _state_path(data_dir)
    marks = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current = {x.id: x.promo_ends.isoformat() for x in book.loans if x.promo_ends is not None}
    kept = {k: v for k, v in marks.items() if current.get(k) == v}  # a deleted loan or a new date drops the old mark
    due = [x for x in _ending(book, today) if kept.get(x.id) != x.promo_ends.isoformat()]
    sent = bool(due) and bool(send("\n".join(["Sắp hết lãi ưu đãi", *(f"• {_line(x, today)}" for x in due), FOOTER])))
    if sent:
        kept |= {x.id: x.promo_ends.isoformat() for x in due}
    if kept != marks:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(sorted(kept.items()))), encoding="utf-8")
        os.replace(tmp, path)
    return {"alerts": len(due), "sent": sent}
