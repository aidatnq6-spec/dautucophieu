"""Thuyết minh TSCĐ nhập tay: the owner's record per ticker and the Việc cần xem lines of projects due. Personal data, never sent to a model."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from investment_agent.domain.fixed_asset_notes import due_view, incentive_text, incentives_view
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.records import read_version

KIND = "cip_project"
TAX_KIND = "tax_incentive"


def incentive_lines(repo, owner, data_dir: Path, *, today: date) -> list[tuple[str, str]]:
    """(symbol, text) of each tax incentive whose last year is this one (Ưu đãi thuế, 25/11/2026)."""
    out = []
    for symbol in load_watchlist(Path(data_dir)).symbols:
        record = read_version(repo, owner, "settings", record_id(symbol), None)
        for i in incentives_view((record.payload if record else {}).get("tax_incentives", []), today=today):
            if i["state"] == "ending":
                out.append((symbol, f"{symbol}: ưu đãi thuế của {i['entity']} ({incentive_text(i)}) hết trong năm {i['until']}; từ năm sau thuế suất thực tế "
                                    "có thể tăng. Xem thuyết minh thuế TNDN của báo cáo năm."))
    return out


def record_id(symbol: str) -> str:
    return f"fixed_asset_notes_{symbol}"


def read_notes(repo, owner, symbol: str):
    record = read_version(repo, owner, "settings", record_id(symbol), None)
    payload = record.payload if record else {}
    return record, payload.get("projects", []), payload.get("ranges", {"period": None, "groups": {}})


def _quarter(q: str) -> str:
    return f"Q{q[-1]}/{q[2:4]}"


def _period(p: str) -> str:
    return p if len(p) == 4 else _quarter(p)


def _ty(v: str | None) -> str:
    if v is None:
        return "chưa có"
    n = (Decimal(v) / 10**9).quantize(Decimal(1), ROUND_HALF_UP)
    return f"{int(n):,}".replace(",", ".") + " tỷ"


def _line(symbol: str, p: dict) -> str:
    due, read = p["at_due"], p["at_read"]
    cip_then = f" (kỳ đã đọc {_period(read['period'])}: {_ty(read['cip'])})" if read else ""
    cost_then = f" ({_ty(read['ppe_gross'])})" if read else ""
    q = _quarter(p["due"])
    return (f"{symbol}: dự án {p['name']} đến quý hoàn thành dự kiến {q}. XDCB dở dang cuối {q}: {_ty(due['cip'])}{cip_then}; "
            f"nguyên giá TSCĐ hữu hình: {_ty(due['ppe_gross'])}{cost_then}. Xác nhận đã hoàn thành hoặc lùi hạn.")


def due_lines(repo, owner, data_dir: Path, *, today: date) -> list[tuple[str, str]]:
    """(symbol, text) of each open project whose quarter's report is stored, until the owner confirms it done or postpones it."""
    store, out = StatementStore(Path(data_dir) / "statements"), []
    for symbol in load_watchlist(Path(data_dir)).symbols:
        _, projects, _ = read_notes(repo, owner, symbol)
        if projects:
            out += [(symbol, _line(symbol, p)) for p in due_view(projects, store.read(symbol) or {}, today=today) if p["state"] == "due"]
    return out
