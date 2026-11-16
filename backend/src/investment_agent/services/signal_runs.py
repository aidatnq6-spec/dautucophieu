"""Nhắc chuỗi tín hiệu: one Telegram note when a session signal has held for several sessions in a row — thin trading five sessions,
a green index over falling stocks (or the reverse) three, VN-Index against the Asian markets three — counted from the newest stored
snapshot back as the "5 phiên gần nhất" table counts them. Each run is told once, named by the session it began; a longer run is not
told again, a new one is. Public market figures only."""

import json
import os
from pathlib import Path
from typing import Callable

from investment_agent.brief.snapshot import BriefStore
from investment_agent.brief.view import recent_signals

RUNS = {"low_liquidity": 5, "green_over_red": 3, "red_over_green": 3, "asia_against": 3}
STATE = ("alerts", "signal-runs.json")
LOOK_BACK = 15
TESTS = {"low_liquidity": lambda r: r["low_liquidity"] is True, "green_over_red": lambda r: r["breadth"] == "green_over_red",
         "red_over_green": lambda r: r["breadth"] == "red_over_green", "asia_against": lambda r: r["asia"] == "against"}
WORDS = {"low_liquidity": ("thanh khoản thấp", "khối lượng khớp dưới 80% trung bình 20 phiên"),
         "green_over_red": ("xanh vỏ đỏ lòng", "VN-Index tăng nhưng số mã giảm áp đảo số mã tăng"),
         "red_over_green": ("đỏ vỏ xanh lòng", "VN-Index giảm nhưng số mã tăng áp đảo số mã giảm"),
         "asia_against": ("VN-Index ngược chiều châu Á", "đa số thị trường châu Á cùng phiên đi chiều kia")}


def _dm(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}"


def check_runs(data_dir: Path, *, send: Callable[[str], bool]) -> dict:
    store = BriefStore(Path(data_dir))
    days = sorted(p.stem for p in store.root.glob("*.json")) if store.root.is_dir() else []
    if not days:
        return {"status": "skipped", "reason": "no_snapshot", "sent": 0}
    rows = recent_signals(Path(data_dir), days[-1], n=LOOK_BACK)
    path = Path(data_dir).joinpath(*STATE)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"told": []}
    sent = 0
    for kind, length in RUNS.items():
        run = []
        for r in rows:  # newest first
            if not r["known"] or not TESTS[kind](r):
                break
            run.append(r)
        if len(run) < length:
            continue
        key = f"{kind}:{run[-1]['date']}"
        if key in state["told"]:
            continue
        name, why = WORDS[kind]
        text = f"Tín hiệu phiên kéo dài: {name} {len(run)} phiên liền ({_dm(run[-1]['date'])}–{_dm(run[0]['date'])}): {why}. Xem Bản tin sau phiên."
        if send(text):
            state["told"] = [*state["told"], key][-100:]
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state), encoding="utf-8")
            os.replace(tmp, path)
            sent += 1
    return {"status": "ok", "sent": sent}
