"""Số đã công bố bị sửa (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-phai-thu-ho-to-design.md).

Each weekly statements sync re-reads two years of a ticker from VNDirect and used to overwrite what it had. Now a closed period (not the
ticker's latest) whose figure changes on a watched line by more than both 1% and 1 tỷ is logged in data/statement-revisions/<MÃ>.json:
period, line, old, new, the day seen. The figures are kept as the source gave them; no cause is inferred (a restatement or a source
fixing its entry). Only changes from now on are caught, and only within the two years each sync re-reads. Public figures."""

import json
import os
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable

LINES = {"npat_parent": "LNST công ty mẹ", "pbt": "LNTT", "equity": "Vốn chủ sở hữu", "bad_debt_st": "Dự phòng phải thu ngắn hạn",
         "bad_debt_lt": "Dự phòng phải thu dài hạn",
         "inventory_provision": "Dự phòng giảm giá hàng tồn kho",  # Dự phòng chốt khi kiểm toán (owner, 23/11/2026)
         # Doanh thu, giá vốn (owner, 25/11/2026): a restatement can move costs back into earlier years' cost of sales (HAG)
         "revenue": "Doanh thu thuần", "cogs": "Giá vốn hàng bán", "gross_profit": "Lợi nhuận gộp"}
SHARE, FLOOR = Decimal("0.01"), Decimal("1000000000")
DIR, TOLD = "statement-revisions", ("alerts", "statement-revisions.json")
FOOTER = "Có thể do điều chỉnh hồi tố hoặc nguồn sửa lỗi nhập; xem thuyết minh và báo cáo kiểm toán."


def find_revisions(old: dict[str, dict], new: dict[str, dict]) -> list[dict]:
    """old, new: period → line → figure. The latest stored period is still moving and is left out."""
    if not old:
        return []
    latest = max(old)
    out = []
    for period in sorted(set(old) & set(new)):
        if period == latest:
            continue
        for line in sorted(LINES):
            a, b = old[period].get(line), new[period].get(line)
            if a is None or b is None:
                continue
            diff = abs(Decimal(b) - Decimal(a))
            if diff > SHARE * abs(Decimal(a)) and diff > FLOOR:
                out.append({"period": period, "line": line, "old": a, "new": b})
    return out


def _path(root: Path, symbol: str) -> Path:
    return Path(root) / DIR / f"{symbol}.json"


def read_revisions(root: Path, symbol: str) -> list[dict]:
    path = _path(root, symbol)
    return json.loads(path.read_text(encoding="utf-8"))["revisions"] if path.is_file() else []


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def record_revisions(root: Path, symbol: str, found: list[dict], *, kind: str, seen_on: date) -> int:
    """Adds what is not logged yet (the same period, line and new figure is one revision); returns how many were added."""
    have = read_revisions(root, symbol)
    keys = {(r["kind"], r["period"], r["line"], r["new"]) for r in have}
    added = [{**r, "kind": kind, "seen_on": seen_on.isoformat()} for r in found if (kind, r["period"], r["line"], r["new"]) not in keys]
    if added:
        _write(_path(root, symbol), {"symbol": symbol, "revisions": have + added})
    return len(added)


def _ty(v: str) -> str:
    x = (Decimal(v) / FLOOR).quantize(Decimal("0.1"), ROUND_HALF_UP).normalize()
    return f"{format(x, 'f').replace('.', ',').replace('-', '−')} tỷ"


def describe(symbol: str, r: dict) -> str:
    when = f"năm {r['period']}" if r["kind"] == "years" else f"quý {r['period'][-1]}/{r['period'][:4]}"
    seen = date.fromisoformat(r["seen_on"])
    return f"{symbol} {when}, {LINES[r['line']]}: {_ty(r['old'])} → {_ty(r['new'])} (thấy {seen:%d/%m/%Y})"


def revisions_note_run(root: Path, *, held: set[str], send: Callable[[str], bool], today: date) -> dict:
    """The held tickers' revisions not told yet, one note; marked only once sent."""
    told_path = Path(root).joinpath(*TOLD)
    told = set(json.loads(told_path.read_text(encoding="utf-8"))) if told_path.is_file() else set()
    fresh = []
    for symbol in sorted(held):
        for r in read_revisions(root, symbol):
            key = f"{symbol}|{r['kind']}|{r['period']}|{r['line']}|{r['new']}"
            if key not in told:
                fresh.append((key, describe(symbol, r)))
    if not fresh:
        return {"new": 0, "sent": False}
    if not send("\n".join(["Số đã công bố bị sửa", *(t for _, t in fresh), FOOTER])):
        return {"new": len(fresh), "sent": False}
    _write(told_path, sorted(told | {k for k, _ in fresh}))
    return {"new": len(fresh), "sent": True}
