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
