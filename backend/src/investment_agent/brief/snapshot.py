"""Per-session public market snapshot for the brief (data/brief/<session>.json), rebuilt on every scheduler wake-up.

Each section fails on its own; a later run fills gaps but never replaces a good section with a failed one.
Nothing personal is stored here: ordering by holdings and news filtering happen when the brief is shown.
"""

import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .board import summarise_board
from .hose import parse_hose
from .indices import IDS, index_rows
from .news import FEEDS, parse_rss, window_items

VN = ZoneInfo("Asia/Ho_Chi_Minh")
CLOSE = time(15, 0)
HOSE_VALUE = "https://api.hsx.vn/mk/api/v1/market/foreign-trading-value-report?fromDate={day}&toDate={day}"
HOSE_VOLUME = "https://api.hsx.vn/mk/api/v1/market/foreign-trading-volumn-report?fromDate={day}&toDate={day}"
NO_PROPRIETARY = {"status": "missing", "reason": "Chưa có nguồn miễn phí"}


class BriefStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "brief"

    def read(self, session: date | str) -> dict | None:
        key = session.isoformat() if isinstance(session, date) else str(session)
        try:
            date.fromisoformat(key)
            data = json.loads((self.root / f"{key}.json").read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        return data if isinstance(data, dict) else None

    def write(self, snapshot: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{date.fromisoformat(snapshot['session_date']).isoformat()}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def latest_session(now: datetime, cal) -> date | None:
    """Today once the market has closed (15:00) on a session day, otherwise the previous session."""
    local = now.astimezone(VN)
    day = local.date() if cal.is_session(local.date()) and local.time() >= CLOSE else local.date() - timedelta(days=1)
    while day >= cal.first:
        if cal.is_session(day):
            return day
        day -= timedelta(days=1)
    return None


def _missing(reason: str) -> dict:
    return {"status": "missing", "reason": reason}


def build_snapshot(*, session_date: date, previous_session: date | None, now: datetime, listing, board, series, hose_get, rss_get,
                   store: BriefStore) -> dict:
    sections: dict[str, dict] = {}
    try:
        sections["indices"] = index_rows({i: series(i) for i in IDS}, session_date=session_date)
    except Exception:
        sections["indices"] = _missing("Không đọc được giá chỉ số")
    try:
        info = listing()
        codes = info.get("icb_codes") or {}
        # The board leaves icb_code2 empty (checked 26/10/2026); the listing carries each symbol's level-2 code.
        records = [{**r, "icb_code2": r.get("icb_code2") or codes.get(r.get("symbol"))} for r in board(info["symbols"])]
        sections["board"] = summarise_board(records, session_date=session_date, icb_names=info["icb_names"])
    except Exception:
        sections["board"] = _missing("Không tải được bảng giá cả sàn")
    try:
        day = session_date.isoformat()
        sections["hose"] = parse_hose(hose_get(HOSE_VALUE.format(day=day)), hose_get(HOSE_VOLUME.format(day=day)))
    except Exception:
        sections["hose"] = _missing("Không kết nối được HOSE")
    items, failures = [], 0
    for source, url in FEEDS:
        try:
            items += parse_rss(rss_get(url), source)
        except Exception:
            failures += 1
    earlier = (store.read(session_date) or {}).get("news") or {}
    if earlier.get("status") == "ok":
        items += earlier.get("items", [])  # RSS only carries the latest items; keep what this session already had
    if failures == len(FEEDS) and earlier.get("status") != "ok":
        sections["news"] = _missing("Không tải được nguồn tin")
    else:
        since = datetime.combine(previous_session or session_date - timedelta(days=1), CLOSE, tzinfo=VN)
        sections["news"] = {"status": "ok", "items": window_items(items, since=since, until=now)}
    sections["proprietary"] = dict(NO_PROPRIETARY)
    previous = store.read(session_date) or {}
    for name, section in sections.items():
        if section.get("status") != "ok" and (previous.get(name) or {}).get("status") == "ok":
            sections[name] = previous[name]  # keep what an earlier wake-up already had
    snapshot = {"session_date": session_date.isoformat(), "updated_at": now.isoformat(), **sections}
    store.write(snapshot)
    return snapshot
