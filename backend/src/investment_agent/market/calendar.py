"""Trading sessions from an explicit, versioned holiday list; never inferred beyond its range."""

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class TradingCalendar:
    version: str
    source: str
    holidays: frozenset[date]
    first: date
    last: date

    def _check(self, day: date):
        if not self.first <= day <= self.last:
            raise ValueError("date outside the calendar's verified range")

    def is_session(self, day: date) -> bool:
        self._check(day)
        return day.weekday() < 5 and day not in self.holidays

    def sessions(self, start: date, end: date) -> tuple[date, ...]:
        self._check(start)
        self._check(end)
        days, day = [], start
        while day <= end:
            if day.weekday() < 5 and day not in self.holidays:
                days.append(day)
            day += timedelta(days=1)
        return tuple(days)


# Read from config/ (moved from cli.py on 28/11/2026 so the public-data MCP can read the calendar without importing the CLI).
class CalendarMissing(FileNotFoundError):
    """The year's HOSE calendar is not in config/: said plainly, never replaced by a guessed one (owner, 23/11/2026)."""


_YEAR_FILE = re.compile(r"^trading-calendar-hose-(\d{4})\.json$")


def _read_calendar(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    # the shape is checked where the file is read, so every caller's (OSError, ValueError, KeyError) holds (review 23/11/2026 (3))
    if not isinstance(data, dict):
        raise ValueError("calendar file must hold one object")
    if data.get("source") in (None, "", "synthetic"):
        raise ValueError("calendar must name its official source")
    if not (all(isinstance(data.get(k), str) for k in ("version", "source", "first", "last")) and isinstance(data.get("holidays"), list)
            and all(isinstance(d, str) for d in data["holidays"])):
        raise ValueError("calendar fields must be text, and holidays a list of dates")
    return TradingCalendar(version=data["version"], source=data["source"], holidays=frozenset(date.fromisoformat(d) for d in data["holidays"]),
                           first=date.fromisoformat(data["first"]), last=date.fromisoformat(data["last"]))


def load_calendar(path: Path):
    """A HOSE calendar file; a year's file (trading-calendar-hose-<year>.json) is read with the years before and after it in the same folder
    when they meet it (31/12 then 01/01), so a look-back crosses new year (owner, 23/11/2026). Years that do not meet are not joined."""
    path = Path(path)
    m = _YEAR_FILE.match(path.name)
    if m and not path.is_file():
        raise CalendarMissing(f"chưa có lịch giao dịch HOSE {m.group(1)} (config/{path.name}); tạo từ thông báo của HOSE")
    cal = _read_calendar(path)
    if not m:
        return cal
    parts, year = [cal], int(m.group(1))

    def neighbour(y: int):
        """The year next door, or None when it is absent or cannot be read: this year's calendar never fails for it (review 23/11/2026)."""
        other = path.with_name(f"trading-calendar-hose-{y}.json")
        try:
            return _read_calendar(other) if other.is_file() else None
        except (OSError, ValueError, KeyError):  # a wrong shape is a ValueError of _read_calendar
            return None
    if (prev := neighbour(year - 1)) and prev.last + timedelta(days=1) == cal.first:
        parts.insert(0, prev)
    if (nxt := neighbour(year + 1)) and nxt.first - timedelta(days=1) == cal.last:
        parts.append(nxt)
    if len(parts) == 1:
        return cal
    return TradingCalendar(version=" + ".join(p.version for p in parts), source=" · ".join(p.source for p in parts),
                           holidays=frozenset().union(*(p.holidays for p in parts)), first=parts[0].first, last=parts[-1].last)


def calendar_dir() -> Path:
    """config/ of the repository, where each year's HOSE calendar lives."""
    from investment_agent.domain.pinned import CONFIG_DIR
    return CONFIG_DIR


MAX_LISTED = 260  # sessions listed by lich_giao_dich, about a year


def calendar_view(folder: Path, day: date, until: date | None = None) -> dict:
    """Lịch giao dịch HOSE cho Claude (owner, 28/11/2026): the day's session, the sessions either side, the count between two days and the
    weekday holidays left, from the year's file and the years it meets; nothing outside the files is inferred."""
    def missing(year: int) -> dict:
        return {"thieu": True, "ly_do": f"chưa có lịch giao dịch HOSE năm {year} trong kho"}
    try:
        cal = load_calendar(Path(folder) / f"trading-calendar-hose-{day.year}.json")
    except CalendarMissing:
        return missing(day.year)
    except (OSError, ValueError, KeyError):
        return {"thieu": True, "ly_do": f"không đọc được lịch giao dịch HOSE năm {day.year}"}
    for d in (day, until):
        if d is not None and not cal.first <= d <= cal.last:
            return missing(d.year)

    def step(start: date, by: int):
        d = start + timedelta(days=by)
        while cal.first <= d <= cal.last:
            if cal.is_session(d):
                return d, None
            d += timedelta(days=by)
        return None, f"chưa có lịch giao dịch HOSE năm {d.year} trong kho"
    before, why_before = step(day, -1)
    after, why_after = step(day, 1)
    weekday = day.weekday() < 5
    out = {"ngay": day.isoformat(), "co_phien": cal.is_session(day),
           "ly_do": None if cal.is_session(day) else ("cuối tuần" if not weekday else "ngày nghỉ theo lịch HOSE"),
           "phien_truoc": before.isoformat() if before else None, "phien_sau": after.isoformat() if after else None}
    if why_before:
        out["ly_do_phien_truoc"] = why_before
    if why_after:
        out["ly_do_phien_sau"] = why_after
    if until is not None:
        lo, hi = sorted((day, until))
        sessions = cal.sessions(lo, hi)
        out.update({"tu": lo.isoformat(), "den": hi.isoformat(), "so_phien": len(sessions),
                    "cac_phien": [d.isoformat() for d in sessions] if len(sessions) <= MAX_LISTED else None})
    checks = []
    for y in range(cal.first.year, cal.last.year + 1):
        try:
            raw = json.loads((Path(folder) / f"trading-calendar-hose-{y}.json").read_text(encoding="utf-8"))
            if raw.get("verification"):
                checks.append(str(raw["verification"]))
        except (OSError, ValueError):
            continue
    out.update({"ngay_nghi_con_lai": sorted(d.isoformat() for d in cal.holidays if d >= day and d.weekday() < 5 and d <= cal.last),
                "pham_vi": {"tu": cal.first.isoformat(), "den": cal.last.isoformat()}, "phien_ban": cal.version, "nguon": cal.source,
                "xac_minh": " · ".join(checks) or None,
                "luu_y": "Theo tệp lịch HOSE trong kho; ngày nghỉ chỉ có ngày, không có tên ngày lễ; ngoài phạm vi lịch thì không suy ra."})
    return out
