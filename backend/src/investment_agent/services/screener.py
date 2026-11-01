"""Bộ lọc tín hiệu: the owner's saved screens (`settings/screens`), the watched tickers' signal values from stored data, and the
after-close Telegram note for tickers new to a screen. The last matches are kept in data/alerts/screens.json (public tickers only).
Nothing is sent to a model."""

import json
import os
from datetime import date, datetime
from pathlib import Path

from investment_agent.api.routes.value_chains import chain_labels
from investment_agent.domain.screener import CRITERIA, MAX_SCREENS, ScreenError, build_rows, entered, match, validate_screen
from investment_agent.market.corporate_events import EventStore
from investment_agent.market.trend import SnapshotStore
from investment_agent.market.view import EmptyMarket
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.services.records import read_version

RECORD = ("settings", "screens")


def read_screens(repo, owner) -> tuple[list[dict], int]:
    record = read_version(repo, owner, *RECORD, None)
    return (list(record.payload.get("screens", [])), record.version) if record else ([], 0)


def change_screens(repo, owner, change: dict, *, expected_version: int, request_id: str) -> tuple[list[dict], int]:
    screens, _ = read_screens(repo, owner)
    if change.get("action") == "save":
        screen = validate_screen(change.get("screen") or {})
        if any(s["id"] == screen["id"] for s in screens):
            screens = [screen if s["id"] == screen["id"] else s for s in screens]
        elif len(screens) >= MAX_SCREENS:
            raise ScreenError("too_many_screens", f"Tối đa {MAX_SCREENS} bộ lọc.")
        else:
            screens = [*screens, screen]
    elif change.get("action") == "delete":
        if not any(s["id"] == change.get("id") for s in screens):
            raise ScreenError("screen_not_found", "Không tìm thấy bộ lọc này; hãy tải lại.")
        screens = [s for s in screens if s["id"] != change.get("id")]
    else:
        raise ScreenError("invalid_action", "Thao tác không hợp lệ.")
    record = repo.write(owner, *RECORD, {"screens": screens}, expected_version=expected_version, request_id=request_id)
    return screens, record.version


def foreign_by_symbol(data_dir: Path) -> dict[str, list[str]]:
    """Each ticker's net foreign value (billion đồng) per stored session snapshot, oldest first; sessions from before the
    per-ticker value was kept are left out."""
    out: dict[str, list[str]] = {}
    for path in sorted((Path(data_dir) / "brief").glob("*.json")):
        try:
            board = json.loads(path.read_text(encoding="utf-8")).get("board") or {}
        except (OSError, ValueError):
            continue
        for symbol, row in (board.get("symbols") or {}).items():
            if row.get("foreign_net_bn") is not None:
                out.setdefault(symbol, []).append(row["foreign_net_bn"])
    return out


def gather_rows(data_dir: Path, repo, owner, *, held: set[str], today: date, market=None) -> list[dict]:
    """The watched tickers with every criterion's value, from stored data; raises RepositoryUnavailable."""
    data_dir = Path(data_dir)
    symbols = list(load_watchlist(data_dir).symbols)
    try:
        valuation = {r["symbol"]: r for r in fair_value_board(data_dir, market or EmptyMarket(), repo, owner, held=held, today=today)["rows"]}
    except (OSError, ValueError, KeyError):
        valuation = {}
    snapshot = SnapshotStore(data_dir / "trend").latest() or {}
    trend = {r["id"]: r["cells"] for g in snapshot.get("groups", []) for r in g.get("rows", [])}
    try:
        chains = chain_labels(data_dir, today=today)
    except (OSError, ValueError):
        chains = None
    return build_rows(symbols=symbols, valuation=valuation, trend=trend, chains=chains, foreign=foreign_by_symbol(data_dir),
                      events=EventStore(data_dir).events(symbols), held=held, today=today)


def _describe(row: dict, criteria: dict) -> str:
    parts = []
    for key in criteria:
        value = row["values"].get(key)
        label, names = CRITERIA[key]
        shown = ", ".join(names[v] for v in value) if isinstance(value, list) else names.get(value, "—")
        parts.append(f"{label}: {shown}")
    return "; ".join(parts)


def _state(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "screens.json"


def screen_check_run(repo, owner, data_dir: Path, *, rows: list[dict], send, now: datetime) -> dict:
    """For screens set to notify: tickers that entered since the last check go out in one note; the first check of a screen is
    a baseline. The matches are recorded only when the note went out (or nothing was due)."""
    screens = [s for s in read_screens(repo, owner)[0] if s.get("notify")]
    path = _state(data_dir)
    previous = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    # Keyed by the screen and its criteria: changing the criteria starts a new baseline instead of announcing every ticker it now finds.
    key = {s["id"]: f"{s['id']}:{json.dumps(s['criteria'], sort_keys=True)}" for s in screens}
    current = {key[s["id"]]: [r["symbol"] for r in rows if match(s["criteria"], r)[0]] for s in screens}
    new = entered(previous, current)
    by_symbol = {r["symbol"]: r for r in rows}
    sent = False
    if new:
        blocks = []
        for s in screens:
            if key[s["id"]] in new:
                found = new[key[s["id"]]]
                lines = [f"Bộ lọc “{s['name']}”: {', '.join(found)}"]
                lines += [f"• {sym} — {_describe(by_symbol[sym], s['criteria'])}" for sym in found]
                blocks.append("\n".join(lines))
        text = (f"Bộ lọc tín hiệu · {now.strftime('%H:%M %d/%m')}\nMã mới lọt vào bộ lọc của bạn:\n\n" + "\n\n".join(blocks)
                + "\n\nChỉ để thu hẹp danh sách. Không phải khuyến nghị.")
        sent = bool(send(text))
        if not sent:
            return {"status": "ok", "screens": len(screens), "entered": sum(map(len, new.values())), "sent": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(current), encoding="utf-8")
    os.replace(tmp, path)
    return {"status": "ok", "screens": len(screens), "entered": sum(map(len, new.values())), "sent": sent}
