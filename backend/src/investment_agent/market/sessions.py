"""Whether a day had a HOSE session: the official calendar of that year when the app has it (config/trading-calendar-hose-<year>.json),
otherwise every weekday counts; nothing is guessed beyond that."""

from datetime import date


def is_session(day: date) -> bool:
    from investment_agent.cli import load_calendar
    from investment_agent.domain.pinned import CONFIG_DIR
    path = CONFIG_DIR / f"trading-calendar-hose-{day.year}.json"
    if path.is_file():
        try:
            return load_calendar(path).is_session(day)
        except ValueError:
            pass
    return day.weekday() < 5
