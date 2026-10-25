"""Trading sessions from an explicit, versioned holiday list; never inferred beyond its range."""

from dataclasses import dataclass
from datetime import date, timedelta


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
