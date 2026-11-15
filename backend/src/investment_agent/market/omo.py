"""Nghiệp vụ thị trường mở: the State Bank's open-market results, one session at a time. The page shows only the latest session and
is replaced the next one, so history is what this store has kept from each run (data/omo.json); a session missed is not filled in."""

import json
import os
import re
from datetime import date
from pathlib import Path

from investment_agent.market.leading import MacroError, _plain, _text, _vn_number

SBV_OMO = "https://sbv.gov.vn/vi/nghi%E1%BB%87p-v%E1%BB%A5-th%E1%BB%8B-tr%C6%B0%E1%BB%9Dng-m%E1%BB%9F"
# Mua kỳ hạn (repos) and Mua hẳn put money in; Bán hẳn (State Bank bills) takes it out.
KINDS = {"mua kỳ hạn": "repo", "mua hẳn": "outright", "bán hẳn": "bill", "bán kỳ hạn": "reverse"}
_DATE = re.compile(r"Ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})")
_TERM = re.compile(r"(?i)kỳ hạn\s+(\d{1,3})\s+ngày")


def parse_omo(page: str) -> dict:
    start = page.find("KẾT QUẢ ĐẤU THẦU THỊ TRƯỜNG MỞ")
    end = page.find("</table>", start)
    if start < 0 or end < 0:
        raise MacroError("omo_unreadable")
    block = page[start:end]
    d = _DATE.search(_text(block))
    if not d:
        raise MacroError("omo_undated")
    rows, group, total = [], None, None
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", block):
        cells = [_text(c).strip() for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
        if len(cells) == 1:
            group = cells[0]
        elif cells and cells[0].lower().startswith("tổng cộng") and len(cells) >= 3:
            total = _plain(_vn_number(cells[2])) if cells[2] else None
        elif len(cells) == 4 and _TERM.search(cells[0]) and group:
            rows.append({"kind": KINDS.get(group.lower(), "other"), "group": group, "term_days": int(_TERM.search(cells[0]).group(1)),
                         "members": cells[1], "volume": _plain(_vn_number(cells[2])), "rate": _plain(_vn_number(cells[3]))})
    if not rows:
        raise MacroError("omo_no_rows")
    return {"date": date(int(d.group(3)), int(d.group(2)), int(d.group(1))).isoformat(), "rows": rows, "total": total}


class OmoStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "omo.json"

    def sessions(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))["sessions"] if self.path.is_file() else []

    def upsert(self, session: dict) -> None:
        by_day = {s["date"]: s for s in self.sessions()}
        by_day[session["date"]] = session
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"sessions": [by_day[k] for k in sorted(by_day)]}, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)


def omo_sync(store: OmoStore, *, get) -> str:
    try:
        store.upsert(parse_omo(get(SBV_OMO)))
        return "ok"
    except Exception as exc:
        return f"error:{type(exc).__name__}"
