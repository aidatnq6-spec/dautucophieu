"""Chênh lệch vàng SJC so với thế giới: the daily gap kept as the macro indicator sjc_gap_pct, the owner's threshold
(settings/sjc_gap_alert), and one Telegram note when the gap goes above the threshold and one when it is back under."""

import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from investment_agent.market.leading import MacroStore

RECORD = ("settings", "sjc_gap_alert")
STATE = ("alerts", "sjc-gap.json")
INDICATOR = "sjc_gap_pct"


def _vn(v: Decimal) -> str:
    return format(v.normalize(), "f").replace(".", ",")


def read_threshold(repo, owner) -> tuple[Decimal | None, int]:
    from investment_agent.services.records import read_version
    record = read_version(repo, owner, *RECORD, None)
    if not record:
        return None, 0
    value = record.payload.get("threshold")
    return (Decimal(value) if value is not None else None), record.version


def parse_threshold(text: str | None) -> Decimal | None:
    """'12,5' or '12.5' → 12.5; None or empty turns the alert off; anything outside 0–100 is refused (ValueError)."""
    if text is None or not str(text).strip():
        return None
    try:
        value = Decimal(str(text).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("not_a_number") from exc
    if not (Decimal(0) < value < Decimal(100)):
        raise ValueError("out_of_range")
    return value.normalize()


def check_sjc_gap(data_dir: Path, *, threshold: Decimal | None, send: Callable[[str], bool]) -> dict:
    if threshold is None:
        return {"status": "skipped", "reason": "no_threshold", "sent": 0}
    obs = MacroStore(Path(data_dir)).read(INDICATOR)
    if not obs:
        return {"status": "skipped", "reason": "no_figure", "sent": 0}
    path = Path(data_dir).joinpath(*STATE)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"above": False}
    latest, day = Decimal(obs[-1]["value"]), date.fromisoformat(obs[-1]["date"]).strftime("%d/%m/%Y")
    above, sent = latest >= threshold, 0
    if above != state["above"]:
        text = (f"Chênh lệch vàng miếng SJC so với giá thế giới quy đổi lên {_vn(latest)}% ({day}), vượt ngưỡng {_vn(threshold)}% bạn đặt. "
                "Xem trang Vĩ mô." if above else
                f"Chênh lệch vàng miếng SJC so với giá thế giới quy đổi đã xuống {_vn(latest)}% ({day}), dưới ngưỡng {_vn(threshold)}% bạn đặt.")
        if send(text):
            sent = 1
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"above": above, "on": obs[-1]["date"]}), encoding="utf-8")
            os.replace(tmp, path)
    return {"status": "ok", "sent": sent, "above": above}
