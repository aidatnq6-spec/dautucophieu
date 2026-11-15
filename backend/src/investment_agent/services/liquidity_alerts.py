"""Nhắc thanh khoản và tỷ giá over Telegram, after each macro update: the overnight interbank rate up more than 1 point in 5 sessions,
or the Vietcombank selling rate less than 1% below the band's ceiling. Each is sent once when it starts; while it lasts nothing more is
sent; once it clears, it may be sent again. Public figures only; the state is kept in data/liquidity-alerts.json."""

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.liquidity import JUMP_SESSIONS, central_view, interbank_view
from investment_agent.market.leading import MacroStore

STATE = "liquidity-alerts.json"


def _num(v: str, digits: int = 2) -> str:
    text = f"{Decimal(v):,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return text.rstrip("0").rstrip(",") if "," in text else text


def _dmy(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def _active(data_dir: Path, today: date) -> dict[str, str]:
    store = MacroStore(data_dir)
    dec = lambda i: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(i)]  # noqa: E731
    out = {}
    on = dec("vn_interbank_on")
    jump = interbank_view({"vn_interbank_on": on})["jump"]
    if jump:
        out["interbank_jump"] = (f"• Lãi suất liên ngân hàng qua đêm tăng {_num(jump['change'])} điểm % trong {JUMP_SESSIONS} phiên: "
                                 f"{_num(str(on[-1][1]))}% ngày {_dmy(on[-1][0].isoformat())} (từ {_dmy(jump['from'])}).")
    fx = central_view(dec("usd_vnd_central"), vcb=dec("usd_vnd_vcb"), today=today)
    if fx["near_ceiling"]:
        room = _num(str(Decimal(fx["room"]) * 100))
        out["near_ceiling"] = (f"• Tỷ giá bán Vietcombank {_num(fx['vcb']['value'], 0)} đ/USD ngày {_dmy(fx['vcb']['date'])}, còn {room}% tới trần "
                               f"{_num(fx['ceiling'], 0)} (tỷ giá trung tâm {_num(fx['latest']['value'], 0)}, biên độ ±5%).")
    return out


def _read(path: Path) -> list[str]:
    return json.loads(path.read_text(encoding="utf-8")).get("active", []) if path.is_file() else []


def check_liquidity(data_dir: Path, *, send, today: date) -> dict:
    path = Path(data_dir) / STATE
    active = _active(Path(data_dir), today)
    before = set(_read(path))
    new = [k for k in active if k not in before]
    sent = bool(new) and bool(send("⚠️ Thanh khoản và tỷ giá\n" + "\n".join(active[k] for k in new)))
    # what is still on stays marked; what cleared is dropped, so it can be sent again; a note Telegram did not take is tried next run
    keep = sorted((set(active) & before) | (set(new) if sent else set()))
    if keep != sorted(before):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"active": keep, "on": today.isoformat()}), encoding="utf-8")
        os.replace(tmp, path)
    return {"status": "ok", "new": len(new), "sent": sent}
