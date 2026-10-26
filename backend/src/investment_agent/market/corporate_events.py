"""Corporate events of watched tickers (Vnstock company events, Community tier): dividends, share issues, shareholder
meetings, insider deals. Stored per ticker under data/events; Telegram reminders go out a few days before the date that
matters (ex-rights date, or the meeting day), once per event. Events without that date are shown but never reminded."""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

REMINDED_KINDS = ("dividend_cash", "issue", "meeting")
_KIND = {"DIV": "dividend_cash", "ISS": "issue", "AGME": "meeting", "EGME": "meeting", "AIS": "listing"}


def _day(value) -> str | None:
    if value is None or value != value:  # None or NaN/NaT
        return None
    text = str(value)
    return text[:10] if len(text) >= 10 and text[4] == "-" else None


def _num(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def normalise(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        code = str(r.get("event_code") or "")
        kind = "insider" if code.startswith("DD") else _KIND.get(code, "other")
        key = _day(r.get("display_date1")) if kind == "meeting" else _day(r.get("exright_date")) if kind in ("dividend_cash", "issue") \
            else _day(r.get("display_date1"))
        out.append({"id": f"{r.get('symbol')}-{r.get('id')}", "symbol": str(r.get("symbol") or "").upper(), "code": code, "kind": kind,
                    "title": str(r.get("event_title_vi") or ""), "key_date": key, "exright": _day(r.get("exright_date")),
                    "record": _day(r.get("record_date")), "payout": _day(r.get("payout_date")),
                    "ratio": _num(r.get("exercise_ratio")), "value_per_share": _num(r.get("value_per_share"))})
    return out


class EventStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "events"

    def _write(self, path: Path, payload) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def save(self, symbol: str, events: list[dict], *, fetched_at: str) -> None:
        self._write(self.root / f"{symbol.upper()}.json", {"symbol": symbol.upper(), "fetched_at": fetched_at, "events": events})

    def read(self, symbol: str) -> dict | None:
        try:
            data = json.loads((self.root / f"{symbol.upper()}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def events(self, symbols: list[str]) -> list[dict]:
        return [e for s in symbols for e in ((self.read(s) or {}).get("events") or [])]

    def notified(self) -> set[str]:
        try:
            return set(json.loads((self.root / "_notified.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return set()

    def mark_notified(self, ids: list[str]) -> None:
        self._write(self.root / "_notified.json", sorted(self.notified() | set(ids)))


def due_reminders(store: EventStore, *, symbols: list[str], today: date, days: int = 5) -> list[dict]:
    """Dated dividend, issue and meeting events from today to today+days that were not reminded yet."""
    done, end = store.notified(), (today + timedelta(days=days)).isoformat()
    due = [e for e in store.events(symbols) if e["kind"] in REMINDED_KINDS and e["key_date"] and today.isoformat() <= e["key_date"] <= end
           and e["id"] not in done]
    return sorted(due, key=lambda e: (e["key_date"], e["symbol"]))


def _vn(day: str | None) -> str:
    return f"{day[8:10]}/{day[5:7]}/{day[:4]}" if day else "chưa có ngày"


def _money(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def describe(e: dict) -> str:
    if e["kind"] == "meeting":
        return f"{e['title'].split(' - ', 1)[-1]}: họp {_vn(e['key_date'])}"
    parts = [e["title"].split(" - ", 1)[0] if e["kind"] == "dividend_cash" else e["title"], f"GDKHQ {_vn(e['exright'])}"]
    if e["kind"] == "dividend_cash" and e["value_per_share"]:
        parts.append(f"{_money(e['value_per_share'])} đ/cp")
    if e["record"]:
        parts.append(f"chốt {_vn(e['record'])}")
    if e["payout"]:
        parts.append(f"trả {_vn(e['payout'])}")
    return " · ".join(parts)


def render_reminders(events: list[dict], *, held: set[str], today: date) -> str:
    lines = [f"LỊCH SỰ KIỆN 5 NGÀY TỚI (từ {_vn(today.isoformat())})", ""]
    for e in sorted(events, key=lambda x: (x["symbol"] not in held, x["key_date"] or "", x["symbol"])):
        name = f"{e['symbol']} (đang nắm)" if e["symbol"] in held else e["symbol"]
        lines.append(f"- {name}: {describe(e)}")
    lines += ["", "Nguồn: Vnstock (sự kiện doanh nghiệp). Chỉ để theo dõi, không phải khuyến nghị."]
    return "\n".join(lines)


def stale(store: EventStore, symbol: str, *, now: datetime, max_age: timedelta = timedelta(hours=20)) -> bool:
    data = store.read(symbol)
    try:
        return data is None or now - datetime.fromisoformat(data["fetched_at"]) > max_age
    except (KeyError, TypeError, ValueError):
        return True


def events_run(data_dir: Path, *, fetch, notify, now: datetime, pace: float = 1.2, days: int = 5) -> dict:
    """Refresh stale tickers of the watchlist (one Vnstock call each, paced), then remind the next `days` days once.
    notify(due) returns True only when the message went out; otherwise the same events are tried again next run."""
    import time

    from .watchlist import load_watchlist
    store, symbols = EventStore(data_dir), list(load_watchlist(Path(data_dir)).symbols)
    refreshed, errors = 0, {}
    for symbol in symbols:
        if not stale(store, symbol, now=now):
            continue
        try:
            store.save(symbol, normalise(fetch(symbol)), fetched_at=now.isoformat())
            refreshed += 1
        except Exception as exc:  # one ticker failing never stops the others
            errors[symbol] = type(exc).__name__
        if pace:
            time.sleep(pace)
    due = due_reminders(store, symbols=symbols, today=now.date(), days=days)
    reminded = 0
    if due and notify is not None and notify(due):
        store.mark_notified([e["id"] for e in due])
        reminded = len(due)
    return {"status": "ok", "refreshed": refreshed, "errors": errors, "reminded": reminded}
