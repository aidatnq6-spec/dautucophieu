"""Báo cáo quý mới: a Telegram note when a watched ticker's latest quarter first appears in the stored statements — the
quarter's parent profit against the same quarter a year before, the report-quality level when there is one, and for a bank
its NPL against the previous quarter and a reminder to enter loan groups, CASA and CAR.

Which quarter was announced for which ticker is kept in data/alerts/quarters.json (public figures only). The first run
records what is already there without sending, so a full refresh never floods the chat; a quarter is marked sent only after
the message went out.
"""

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Callable

from investment_agent.market.financial_ratios import FinancialRatioStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.watchlist import load_watchlist
from investment_agent.valuation.quality import _bn, _pct, report_quality

LEVEL = {"strong": "mạnh", "medium": "trung bình", "weak": "yếu"}


def _state_path(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "quarters.json"


def _save_state(data_dir: Path, sent: dict[str, str]) -> None:
    path = _state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(sent.items()))), encoding="utf-8")
    os.replace(tmp, path)


def _label(quarter: str) -> str:
    return f"Q{quarter[-1]}/{quarter[:4]}"


def _line(symbol: str, quarter: str, record: dict, sector: str | None, ratios: dict | None) -> str:
    quarters = record.get("quarters", {})
    now = quarters.get(quarter, {}).get("npat")
    before = quarters.get(f"{int(quarter[:4]) - 1}{quarter[4:]}", {}).get("npat")
    parts = [f"{symbol} · {_label(quarter)}: "]
    if now is None:
        parts[0] += "chưa có lợi nhuận quý"
    else:
        a = Decimal(now)
        if before and Decimal(before) > 0:
            change = a / Decimal(before) - 1
            parts[0] += f"LNST quý {_bn(a)} ({'+' if change >= 0 else ''}{_pct(change)} so với cùng kỳ)"
        else:
            parts[0] += f"LNST quý {_bn(a)} (chưa có cùng kỳ năm trước)"
    if ratios and ratios.get("kind") == "bank":
        dates = sorted(ratios["quarters"])
        end = f"{quarter[:4]}-{int(quarter[-1]) * 3:02d}-"
        current = next((d for d in dates if d.startswith(end)), None)
        if current and (npl := ratios["quarters"][current].get("BAD_LOANS_RATIO_AQ")):
            earlier = [d for d in dates if d < current]
            prev = ratios["quarters"][earlier[-1]].get("BAD_LOANS_RATIO_AQ") if earlier else None
            parts.append(f"NPL {_pct(Decimal(npl), 2)}" + (f" (quý trước {_pct(Decimal(prev), 2)})" if prev else ""))
    q = report_quality(record, sector, ratios)
    if (f := q.get("f_score")) and f.get("level"):
        parts.append(f"{f.get('title') or 'F-Score'} {f['score']}/{f['evaluated']} ({LEVEL[f['level']]})")
    text = " · ".join(parts)
    if sector == "Ngân hàng":
        text += f"\n  → nhập nợ nhóm 1–5, CASA, CAR trên trang mã {symbol} (Số liệu ngân hàng)"
    return text


def render(lines: list[str]) -> str:
    return "Báo cáo quý mới\n" + "\n".join(f"• {ln}" for ln in lines) + "\nXem chi tiết ở Định giá và trang từng mã. Không phải khuyến nghị."


def quarter_alerts_run(data_dir: Path, *, send: Callable[[str], bool]) -> dict:
    data_dir = Path(data_dir)
    store, ratio_store = FundamentalsStore(data_dir / "fundamentals"), FinancialRatioStore(data_dir / "financial-ratios")
    sectors = load_sectors(data_dir)[0]
    seen = {}
    for s in load_watchlist(data_dir).symbols:
        record = store.read(s)
        if record and (latest := record.get("latest_quarter_seen")):
            seen[s] = (latest["quarter"], record)
    path = _state_path(data_dir)
    if not path.is_file():
        _save_state(data_dir, {s: q for s, (q, _) in seen.items()})
        return {"baseline": True, "alerts": 0, "sent": False}
    sent = json.loads(path.read_text(encoding="utf-8"))
    pending = {s: (q, r) for s, (q, r) in seen.items() if sent.get(s) != q}
    if not pending:
        return {"baseline": False, "alerts": 0, "sent": False}
    lines = [_line(s, q, r, sectors.get(s), ratio_store.read(s)) for s, (q, r) in sorted(pending.items())]
    delivered = bool(send(render(lines)))
    if delivered:
        _save_state(data_dir, {**sent, **{s: q for s, (q, _) in pending.items()}})
    return {"baseline": False, "alerts": len(pending), "sent": delivered}
