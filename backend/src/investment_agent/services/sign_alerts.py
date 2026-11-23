"""Nhắc dấu hiệu phải thu mới: after the evening statement refresh, one Telegram note when a held ticker shows a receivable sign it did
not show before (Bảng dấu hiệu phải thu). The first run only records what is on now, and so does a ticker's first run on the board; a sign is told once, and again only after it
cleared. Signs of tickers not held are recorded and never told. The state is kept in data/alerts/receivable-signs.json."""

import json
import os
from pathlib import Path

STATE = "receivable-signs.json"


def check_signs(data_dir: Path, *, rows: list[dict], held: set[str], titles: dict[str, str], send) -> dict:
    path = Path(data_dir) / "alerts" / STATE
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    now = {r["symbol"]: sorted(k for k, v in r["signs"].items() if v is True) for r in rows}
    if state is None:
        _write(path, {"symbols": now})
        return {"status": "baseline", "new": 0, "sent": False}
    before = state["symbols"]
    # a ticker new to the board (banks joined it on 23/11/2026) is only recorded on its first run, like the board's own first run
    news = {s: [k for k in keys if k not in before[s]] for s, keys in now.items() if s in held and s in before}
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
    kept = {s: (before.get(s, []) if s in news and not sent else keys) for s, keys in now.items()}
    _write(path, {"symbols": kept})
    return {"status": "ok", "new": sum(len(ks) for ks in news.values()), "sent": sent}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
