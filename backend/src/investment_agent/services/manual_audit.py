"""Rà dữ liệu nhập tay: the macro figures entered by hand that break the rules the app keeps — a monthly figure not at its month's end
(the day it was typed), one beside or equal to an automatic figure, a session figure on a day without a HOSE session. Listed with why
for Bản tin tuần; nothing is changed here, the owner decides. Public macro figures only."""

import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.market.leading import MacroStore
from investment_agent.market.sessions import is_session


def _dmy(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _vn(value: str) -> str:
    return format(Decimal(value).normalize(), "f").replace(".", ",")


def _month_before(day: date) -> str:
    return f"{day.year - 1}-12" if day.month == 1 else f"{day.year}-{day.month - 1:02d}"


def audit_manual(data_dir: Path, indicators: list[dict]) -> list[dict]:
    store, found = MacroStore(Path(data_dir)), []
    for spec in indicators:
        obs = store.read(spec["id"])
        auto = [o for o in obs if o.get("entry") != "manual"]
        for o in (x for x in obs if x.get("entry") == "manual"):
            day, reasons = date.fromisoformat(o["date"]), []
            if spec.get("period") == "month":
                if day.day != calendar.monthrange(day.year, day.month)[1]:
                    reasons.append("không ghi vào ngày cuối tháng")
                same = [a for a in auto if a["date"][:7] == o["date"][:7]]
                before = [a for a in auto if a["date"][:7] == _month_before(day) and Decimal(a["value"]) == Decimal(o["value"])]
                if same and Decimal(same[-1]["value"]) == Decimal(o["value"]):
                    reasons.append(f"trùng giá trị với số tự động ngày {_dmy(same[-1]['date'])}")
                elif same:
                    reasons.append(f"cùng tháng đã có số tự động {_vn(same[-1]['value'])} ({_dmy(same[-1]['date'])})")
                elif before:
                    reasons.append(f"trùng giá trị với số tự động ngày {_dmy(before[-1]['date'])}")
            elif spec.get("period") == "session" and not is_session(day):
                reasons.append("ngày không có phiên giao dịch")
            if reasons:
                found.append({"indicator": spec["id"], "label": spec["label"], "date": o["date"], "value": o["value"], "reasons": reasons})
    return found
