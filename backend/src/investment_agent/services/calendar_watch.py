"""Dò lịch giao dịch HOSE: each run reads HOSE's latest news (api.hsx.vn, robots.txt allows) and tells over Telegram, once, a notice whose
title speaks of days off or the trading calendar of this year (and of next year from 1 December), with its link: to make the calendar
file when it is missing, or to check it when it exists. Until 27/11/2026 the watch stopped once a year's file existed, and so missed
HOSE's notice of 11/11/2026 adding 24/11/2026 (Ngày Văn hóa Việt Nam). The calendar file is edited by hand; nothing is guessed here."""

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

NEWS_URL = "https://api.hsx.vn/n/api/v1/1/news/newstype/-1/1?pageIndex=1&pageSize=50"
LINK = "https://www.hsx.vn/tin-tuc/tin-hose/chi-tiet/{id}"
STATE = ("alerts", "calendar-watch.json")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_WORDS = re.compile(r"nghỉ|lịch giao dịch|ngày lễ", re.IGNORECASE)


def default_get(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=90, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
    response.raise_for_status()
    return response.text


def watching(today: date) -> list[int]:
    return [today.year] + ([today.year + 1] if today.month == 12 else [])


def looking_for(config_dir: Path, today: date) -> list[int]:
    """The years watched whose calendar file is still missing."""
    return [y for y in watching(today) if not (Path(config_dir) / f"trading-calendar-hose-{y}.json").is_file()]


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def watch_calendar(data_dir: Path, config_dir: Path, *, get: Callable[[str], str] = default_get, send: Callable[[str], bool],
                   today: date) -> dict:
    years, missing = watching(today), looking_for(config_dir, today)
    try:
        items = json.loads(get(NEWS_URL))["data"]["list"] or []
    except Exception:
        return {"status": "source_error", "watching": years, "looking_for": missing, "sent": 0}
    path = Path(data_dir).joinpath(*STATE)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"told": []}
    sent = 0
    for item in items:
        title = (item.get("title") or "").strip()
        year = next((y for y in years if str(y) in title), None)
        if year is None or not _WORDS.search(title) or item["id"] in state["told"]:
            continue
        day = datetime.fromtimestamp(item["postedDate"], VN).strftime("%d/%m/%Y")
        head = f"Lịch giao dịch HOSE {year}: HOSE vừa đăng “{title}” ({day}) {LINK.format(id=item['id'])}\n"
        text = head + (f"Phần mềm chưa có tệp config/trading-calendar-hose-{year}.json: gửi thông báo này để tạo lịch theo đúng số ngày nghỉ HOSE công bố."
                       if year in missing else
                       f"Kiểm lại config/trading-calendar-hose-{year}.json: thông báo này có thể thêm hoặc đổi ngày nghỉ của năm đang dùng.")
        if send(text):
            state["told"].append(item["id"])
            _write(path, state)
            sent += 1
    return {"status": "ok", "watching": years, "looking_for": missing, "sent": sent}
