"""Dò lịch giao dịch HOSE: from 1 December while next year's calendar file is missing (and in any month while this year's is), each run
reads HOSE's latest news (api.hsx.vn, robots.txt allows) and tells over Telegram, once, a notice whose title speaks of days off or the
trading calendar of that year, with its link. The calendar file itself is made by hand from the notice; nothing is guessed here."""

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


def looking_for(config_dir: Path, today: date) -> list[int]:
    years = [today.year] + ([today.year + 1] if today.month == 12 else [])
    return [y for y in years if not (Path(config_dir) / f"trading-calendar-hose-{y}.json").is_file()]


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def watch_calendar(data_dir: Path, config_dir: Path, *, get: Callable[[str], str] = default_get, send: Callable[[str], bool],
                   today: date) -> dict:
    years = looking_for(config_dir, today)
    if not years:
        return {"status": "ok", "looking_for": [], "sent": 0}
    try:
        items = json.loads(get(NEWS_URL))["data"]["list"] or []
    except Exception:
        return {"status": "source_error", "looking_for": years, "sent": 0}
    path = Path(data_dir).joinpath(*STATE)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"told": []}
    sent = 0
    for item in items:
        title = (item.get("title") or "").strip()
        year = next((y for y in years if str(y) in title), None)
        if year is None or not _WORDS.search(title) or item["id"] in state["told"]:
            continue
        day = datetime.fromtimestamp(item["postedDate"], VN).strftime("%d/%m/%Y")
        text = (f"Lịch giao dịch HOSE {year}: HOSE vừa đăng “{title}” ({day}) {LINK.format(id=item['id'])}\n"
                f"Phần mềm chưa có tệp config/trading-calendar-hose-{year}.json: gửi thông báo này để tạo lịch theo đúng số ngày nghỉ HOSE công bố.")
        if send(text):
            state["told"].append(item["id"])
            _write(path, state)
            sent += 1
    return {"status": "ok", "looking_for": years, "sent": sent}
