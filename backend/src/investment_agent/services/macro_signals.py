"""Đèn tín hiệu rủi ro vĩ mô after each macro sync: compute the lights, compare with the last run's levels (data/macro/_signals.json)
and send one Telegram message when any light changed level (spec 2026-11-21). The first run only records the levels; a message that
did not go out leaves the levels as they were, so the next run tries again."""

import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.macro_signals import macro_signals, signal_changes
from investment_agent.market.leading import MacroStore

SERIES = ("factor_oil", "factor_usd", "usd_vnd_free", "usd_vnd_vcb", "foreign_net", "vn_interbank_on")


def load_series(data_dir: Path) -> dict[str, list[tuple[date, Decimal]]]:
    store = MacroStore(Path(data_dir))
    return {k: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(k)] for k in SERIES}


def signals_run(data_dir: Path, *, today: date, send) -> dict:
    current = macro_signals(load_series(data_dir), today=today)
    path = Path(data_dir) / "macro" / "_signals.json"
    previous = json.loads(path.read_text(encoding="utf-8"))["levels"] if path.is_file() else None
    lines = signal_changes(previous, current)
    sent = False
    if lines:
        sent = bool(send("ĐÈN TÍN HIỆU RỦI RO VĨ MÔ\n" + "\n".join(f"- {line}" for line in lines)
                         + "\nChỉ mô tả dữ liệu, không phải khuyến nghị. Chi tiết ở trang Vĩ mô."))
    levels = {s["id"]: s["level"] for s in current}
    if lines and not sent:
        return {"levels": levels, "changes": len(lines), "sent": False, "first_run": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"levels": levels, "at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    os.replace(tmp, path)
    return {"levels": levels, "changes": len(lines), "sent": sent, "first_run": previous is None}
