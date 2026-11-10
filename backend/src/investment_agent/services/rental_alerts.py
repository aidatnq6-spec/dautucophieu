"""Nhắc thu tiền thuê and hợp đồng sắp hết: in Việc cần xem while due, and one Telegram note per room and month (or lease end). Which were sent is kept
in data/alerts/rental.json as keys only, no amounts or names. Personal data; never sent to a model."""

import json
import os
from datetime import date
from pathlib import Path
from typing import Callable

from investment_agent.domain.rental_book import RentalBook, due_items
from investment_agent.services.records import read_version

RECORD = ("settings", "rental_book")
FOOTER = "Ứng dụng chỉ nhắc; ghi lần thu ở Hồ sơ & rủi ro, thẻ Tài sản. Không phải khuyến nghị."


def read_rental_book(repo, owner) -> RentalBook | None:
    stored = read_version(repo, owner, *RECORD, None)
    return RentalBook.model_validate(stored.payload) if stored else None


def rental_alerts_run(data_dir: Path, *, book: RentalBook | None, send: Callable[[str], bool], today: date) -> dict:
    path = Path(data_dir) / "alerts" / "rental.json"
    sent_keys = set(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else set()
    due = [(k, key, line) for k, key, line in due_items(book, today) if key not in sent_keys]
    sent = bool(due) and bool(send("\n".join(["Cho thuê căn hộ", *(f"• {line}" for _, _, line in due), FOOTER])))
    if sent:
        keep = sorted(sent_keys | {key for _, key, _ in due})[-500:]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(keep), encoding="utf-8")
        os.replace(tmp, path)
    return {"alerts": len(due), "sent": sent}
