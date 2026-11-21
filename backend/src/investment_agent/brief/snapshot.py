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
from .session_shape import hose_liquidity, index_session

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


def _signals(sections: dict, shares, store: BriefStore, sessions_before: list[date], previous: dict | None,
             vn30_weights=lambda: {}) -> dict:
    """Tín hiệu phiên (brief.signals) from this snapshot's board, index row and volume, and the volume ratios of the sessions before."""
    from decimal import Decimal

    from .signals import asia_vs_index, index_pull, session_signals, vn30_multipliers
    board = sections.get("board") or {}
    vn = next((r for r in (sections.get("indices") or {}).get("rows", []) if r.get("id") == "VNINDEX" and r.get("status") == "ok"), None)
    change = Decimal(vn["change"]) if vn else None
    pull = {"status": "missing", "reason": "Chưa có bảng giá cả sàn hoặc VN-Index"}
    if board.get("status") == "ok" and vn:
        try:
            got = shares(list(board["symbols"]))
        except Exception:
            got = {}
        pull = index_pull(board["symbols"], got, change=change, close=Decimal(vn["close"]))
    if pull["status"] == "missing" and previous and (previous.get("pull") or {}).get("status") in ("ok", "mismatch"):
        pull = previous["pull"]  # an earlier wake-up of this session had the shares
    ratios = []
    for day in sessions_before[-25:]:
        volume = (((store.read(day) or {}).get("index_session") or {}).get("volume") or {})
        ratios.append(Decimal(volume["ratio20"]) if volume.get("status") == "ok" and volume.get("ratio20") else None)
    rest = session_signals(index_change=change, breadth=board.get("breadth") if board.get("status") == "ok" else None,
                           volume=((sections.get("index_session") or {}).get("volume")), earlier_ratios=ratios)
    vn30 = next((r for r in (sections.get("indices") or {}).get("rows", []) if r.get("id") == "VN30" and r.get("status") == "ok"), None)
    pull_vn30 = {"status": "missing", "reason": "Chưa có trọng số VN30 từ thông báo của HOSE"}
    if board.get("status") == "ok" and vn30:
        try:
            weights = vn30_multipliers(vn30_weights())
        except Exception:
            weights = {}
        if weights:
            pull_vn30 = index_pull({s: r for s, r in board["symbols"].items() if s in weights}, weights,
                                   change=Decimal(vn30["change"]), close=Decimal(vn30["close"]))
    if pull_vn30["status"] == "missing" and previous and (previous.get("pull_vn30") or {}).get("status") in ("ok", "mismatch"):
        pull_vn30 = previous["pull_vn30"]
    return {"status": "ok", "pull": pull, "pull_vn30": pull_vn30, "asia": asia_vs_index(change, sections.get("asia")), **rest}


def build_snapshot(*, session_date: date, previous_session: date | None, now: datetime, listing, board, series, hose_get, rss_get,
                   store: BriefStore, earlier: list[date] = (), index_bars=lambda: {}, shares=lambda symbols: {},
                   vn30_weights=lambda: {}, asia=lambda: None, us=lambda: None) -> dict:
    """earlier: the sessions before session_date on the trading calendar, ascending; index_bars(): VN-Index daily bars by session;
    shares(symbols): shares outstanding by symbol, for Tín hiệu phiên (mã kéo chỉ số)."""
    sections: dict[str, dict] = {}
    sessions_before = list(earlier)
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
    try:
        sections["index_session"] = index_session(index_bars(), session_date=session_date, earlier=list(earlier))
    except Exception:
        sections["index_session"] = _missing("Không đọc được nến VN-Index")
    try:  # Chứng khoán châu Á (market.asia_indices): read with the snapshot, shown with the time it was read
        sections["asia"] = asia() or _missing("Chưa đọc chỉ số châu Á")
    except Exception:
        sections["asia"] = _missing("Không đọc được chỉ số châu Á")
    try:  # Chứng khoán Mỹ (market.us_indices): FRED's closes as macro-sync stored them, each with its session date (21/11/2026)
        got = us()
        sections["us"] = {"status": "ok", **got} if got and got.get("rows") else _missing("Chưa có chỉ số Mỹ từ FRED")
    except Exception:
        sections["us"] = _missing("Không đọc được chỉ số Mỹ")
    try:  # Cú sốc hôm nay (domain.history_stats): VN-Index's shocks of the session, read from its stored closes since 2000 (21/11/2026)
        from decimal import Decimal

        from investment_agent.domain.history_stats import shocks_today
        closes = sorted((t.date(), Decimal(str(v))) for t, v in series("VNINDEX"))
        sections["shocks"] = shocks_today(closes, session=session_date)
    except Exception:
        sections["shocks"] = _missing("Không tính được cú sốc của VN-Index")
    try:
        sections["hose_liquidity"] = hose_liquidity(sections["hose"], earlier=list(earlier), hose_get=hose_get)
    except Exception:
        sections["hose_liquidity"] = _missing("Không kết nối được HOSE")
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
    sections["signals"] = _signals(sections, shares, store, sessions_before, previous.get("signals"), vn30_weights)
    snapshot = {"session_date": session_date.isoformat(), "updated_at": now.isoformat(), **sections}
    store.write(snapshot)
    return snapshot
