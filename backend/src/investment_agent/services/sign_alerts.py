"""Nhắc dấu hiệu phải thu mới: after the evening statement refresh, one Telegram note when a held ticker shows a receivable sign it did
not show before (Bảng dấu hiệu phải thu). The first run only records what is on now, and so did the banks' one-time arrival on the board (23/11/2026); a sign is told once, and again only after it
cleared. Signs of tickers not held are recorded and never told. The state is kept in data/alerts/receivable-signs.json."""

import json
import os
from pathlib import Path

STATE = "receivable-signs.json"
BANK = "Ngân hàng"


def check_signs(data_dir: Path, *, rows: list[dict], held: set[str], titles: dict[str, str], send) -> dict:
    path = Path(data_dir) / "alerts" / STATE
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    now = {r["symbol"]: sorted(k for k, v in r["signs"].items() if v is True) for r in rows}
    banks = {r["symbol"] for r in rows if r.get("sector") == BANK}
    if state is None:
        _write(path, {"symbols": now, **({"banks_joined": True} if banks else {})})
        return {"status": "baseline", "new": 0, "sent": False}
    before = state["symbols"]
    # a sign that could not be read this run (None) keeps what was recorded: not cleared, so not told again when it reads; this holds
    # for one sign as for a whole row whose file was cut short (review 23/11/2026 (2), (3))
    now = {r["symbol"]: sorted({k for k, v in r["signs"].items() if v is True}
                               | {k for k, v in r["signs"].items() if v is None and k in before.get(r["symbol"], [])}) for r in rows}
    unread = {r["symbol"] for r in rows if r["signs"] and all(v is None for v in r["signs"].values())}
    # the banks joined the board on 23/11/2026: their signs already on are recorded once, not told; any other ticker new to the board
    # (one the owner adds to the watchlist) is told as before (review 23/11/2026). A bank unread on that run is not recorded, so its
    # one silent run comes when it reads (review 23/11/2026 (3)).
    arriving = set() if state.get("banks_joined") else {s for s in banks if s not in before}
    waiting = arriving & unread
    news = {s: [k for k in keys if k not in before.get(s, [])] for s, keys in now.items()
            if s in held and s not in arriving and s not in unread}
    news = {s: ks for s, ks in news.items() if ks}
    detail = {r["symbol"]: r.get("details", {}) for r in rows}
    sent = False
    if news:
        lines = []
        for s, ks in news.items():
            parts = [titles.get(k, k) + (f" — {detail[s][k]}" if detail[s].get(k) else "") for k in ks]
            lines.append(f"• {s}: " + "; ".join(parts))
        # "báo cáo", not "phải thu": a bank's signs (provisions, accrued interest; owner 23/11/2026) come in the same note
        sent = bool(send("🔎 Dấu hiệu báo cáo mới ở mã đang nắm\n" + "\n".join(lines)
                         + "\nXem Phân tích ngành → Ngành theo quý → Dấu hiệu phải thu, và thuyết minh của mã."))
    # what Telegram did not take stays new for the held tickers, to be tried next run; everything else is recorded as it is now
    kept = {s: (before.get(s, []) if s in news and not sent else keys) for s, keys in now.items() if s not in waiting}
    joined = state.get("banks_joined") or (bool(banks) and not waiting)
    _write(path, {"symbols": kept, **({"banks_joined": True} if joined else {})})
    return {"status": "ok", "new": sum(len(ks) for ks in news.values()), "sent": sent}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
