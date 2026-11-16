"""Lịch vĩ mô Mỹ: the Fed's rate decisions and FOMC minutes (the Fed's own monthly calendar pages, federalreserve.gov/newsevents/
<year>-<month>.htm: no robots.txt, checked 16/11/2026) and the CPI release dates (BLS schedule, bls.gov/schedule/news_release/cpi.htm,
robots.txt allows). Times are the publishers' Eastern times, turned into Vietnam time (summer time counted). Read once a day into
data/macro/us-calendar.json; a source that fails keeps the events it gave before. Nothing is worked out: a minutes date appears only once
the Fed's calendar lists it."""

import calendar as _cal
import html
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

ET, VN = ZoneInfo("America/New_York"), ZoneInfo("Asia/Ho_Chi_Minh")
BLS_CPI = "https://www.bls.gov/schedule/news_release/cpi.htm"
FILE, STATE = ("macro", "us-calendar.json"), ("alerts", "us-calendar.json")
MONTHS_AHEAD = 3
MONTHS = {m.lower(): i for i, m in enumerate(_cal.month_name) if m}
USER_AGENT = "investment-agent/0.1 (personal use)"

_ROW = re.compile(r'<div class="col-xs-2">\s*<p>([^<]+)</p>\s*</div>\s*<div class="col-xs-7">(.*?)</div>\s*<div class="col-xs-3">\s*<p>(\d{1,2})</p>',
                  re.S)
_BLS_ROW = re.compile(r"<td>\s*([A-Z][a-z]+ \d{4})\s*</td>\s*<td>\s*([A-Z][a-z]{2,4})\.? (\d{1,2}), (\d{4})\s*</td>\s*<td>\s*(\d{1,2}):(\d{2}) ([AP]M)")
_SPAN = re.compile(r"([A-Z][a-z]+)\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?")


def fed_month_url(year: int, month: int) -> str:
    return f"https://www.federalreserve.gov/newsevents/{year}-{_cal.month_name[month].lower()}.htm"


def default_get(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def _text(fragment: str) -> list[str]:
    parts = [html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in re.findall(r"<p>(.*?)</p>", fragment, re.S)]
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip() and re.sub(r"<[^>]+>", "", p).strip()]


def _clock(text: str) -> tuple[int, int]:
    m = re.match(r"(\d{1,2}):(\d{2})\s*([ap])\.?m\.?", text.strip().lower())
    if not m:
        raise ValueError(text)
    hour = int(m.group(1)) % 12 + (12 if m.group(3) == "p" else 0)
    return hour, int(m.group(2))


def parse_fed_month(page: str, year: int, month: int) -> list[dict]:
    """The FOMC block of one month page: the meeting (decision day) and the minutes, with their Eastern time."""
    start = page.find("FOMC Meetings")
    if start < 0:
        return []
    end = page.find("cal-nojs__rowTitle", start)
    block = page[start:end if end > 0 else len(page)]
    out = []
    for time_text, body, day in _ROW.findall(block):
        lines = _text(body)
        if not lines:
            continue
        kind = {"FOMC Meeting": "fomc", "FOMC Minutes": "minutes"}.get(lines[0])
        if kind is None:
            continue
        hour, minute = _clock(time_text)
        at = datetime(year, month, int(day), hour, minute, tzinfo=ET)
        out.append({"kind": kind, "et": at.isoformat(), "detail": lines[1] if len(lines) > 1 else ""})
    return out


def parse_bls_cpi(page: str) -> list[dict]:
    out = []
    for ref, mon, day, year, hour, minute, half in _BLS_ROW.findall(page):
        month = MONTHS.get(next((m for m in MONTHS if m.startswith(mon.lower()[:3])), ""), 0)
        if not month:
            continue
        h = int(hour) % 12 + (12 if half == "PM" else 0)
        out.append({"kind": "cpi", "et": datetime(int(year), month, int(day), h, int(minute), tzinfo=ET).isoformat(), "detail": ref})
    return out


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _read(path: Path, empty: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty


def refresh_us_calendar(data_dir: Path, *, get: Callable[[str], str] = default_get, today: date) -> dict:
    path = Path(data_dir).joinpath(*FILE)
    saved = _read(path, {"events": []})
    months = [((today.year * 12 + today.month - 1 + i) // 12, (today.month - 1 + i) % 12 + 1) for i in range(MONTHS_AHEAD)]
    sources = [(fed_month_url(y, m), lambda page, y=y, m=m: parse_fed_month(page, y, m)) for y, m in months] + [(BLS_CPI, parse_bls_cpi)]
    fresh, errors, read = [], [], set()
    for url, parse in sources:
        try:
            fresh += [{**e, "source": url} for e in parse(get(url))]
            read.add(url)
        except Exception:
            errors.append(url)
    keep_from = (today - timedelta(days=60)).isoformat()
    events = [e for e in saved["events"] if e["source"] not in read and e["et"][:10] >= keep_from] + fresh
    events = sorted({(e["kind"], e["et"]): e for e in events}.values(), key=lambda e: e["et"])
    _write(path, {"updated_on": today.isoformat(), "events": events, "errors": errors})
    return {"status": "ok" if read else "error", "events": len(events), "errors": errors}


def _span(detail: str) -> str:
    m = _SPAN.search(detail)
    if not m or m.group(1).lower() not in MONTHS:
        return detail
    month, first, last = MONTHS[m.group(1).lower()], m.group(2), m.group(3)
    return f"{first}–{last}/{month}" if last else f"{first}/{month}"


def _describe(e: dict) -> str:
    if e["kind"] == "fomc":
        return f"Fed công bố quyết định lãi suất (họp {_span(e['detail'])})"
    if e["kind"] == "minutes":
        return f"Fed công bố biên bản họp FOMC (cuộc họp {_span(e['detail'])})"
    month, year = e["detail"].split()
    return f"Mỹ công bố CPI tháng {MONTHS[month.lower()]}/{year}"


def upcoming(data_dir: Path, *, today: date, days: int) -> list[dict]:
    rows = []
    for e in _read(Path(data_dir).joinpath(*FILE), {"events": []})["events"]:
        at = datetime.fromisoformat(e["et"]).astimezone(VN)
        if today <= at.date() <= today + timedelta(days=days):
            rows.append({"kind": e["kind"], "on": at.date().isoformat(), "at": at.strftime("%H:%M"), "text": _describe(e), "source": e["source"],
                         "key": f"{e['kind']}:{e['et']}"})
    return sorted(rows, key=lambda r: (r["on"], r["at"]))


def remind_us_calendar(data_dir: Path, *, send: Callable[[str], bool], today: date) -> dict:
    """One Telegram note an event, the day before (Vietnam time) or, when that one did not go out, on the day."""
    path = Path(data_dir).joinpath(*STATE)
    state = _read(path, {"told": []})
    sent = 0
    for e in upcoming(data_dir, today=today, days=1):
        if e["key"] in state["told"]:
            continue
        when = "hôm nay" if e["on"] == today.isoformat() else "ngày mai"
        site = "federalreserve.gov" if "federalreserve" in e["source"] else "bls.gov"
        text = f"Lịch vĩ mô Mỹ: {when} {e['on'][8:10]}/{e['on'][5:7]} lúc {e['at']} (giờ Việt Nam), {e['text']}. Nguồn: {site}"
        if send(text):
            state["told"] = [*state["told"], e["key"]][-200:]
            _write(path, state)
            sent += 1
    return {"sent": sent}
