"""Nhắc Tháp tài sản: one Telegram note when a layer of Tháp tài sản changes between short, in range and over (owner, 21/11/2026).
Stocks are at market price and a layer is short or over only once it is more than 1 point outside its range, so a note means a real
move, not a session's noise. The first run only records the layers.

What was last said is kept in data/alerts/pyramid.json — the layers' statuses only, no amounts. It moves only after the note went out,
so a failed send is tried again next run. Describes the owner's figures; never says to buy or sell. Personal data; never sent to a model."""

import json
import os
from datetime import date
from pathlib import Path
from typing import Callable

from investment_agent.domain.asset_pyramid import _dong, _percent

LAYERS = ("deposit", "bond", "gold", "stocks", "crypto")
NAME = {"deposit": "Tiền gửi (gồm tiền mặt)", "bond": "Trái phiếu", "gold": "Vàng", "stocks": "Cổ phiếu", "crypto": "Tiền số"}
WORD = {"short": "thiếu", "ok": "đủ", "over": "vượt"}
FOOTER = ("Lệch không quá 1 điểm % không báo; cổ phiếu theo thị giá. Xem Tháp tài sản ở Hồ sơ → Tài sản. Tái cân bằng theo tỷ trọng, "
          "không phải khuyến nghị.")


def _state_path(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "pyramid.json"


def _save(data_dir: Path, state: dict[str, str]) -> None:
    path = _state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(state.items()))), encoding="utf-8")
    os.replace(tmp, path)


def _span(layer: dict) -> str:
    if layer["target_min"] == "0":
        return f"mục tiêu tối đa {_percent(layer['target_max'], 0)}"
    return f"mục tiêu {_percent(layer['target_min'], 0)[:-1]}–{_percent(layer['target_max'], 0)}"


def _line(layer: dict, before: str) -> str:
    detail = f"{_percent(layer['share'])} phần sau dự phòng, {_span(layer)}"
    if layer["status"] in ("short", "over") and layer["gap"]:
        detail += f"; {WORD[layer['status']]} {_dong(layer['gap'])}"
    return f"{NAME[layer['id']]}: {WORD[before]} → {WORD[layer['status']]} ({detail})"


def pyramid_alerts_run(data_dir: Path, *, pyramid: dict | None, send: Callable[[str], bool], today: date) -> dict:
    if pyramid is None:
        return {"changes": 0, "sent": False}
    path = _state_path(data_dir)
    before = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    layers = {l["id"]: l for l in pyramid["layers"] if l["id"] in LAYERS and l["share"] is not None}
    now = {k: l["status"] for k, l in layers.items()}
    if before is None:
        _save(data_dir, now)
        return {"changes": 0, "sent": False}
    lines = [_line(layers[k], before[k]) for k in LAYERS if k in now and before.get(k) in WORD and before[k] != now[k]]
    sent = bool(lines) and bool(send("\n".join([f"Tháp tài sản {today.strftime('%d/%m/%Y')}", *lines, FOOTER])))
    if (sent or not lines) and now != before:
        _save(data_dir, now)
    return {"changes": len(lines), "sent": sent}
