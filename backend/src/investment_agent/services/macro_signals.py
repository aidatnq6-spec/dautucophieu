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

SERIES = ("factor_oil", "factor_usd", "usd_vnd_free", "usd_vnd_vcb", "usd_vnd_central", "us10y", "foreign_net", "vn_interbank_on", "vn_pmi")
PE_SERIES = "VNINDEX-pe-1d"  # VNDirect's daily P/E of VN-Index, kept by index-valuation-sync


def load_series(data_dir: Path) -> dict[str, list[tuple[date, Decimal]]]:
    store = MacroStore(Path(data_dir))
    from investment_agent.market.series import SeriesStore
    out = {k: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(k)] for k in SERIES}
    out["vnindex_pe"] = [(date.fromisoformat(t[:10]), Decimal(v)) for t, v in SeriesStore(Path(data_dir) / "index-valuation").points(PE_SERIES)]
    return out


FOOTER = "Chỉ mô tả dữ liệu, không phải khuyến nghị. Chi tiết ở trang Vĩ mô."


def signals_note(data_dir: Path, *, today: date):
    """(the lights' section or None, a summary, commit(sent)): commit keeps the levels unless a changed light's note did not go out."""
    current = macro_signals(load_series(data_dir), today=today)
    path = Path(data_dir) / "macro" / "_signals.json"
    previous = json.loads(path.read_text(encoding="utf-8"))["levels"] if path.is_file() else None
    lines = signal_changes(previous, current)
    levels = {s["id"]: s["level"] for s in current}
    text = "ĐÈN TÍN HIỆU RỦI RO VĨ MÔ\n" + "\n".join(f"- {line}" for line in lines) if lines else None

    def commit(sent: bool) -> dict:
        if lines and not sent:
            return {"levels": levels, "changes": len(lines), "sent": False, "first_run": False}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"levels": levels, "at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
        os.replace(tmp, path)
        return {"levels": levels, "changes": len(lines), "sent": sent, "first_run": previous is None}
    return text, commit


def signals_run(data_dir: Path, *, today: date, send) -> dict:
    text, commit = signals_note(data_dir, today=today)
    return commit(bool(send(text + "\n" + FOOTER)) if text else False)
