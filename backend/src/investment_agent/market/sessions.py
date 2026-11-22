"""Whether a day had a HOSE session: the official calendar of that year when the app has it (config/trading-calendar-hose-<year>.json),
otherwise every weekday counts; nothing is guessed beyond that."""

from datetime import date

_CACHE: dict = {}  # path → (modified time, calendar or None): read once per file, again when the file changes (owner review 22/11/2026)


def _calendar(path):
    from investment_agent.cli import load_calendar
    stamp = path.stat().st_mtime_ns
    hit = _CACHE.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        cal = load_calendar(path)
    except ValueError:
        cal = None
    _CACHE[path] = (stamp, cal)
    return cal


def is_session(day: date) -> bool:
    from investment_agent.domain.pinned import CONFIG_DIR
    path = CONFIG_DIR / f"trading-calendar-hose-{day.year}.json"
    if path.is_file():
        cal = _calendar(path)
        if cal is not None:
            try:
                return cal.is_session(day)
            except ValueError:
                pass
    return day.weekday() < 5
