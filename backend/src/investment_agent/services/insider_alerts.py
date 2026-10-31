"""Giao dịch nội bộ mới: a Telegram note when a ticker the owner holds gets a new insider or major-shareholder notice on HOSE
(VNDirect's public list, the same as the ticker page). Run by the after-close schedule.

What was already seen per ticker is kept in data/alerts/insider.json (public notices only). A ticker's first run records what is
there without sending, so starting to hold a ticker never floods the chat; a notice dated more than 30 days back (a late
listing) is recorded, not sent; notices are marked seen only after the message went out.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from investment_agent.market.insider_deals import InsiderStore, insider_deals

RECENT = timedelta(days=30)
KIND = {"Mua": "Mua", "Bán": "Bán", "Đăng kí mua": "Đăng ký mua", "Đăng kí bán": "Đăng ký bán"}


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "insider.json"


def _key(deal: dict) -> str:
    return f"{deal['date']}|{deal['title']}"


def _shares(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _line(symbol: str, d: dict) -> str:
    when = date.fromisoformat(d["date"]).strftime("%d/%m")
    what = KIND.get(d["kind"] or "", "")
    volume = f" {_shares(d['shares'])} cp" if d["shares"] is not None else ""
    head = f"{symbol} · {when}: " + (f"{what}{volume} — " if what else "")
    return head + d["title"] + (f"\n  {d['url']}" if d["url"] else "")


def render(lines: list[str]) -> str:
    return ("Giao dịch nội bộ mới (mã đang nắm)\n" + "\n".join(f"• {ln}" for ln in lines)
            + "\n\"Đăng ký\" là ý định, chưa phải giao dịch. Nguồn: thông báo HOSE qua VNDirect. Không phải khuyến nghị.")


def insider_alerts_run(data_dir: Path, *, held: set[str], get: Callable[[str], str], send: Callable[[str], bool], now: datetime) -> dict:
    path = _path(data_dir)
    seen: dict[str, list[str]] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    store = InsiderStore(Path(data_dir))
    baseline, errors, pending, lines = [], [], {}, []
    since = (now.date() - RECENT).isoformat()
    for symbol in sorted(held):
        view = insider_deals(store, symbol, get=get, now=now)
        if view["reason"]:
            errors.append(symbol)
            continue
        keys = [_key(d) for d in view["deals"]]
        if symbol not in seen:
            seen[symbol] = keys
            baseline.append(symbol)
            continue
        known = set(seen[symbol])
        new = [d for d in view["deals"] if _key(d) not in known]
        seen[symbol] = sorted(known | {_key(d) for d in new if d["date"] < since})  # late listings: recorded, not sent
        fresh = sorted((d for d in new if d["date"] >= since), key=lambda d: d["date"])
        if fresh:
            pending[symbol] = [_key(d) for d in fresh]
            lines += [_line(symbol, d) for d in fresh]
    sent = bool(lines) and send(render(lines))
    if sent:
        for symbol, keys in pending.items():
            seen[symbol] = sorted(set(seen[symbol]) | set(keys))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(seen.items())), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return {"status": "ok", "baseline": baseline, "notices": len(lines), "sent": sent, "errors": errors}
