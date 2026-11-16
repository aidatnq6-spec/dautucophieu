"""Bản tin tuần: one Telegram note on the weekend about the Monday–Friday just past — the portfolio's time-weighted return against
VN-Index, foreign net trading on HOSE summed over the session snapshots, each held ticker's weekly change, insider notices of held
tickers, known corporate events of the next seven days, the owner's own catalysts due that week (or already due), and price alerts that fired; then the receivable signs that came on or
went off since last week's note, the monthly macro figures with a new period, and the public sources failing now. Built from data the
app already keeps; a missing piece is named, never estimated. Sent once per week (data/alerts/weekly.json, which also keeps the marks
the next week compares with), retried until it goes out.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable

from investment_agent.domain.thesis import describe as describe_condition
from investment_agent.domain.thesis import holding
from investment_agent.market.corporate_events import REMINDED_KINDS, describe
from investment_agent.notifications.render import vnd

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


def _theses(theses: list[dict], closes: dict, costs: dict[str, str], shares: dict[str, int], held: set[str], today: date) -> list[str]:
    """Broken conditions of open theses not under a Giữ tiếp: the first report, what the price did since, and where the position
    stands against its cost — all figures that already happened. Held tickers without a thesis are named."""
    out = []
    for t in theses:
        if t.get("closed_on") is not None or t["symbol"] not in held:
            continue
        last = closes.get(t["symbol"], [])
        price = Decimal(str(last[-1][1])) * 1000 if last else None
        for c in t["conditions"]:
            if c.get("status") != "broken" or holding(c, today):
                continue
            line = f"- {t['symbol']} · {describe_condition(c)}: báo từ {_dm(c['broken_on'])}"
            if c.get("broken_price"):
                line += f" ở {_num(Decimal(c['broken_price']) / 1000)}"
                if price is not None:
                    line += f"; từ đó {_pct(price / Decimal(c['broken_price']) - 1)}"
            cost, n = costs.get(t["symbol"]), shares.get(t["symbol"])
            if price is not None and cost and n:
                line += f"; vị thế hiện tại {vnd(format(((price - Decimal(cost)) * n).quantize(Decimal(1)), 'f'))} so với giá vốn"
            out.append(line)
    if not out:
        out.append("Không có điều kiện nào đang bị phá (ngoài các lần đã giữ tiếp có lý do).")
    missing = sorted(held - {t["symbol"] for t in theses if t.get("closed_on") is None})
    if missing:
        out.append("Chưa có luận điểm: " + ", ".join(missing))
    return out


def _plain(value: str) -> str:
    d = Decimal(value)
    return _num(d, 0) if d == d.to_integral_value() else format(d.normalize(), "f").replace(".", ",")


def _signs(signs: dict, held: set[str]) -> list[str]:
    if signs.get("before") is None:
        return ["Tuần đầu: phần mềm ghi mốc hôm nay, từ tuần sau sẽ báo dấu hiệu bật hoặc tắt."]
    before, now, titles = signs["before"], signs["now"], signs.get("titles", {})
    mark = lambda s: f"{s}{' (đang nắm)' if s in held else ''}"  # noqa: E731
    on = [f"- Bật: {mark(s)} — {titles.get(k, k)}" for s in sorted(now) for k in now[s] if k not in before.get(s, [])]
    off = [f"- Tắt: {mark(s)} — {titles.get(k, k)}" for s in sorted(before) for k in before[s] if k not in now.get(s, [])]
    return on + off or ["Không có dấu hiệu nào bật hay tắt trong tuần."]


def _macro(macro: dict) -> list[str]:
    before = macro.get("before")
    if before is None:
        return ["Tuần đầu: phần mềm ghi mốc hôm nay."]
    new = [(k, v) for k, v in sorted(macro["now"].items()) if k in before and v["date"] > before[k]]
    return [f"- {v['label']}: {_plain(v['value'])} {v['unit']} (kỳ {date.fromisoformat(v['date']).strftime('%d/%m/%Y')})" for _, v in new] \
        or ["Không có chỉ số tháng nào có kỳ mới trong tuần."]


SIGN = {"+": " (+)", "-": " (−)", "?": ""}
FUEL = ("vn_ron95_price", "vn_diesel_price")


def fuel_periods(data_dir, specs: list[dict], *, today: date) -> list[dict]:
    """Giá xăng dầu: each fuel ceiling period that began in the last seven days, with the period before it (entered by hand or read)."""
    from pathlib import Path

    from investment_agent.market.leading import MacroStore
    store, since, out = MacroStore(Path(data_dir)), (today - timedelta(days=7)).isoformat(), []
    for spec in specs:
        obs = store.read(spec["id"])
        for i, o in enumerate(obs):
            if since < o["date"] <= today.isoformat():
                out.append({"label": spec["label"].replace(" (đồng/lít)", ""), "date": o["date"], "value": o["value"],
                            "previous": {"date": obs[i - 1]["date"], "value": obs[i - 1]["value"]} if i else None})
    return out


def _fuel(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        line = f"- {r['label']}: {_num(Decimal(r['value']), 0)} đ/lít từ {_dm(r['date'])}"
        if r["previous"]:
            new, old = Decimal(r["value"]), Decimal(r["previous"]["value"])
            pct = ((new / old - 1) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
            change = new - old
            sign = "+" if change > 0 else "−" if change < 0 else ""
            line += (f" ({sign}{_num(abs(change), 0)} đ, {sign}{_num(abs(pct), 2)}% so với kỳ {_dm(r['previous']['date'])})"
                     if change else f" (không đổi so với kỳ {_dm(r['previous']['date'])})")
        out.append(line)
    return out


def _count(text: str, n: int) -> str:
    """'Hạn công bố … Q4/2026 (20 ngày …)' → 'Hạn công bố … Q4/2026 của n mã (20 ngày …)'."""
    head, sep, tail = text.partition(" (")
    return f"{head} của {n} mã{sep}{tail}"


def _catalysts(items: list[dict], held: set[str]) -> list[str]:
    """The owner's catalysts with a day up to a week ahead or already due, and the report deadlines; the corporate events are in LỊCH TUẦN TỚI."""
    out, groups = [], {}
    for c in (c for c in items if c.get("on") and c.get("auto")):
        groups.setdefault((c["on"], c["text"]), []).append(c["symbol"])
    lines = [(on, "", f"- {_dm(on)}: {_count(text, len(syms))}" + (f"; đang nắm: {', '.join(sorted(s for s in syms if s in held))}"
                                                                   if any(s in held for s in syms) else ""))
             for (on, text), syms in groups.items() if len(syms) > 1]
    alone = {k for k, syms in groups.items() if len(syms) == 1}
    for c in sorted((c for c in items if c.get("on") and (not c.get("auto") or (c["on"], c["text"]) in alone)), key=lambda c: (c["on"], c["symbol"])):
        late = " — đã đến mốc, chưa đánh dấu đã xảy ra" if c.get("due") else ""
        lines.append((c["on"], c["symbol"], f"- {c['symbol']}{' (đang nắm)' if c['symbol'] in held else ''} · {_dm(c['on'])}{SIGN.get(c['sign'], '')}: "
                                             f"{c['text']}{late}"))
    out = [line for _, _, line in sorted(lines, key=lambda x: (x[0], x[1]))]
    return out or [f"Không có mốc nào trong {NEXT_DAYS} ngày tới."]


def compose(*, series, index, briefs, closes, insider, events, alerts, held: set[str], watched: set[str], today: date,
            sessions: list[date] | None = None, theses: list[dict] | None = None, costs: dict[str, str] | None = None,
            shares: dict[str, int] | None = None, todo: list[str] | None = None, signs: dict | None = None, macro: dict | None = None,
            sources: list[dict] | None = None, manual: list[dict] | None = None, catalysts: list[dict] | None = None,
            us_events: list[dict] | None = None, us_chain: dict | None = None, week_signals: dict | None = None,
            fuel: list[dict] | None = None) -> str:
    start, end = week_of(today)
    sessions = sessions if sessions is not None else [start + timedelta(days=i) for i in range(5)]
    lines = [f"BẢN TIN TUẦN {_dm(start)}–{_dm(end)}/{end.year}", "",
             f"{_portfolio(series, start, end)} · {_vnindex(index, briefs, start, end)}", _foreign(briefs, sessions)]
    if week_signals:
        w = week_signals
        gaps = f"{w['green_over_red']} phiên xanh vỏ đỏ lòng" + (f", {w['red_over_green']} phiên đỏ vỏ xanh lòng" if w["red_over_green"] else "")
        asia = (f"{w['asia_against']}/{w['asia_sessions']} phiên VN-Index ngược chiều châu Á" if w["asia_sessions"]
                else "chưa có số châu Á cùng phiên")
        lines += [f"Tín hiệu trong tuần ({w['sessions']} phiên có số): {gaps} · {w['low_liquidity']} phiên thanh khoản thấp · {asia}"]
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
    if fuel:
        lines += ["", "GIÁ XĂNG DẦU (kỳ điều hành mới)", *_fuel(fuel)]
    if us_chain is not None:
        from investment_agent.domain.us_chain import chain_summary, premium_text
        gold = next((n for n in us_chain["nodes"] if n["id"] == "gold"), {})
        lines += ["", "CHUỖI LIÊN THỊ TRƯỜNG TRONG TUẦN", f"- {chain_summary(us_chain)}",
                  *([f"- {premium_text(gold['premium'])}"] if gold.get("premium") else [])]
    if us_events is not None:
        lines += ["", f"LỊCH VĨ MÔ MỸ ({_dm(today)}–{_dm(today + timedelta(days=NEXT_DAYS))}, giờ Việt Nam)",
                  *([f"- {_dm(e['on'])} {e['at']}: {e['text']}" for e in us_events] or ["Không có lịch công bố nào của Fed hay CPI Mỹ."])]
    if catalysts is not None:
        lines += ["", f"MỐC TRONG LUẬN ĐIỂM ({_dm(today)}–{_dm(today + timedelta(days=NEXT_DAYS))})", *_catalysts(catalysts, held)]
    if held and theses is not None:
        lines += ["", "LUẬN ĐIỂM ĐẦU TƯ (đã bị phá mà vẫn đang giữ)", *_theses(theses, closes, costs or {}, shares or {}, held, today)]
    lines += ["", "CẢNH BÁO GIÁ"]
    fired = [a for a in alerts if a.get("triggered_at") and start <= datetime.fromisoformat(a["triggered_at"]).astimezone(VN).date() <= end]
    for a in fired:
        lines.append(f"- {a['symbol']} {OPS[a['op']]} {_num(Decimal(a['price']))}: đã báo "
                     f"{_dm(datetime.fromisoformat(a['triggered_at']).astimezone(VN).date())} ở {_num(Decimal(a['triggered_price']))}")
    waiting = sum(1 for a in alerts if not a.get("triggered_at"))
    lines.append(f"{'Không có cảnh báo nào kích hoạt trong tuần. ' if not fired else ''}{waiting} cảnh báo đang chờ.")
    if signs is not None:
        lines += ["", "DẤU HIỆU PHẢI THU TRONG TUẦN", *_signs(signs, held)]
    if macro is not None:
        lines += ["", "SỐ VĨ MÔ MỚI", *_macro(macro)]
    if sources is not None:
        lines += ["", "NGUỒN SỐ LIỆU", *([f"- {g['source']} lỗi {g['fails']} lượt liên tiếp: {', '.join(g['labels'])}" for g in sources]
                                        or ["Mọi nguồn đều lấy được ở lượt gần nhất."])]
    if manual is not None:
        lines += ["", "DỮ LIỆU NHẬP TAY CẦN XEM",
                  *([f"- {m['label']}, {date.fromisoformat(m['date']).strftime('%d/%m/%Y')} = {_plain(m['value'])}: {'; '.join(m['reasons'])}"
                     for m in manual] or ["Không có dòng nhập tay bất thường."])]
    if todo:
        lines += ["", "VIỆC CẦN XEM", *[f"- {t}" for t in todo]]
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
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    sent_for = state.get("week")
    if sent_for == friday.isoformat():
        return {"status": "already_sent", "week": sent_for}
    got = inputs()
    # last week's marks, so the note says what changed since
    if got.get("signs") is not None:
        got["signs"] = {**got["signs"], "before": state.get("signs")}
    if got.get("macro") is not None:
        got["macro"] = {**got["macro"], "before": state.get("macro")}
    if not send(compose(**got, today=today)):
        return {"status": "ok", "week": friday.isoformat(), "sent": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    keep = {"week": friday.isoformat(), "sent_at": now.isoformat(),
            "signs": got["signs"]["now"] if got.get("signs") is not None else state.get("signs"),
            "macro": {k: v["date"] for k, v in got["macro"]["now"].items()} if got.get("macro") is not None else state.get("macro")}
    tmp.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return {"status": "ok", "week": friday.isoformat(), "sent": True}
