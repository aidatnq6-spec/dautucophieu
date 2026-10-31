"""Bản tin tuần: one Telegram note on the weekend about the Monday–Friday just past — the portfolio's time-weighted return against
VN-Index, foreign net trading on HOSE summed over the session snapshots, each held ticker's weekly change, insider notices of held
tickers, known corporate events of the next seven days, and price alerts that fired. Built from data the app already keeps; a
missing piece is named, never estimated. Sent once per week (data/alerts/weekly.json), retried until it goes out.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable

from investment_agent.market.corporate_events import REMINDED_KINDS, describe

VN = timezone(timedelta(hours=7))
OPS = {"above": "≥", "below": "≤"}
KIND = {"Mua": "Mua", "Bán": "Bán", "Đăng kí mua": "Đăng ký mua", "Đăng kí bán": "Đăng ký bán"}
NEXT_DAYS = 7


def week_of(today: date) -> tuple[date, date]:
    """Monday and Friday of the last full week on or before today (a weekday counts its own week)."""
    friday = today - timedelta(days=(today.weekday() - 4) % 7)
    return friday - timedelta(days=4), friday


def _dm(d: date | str) -> str:
    d = date.fromisoformat(d[:10]) if isinstance(d, str) else d
    return d.strftime("%d/%m")


def _num(value: Decimal, digits: int = 2) -> str:
    q = value.quantize(Decimal(1).scaleb(-digits), ROUND_HALF_UP)
    whole, _, frac = f"{abs(q):,.{digits}f}".partition(".")
    return ("−" if q < 0 else "") + whole.replace(",", ".") + (f",{frac}" if digits else "")


def _pct(ratio: Decimal) -> str:
    text = _num(ratio * 100)
    return f"{'+' if ratio > 0 else ''}{text}%"


def _at_or_before(points: list[tuple[date, Decimal]], day: date) -> Decimal | None:
    found = [v for d, v in points if d <= day]
    return found[-1] if found else None


def _portfolio(series: list[dict], start: date, end: date) -> str:
    points = [(date.fromisoformat(p["date"]), Decimal(p["portfolio"])) for p in series]
    now, before = _at_or_before(points, end), _at_or_before(points, start - timedelta(days=1))
    if now is None or before is None or not [d for d, _ in points if start <= d <= end]:
        return "Danh mục: chưa đủ dữ liệu hiệu quả cho tuần này"
    return f"Danh mục: {_pct(now / before - 1)}"


def _vnindex(index: list[tuple[date, float]], briefs: dict[str, dict], start: date, end: date) -> str:
    """Daily VN-Index closes (the series Hiệu quả uses); a session missing there is taken from that day's snapshot."""
    by_day = {d: Decimal(str(v)) for d, v in index}
    for day, b in sorted(briefs.items()):
        row = next((r for r in (b.get("indices") or {}).get("rows", []) if r.get("id") == "VNINDEX" and r.get("close")), None)
        if row:
            by_day.setdefault(date.fromisoformat(day), Decimal(row["close"]))
    closes = sorted(by_day.items())
    now = [(d, v) for d, v in closes if start <= d <= end]
    before = _at_or_before(closes, start - timedelta(days=1))
    if not now:
        return "VN-Index: chưa có số phiên cuối tuần"
    level = now[-1][1]
    if before is None:
        return f"VN-Index: {_num(level)} điểm (chưa có số tuần trước)"
    return f"VN-Index: {_pct(level / before - 1)} ({_num(level)} điểm, tuần trước {_num(before)})"


def _foreign(briefs: dict[str, dict], sessions: list[date]) -> str:
    nets, missing = [], []
    for day in sessions:
        net = ((briefs.get(day.isoformat()) or {}).get("hose") or {}).get("foreign", {}).get("net_value_bn")
        if net is None:
            missing.append(day)
        else:
            nets.append(Decimal(net))
    if not nets:
        return "Khối ngoại HOSE: chưa có số"
    total = sum(nets, Decimal(0))
    side = "mua ròng" if total > 0 else "bán ròng" if total < 0 else "cân bằng"
    gap = f"; thiếu {', '.join(_dm(d) for d in missing)}" if missing else ""
    return f"Khối ngoại HOSE: {side} {_num(abs(total), 1)} tỷ đồng ({len(nets)} phiên có số{gap})"


def _holdings(closes: dict[str, list[tuple[date, float]]], held: set[str], start: date, end: date) -> list[str]:
    out = []
    for symbol in sorted(held):
        points = [(d, Decimal(str(v))) for d, v in closes.get(symbol, [])]
        now = [(d, v) for d, v in points if start <= d <= end]
        before = _at_or_before(points, start - timedelta(days=1))
        if not now:
            out.append(f"{symbol}: chưa có giá trong tuần")
        elif before is None:
            out.append(f"{symbol}: chưa có giá tuần trước")
        else:
            out.append(f"{symbol} {_pct(now[-1][1] / before - 1)}")
    return out


def compose(*, series, index, briefs, closes, insider, events, alerts, held: set[str], watched: set[str], today: date,
            sessions: list[date] | None = None) -> str:
    start, end = week_of(today)
    sessions = sessions if sessions is not None else [start + timedelta(days=i) for i in range(5)]
    lines = [f"BẢN TIN TUẦN {_dm(start)}–{_dm(end)}/{end.year}", "",
             f"{_portfolio(series, start, end)} · {_vnindex(index, briefs, start, end)}", _foreign(briefs, sessions)]
    if held:
        lines += ["Mã đang nắm trong tuần: " + "; ".join(_holdings(closes, held, start, end))]
    lines += ["", "GIAO DỊCH NỘI BỘ (mã đang nắm)"]
    deals = [(s, d) for s in sorted(held) for d in insider.get(s, []) if start.isoformat() <= d["date"] <= end.isoformat()]
    for s, d in sorted(deals, key=lambda x: (x[1]["date"], x[0])):
        what = KIND.get(d.get("kind") or "", "")
        volume = f" {_num(Decimal(d['shares']), 0)} cp" if d.get("shares") is not None and what else ""
        lines.append(f"- {s} · {_dm(d['date'])}: " + (f"{what}{volume} — " if what else "") + d["title"])
    if not deals:
        lines.append("Không có thông báo mới của mã đang nắm.")
    lines += ["", f"LỊCH TUẦN TỚI ({_dm(today)}–{_dm(today + timedelta(days=NEXT_DAYS))})"]
    upcoming = sorted((e for e in events if e["symbol"] in watched and e.get("kind") in REMINDED_KINDS and e.get("key_date")
                       and today.isoformat() <= e["key_date"] <= (today + timedelta(days=NEXT_DAYS)).isoformat()),
                      key=lambda e: (e["symbol"] not in held, e["key_date"], e["symbol"]))
    for e in upcoming:
        lines.append(f"- {e['symbol']}{' (đang nắm)' if e['symbol'] in held else ''}: {describe(e)}")
    if not upcoming:
        lines.append("Không có sự kiện đã biết.")
    lines += ["", "CẢNH BÁO GIÁ"]
    fired = [a for a in alerts if a.get("triggered_at") and start <= datetime.fromisoformat(a["triggered_at"]).astimezone(VN).date() <= end]
    for a in fired:
        lines.append(f"- {a['symbol']} {OPS[a['op']]} {_num(Decimal(a['price']))}: đã báo "
                     f"{_dm(datetime.fromisoformat(a['triggered_at']).astimezone(VN).date())} ở {_num(Decimal(a['triggered_price']))}")
    waiting = sum(1 for a in alerts if not a.get("triggered_at"))
    lines.append(f"{'Không có cảnh báo nào kích hoạt trong tuần. ' if not fired else ''}{waiting} cảnh báo đang chờ.")
    lines += ["", "Nguồn: dữ liệu phần mềm đã lưu (Vnstock, VNDirect). Chỉ để theo dõi. Không phải khuyến nghị."]
    return "\n".join(lines)


def _state(data_dir: Path) -> Path:
    return Path(data_dir) / "alerts" / "weekly.json"


def weekly_brief_run(data_dir: Path, *, inputs: Callable[[], dict], send: Callable[[str], bool], now: datetime) -> dict:
    today = now.astimezone(VN).date()
    if today.weekday() < 5:
        return {"status": "skipped", "reason": "weekday"}
    _, friday = week_of(today)
    path = _state(data_dir)
    sent_for = json.loads(path.read_text(encoding="utf-8")).get("week") if path.is_file() else None
    if sent_for == friday.isoformat():
        return {"status": "already_sent", "week": sent_for}
    if not send(compose(**inputs(), today=today)):
        return {"status": "ok", "week": friday.isoformat(), "sent": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"week": friday.isoformat(), "sent_at": now.isoformat()}), encoding="utf-8")
    os.replace(tmp, path)
    return {"status": "ok", "week": friday.isoformat(), "sent": True}
