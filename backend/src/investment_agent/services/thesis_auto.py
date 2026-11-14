"""What the thesis page fills in by itself from stored public data (A1, A2, A4, A5); the owner's judgements stay the owner's.

- A1 catalysts: the ticker's corporate events in the coming year (VNDirect) and the deadline of the next quarter's report
  (20 days after the quarter, Thông tư 96/2020 Điều 14), each with sign "?" until the owner keeps it with + or −;
- A2 suggested indicators: profit, revenue, gross margin and associates' share per quarter, and P/E, each with levels from the
  ticker's own history (25th percentile, median, 75th; reversed for P/E), for the owner to adjust;
- A4 facts per question: figures only (growth over four quarters, margins, plan progress, the sector's peers, multiples against
  their own past, insiders, the trend board), refreshed with the data;
- A5 gaps: a fact that cannot be worked out says what is missing, and goes away once the data is there.
Nothing is estimated: a figure without its inputs is a gap, not a guess.
"""

import hashlib
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import median

B = Decimal(10) ** 9
SUGGEST_QUARTERS, EVENT_DAYS, REPORT_DAYS = 12, 365, 20
Q_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _pct(v: Decimal) -> str:
    q = (v * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
    return f"{'+' if q > 0 else ''}{format(q, 'f').replace('.', ',')}%"


def _ty(v: Decimal) -> str:
    return f"{format((v / B).quantize(Decimal(1), ROUND_HALF_UP), ',').replace(',', '.')} tỷ"


def _ql(q: str) -> str:
    return f"Q{q[-1]}/{q[:4]}"


def _d(v) -> Decimal | None:
    return Decimal(str(v)) if v is not None else None


def _ttm(quarters: dict, line: str) -> tuple[Decimal, Decimal, str] | None:
    """(last four quarters, the four before, the last quarter) of a line; None without eight consecutive figures."""
    keys = sorted(q for q, f in quarters.items() if f.get(line) is not None)[-8:]
    if len(keys) < 8:
        return None
    vals = [Decimal(quarters[q][line]) for q in keys]
    return sum(vals[4:]), sum(vals[:4]), keys[-1]


def _growth_line(label: str, t) -> str | None:
    if t is None:
        return None
    now, before, last = t
    change = f", {_pct(now / before - 1)} so với 4 quý trước" if before > 0 else " (4 quý trước lỗ: không tính tăng trưởng)"
    return f"{label} 4 quý đến {_ql(last)}: {_ty(now)}{change}."


def _short_id(raw: str) -> str:
    return "ev" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def catalysts(data_dir: Path, symbol: str, quarters: dict, *, today: date) -> list[dict]:
    """A1: coming corporate events and the next quarterly report deadline, as catalysts marked automatic."""
    from investment_agent.market.corporate_events import EventStore, describe
    out, seen = [], set()
    for e in (EventStore(data_dir).read(symbol) or {}).get("events") or []:
        day = e.get("key_date")
        if not day or "EN_GB" in str(e.get("id")) or not (today <= date.fromisoformat(day) <= today + timedelta(days=EVENT_DAYS)):
            continue
        text = describe(e)
        if (day, text) in seen:
            continue
        seen.add((day, text))
        out.append({"id": _short_id(str(e.get("id"))), "when": f"{day[8:10]}/{day[5:7]}/{day[:4]}", "on": day, "sign": "?", "text": text,
                    "source": "VNDirect (lịch sự kiện)", "done": False, "auto": True})
    if quarters:
        last = max(quarters)
        y, q = int(last[:4]), int(last[-1])
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
        end = date(y, *Q_END[q])
        due = end + timedelta(days=REPORT_DAYS)
        if due >= today - timedelta(days=60):
            out.append({"id": _short_id(f"report-{y}-Q{q}"), "when": _ql(f"{y}-Q{q}"), "on": due.isoformat(), "sign": "?",
                        "text": f"Hạn công bố báo cáo tài chính {_ql(f'{y}-Q{q}')} ({due:%d/%m/%Y}, 20 ngày sau quý)", "source": "Thông tư 96/2020 Điều 14",
                        "done": False, "auto": True})
    return sorted(out, key=lambda c: c["on"])


def _levels(values: list[Decimal], *, lower_better: bool, places: str) -> dict | None:
    if len(values) < 8:
        return None
    s = sorted(values)
    at = lambda f: s[round(f * (len(s) - 1))].quantize(Decimal(places), ROUND_HALF_UP)  # noqa: E731
    p25, mid, p75 = at(0.25), Decimal(str(median(s))).quantize(Decimal(places), ROUND_HALF_UP), at(0.75)
    bad, good = (p75, p25) if lower_better else (p25, p75)
    if (lower_better and not bad > mid >= good) or (not lower_better and not bad < mid <= good):
        return None
    f = lambda v: format(v.normalize(), "f")  # noqa: E731
    return {"bad": f(bad), "base": f(mid), "good": f(good)}


def suggested_indicators(quarters: dict, pe: list[Decimal], *, have: set[str]) -> list[dict]:
    """A2: one indicator per figure the ticker reports, levels from its own last 12 quarters (P/E: 60 months, lower is better)."""
    keys = sorted(quarters)[-SUGGEST_QUARTERS:]
    series = {
        "npat_parent_q": ("Lợi nhuận cổ đông mẹ quý", "tỷ", "lag", [Decimal(quarters[q]["npat_parent"]) / B for q in keys if quarters[q].get("npat_parent") is not None]),
        "revenue_q": ("Doanh thu thuần quý", "tỷ", "coincident", [Decimal(quarters[q]["revenue"]) / B for q in keys if quarters[q].get("revenue") is not None]),
        "gross_margin_q": ("Biên lợi nhuận gộp quý", "%", "lag", [Decimal(quarters[q]["gross_profit"]) / Decimal(quarters[q]["revenue"]) * 100 for q in keys
                                                               if quarters[q].get("gross_profit") is not None and quarters[q].get("revenue") not in (None, "0")]),
        "associates_q": ("Lãi công ty liên doanh, liên kết quý", "tỷ", "lag", [Decimal(quarters[q]["associates"]) / B for q in keys
                                                                         if quarters[q].get("associates") not in (None, "0")]),
    }
    out = []
    for metric, (name, unit, tier, values) in series.items():
        lv = _levels(values, lower_better=False, places="0.1")
        if lv and f"auto:{metric}" not in have:
            out.append({"id": f"s-{metric}", "name": name, "tier": tier, "unit": unit, **lv, "lower_better": False, "source": f"auto:{metric}", "readings": []})
    lv = _levels([v for v in pe[-60:] if v > 0], lower_better=True, places="0.01")
    if lv and "auto:pe_ttm" not in have:
        out.append({"id": "s-pe_ttm", "name": "P/E bốn quý", "tier": "valuation", "unit": "lần", **lv, "lower_better": True, "source": "auto:pe_ttm", "readings": []})
    return out


def facts(data_dir: Path, symbol: str, quarters: dict, years: dict, *, pe: list[Decimal], pb: list[Decimal], plans: dict, lights: dict,
          today: date) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """A4 facts and A5 gaps per question: ({question: [facts]}, {question: [what is missing]})."""
    f: dict[str, list[str]] = {k: [] for k in ("business", "strategy", "industry", "valuation", "monitoring", "timing")}
    g: dict[str, list[str]] = {k: [] for k in f}
    # 1 · business
    for label, line in (("Doanh thu", "revenue"), ("Lợi nhuận cổ đông mẹ", "npat_parent")):
        text = _growth_line(label, _ttm(quarters, line))
        (f["business"].append(text) if text else g["business"].append(f"Thiếu 8 quý {label.lower()} liên tiếp để tính tăng trưởng 4 quý"))
    with_margin = [q for q in sorted(quarters) if quarters[q].get("gross_profit") is not None and quarters[q].get("revenue") not in (None, "0")]
    if with_margin:
        last = with_margin[-1]
        m = Decimal(quarters[last]["gross_profit"]) / Decimal(quarters[last]["revenue"])
        prior = f"{int(last[:4]) - 1}{last[4:]}"
        old = (Decimal(quarters[prior]["gross_profit"]) / Decimal(quarters[prior]["revenue"])) if prior in with_margin else None
        f["business"].append(f"Biên gộp {_ql(last)}: {_pct(m).lstrip('+')}" + (f" (cùng kỳ {_pct(old).lstrip('+')})." if old is not None else "."))
    assoc, pbt = _ttm(quarters, "associates"), _ttm(quarters, "pbt")
    if assoc and pbt and pbt[0] > 0 and assoc[0] != 0:
        f["business"].append(f"Lãi liên doanh, liên kết bằng {_pct(assoc[0] / pbt[0]).lstrip('+')} lợi nhuận trước thuế 4 quý.")
    ys = [y for y in sorted(years) if years[y].get("cfo") is not None and years[y].get("npat") not in (None, "0")][-3:]
    if len(ys) == 3:
        cfo, npat = sum(Decimal(years[y]["cfo"]) for y in ys), sum(Decimal(years[y]["npat"]) for y in ys)
        if npat > 0:
            f["business"].append(f"Dòng tiền kinh doanh / lợi nhuận sau thuế {ys[0]}–{ys[-1]}: {format((cfo / npat).quantize(Decimal('0.01')), 'f').replace('.', ',')} lần.")
    else:
        g["business"].append("Thiếu 3 năm dòng tiền kinh doanh để so với lợi nhuận")
    # 2 · strategy: this year's plan
    from investment_agent.domain.annual_plans import plan_progress
    from investment_agent.market.plans_cafef import PlanStore
    cafef = (PlanStore(Path(data_dir) / "annual-plans-cafef").read(symbol) or {}).get("years")
    progress = [p for p in plan_progress(plans, quarters or None, cafef=cafef) if p["year"] == str(today.year)]
    if progress and progress[0]["profit"]["ratio"] is not None:
        p = progress[0]
        rev = f"; doanh thu đạt {_pct(Decimal(p['revenue']['ratio'])).lstrip('+')}" if p["revenue"]["ratio"] else ""
        f["strategy"].append(f"Kế hoạch {p['profit_label']} {p['year']} ({'bạn nhập' if p['origin'] == 'owner' else 'CafeF'}): đạt "
                             f"{_pct(Decimal(p['profit']['ratio'])).lstrip('+')} sau {_ql(p['through'])}{rev}.")
    else:
        g["strategy"].append(f"Chưa có kế hoạch kinh doanh năm {today.year} (nhập ở phần Kế hoạch năm của trang mã)")
    # 3 · industry: the sector's watched peers
    from investment_agent.market.financial_ratios import kind_of
    from investment_agent.market.sectors import load_sectors
    from investment_agent.market.statements import StatementStore
    from investment_agent.market.watchlist import load_watchlist
    sectors = load_sectors(Path(data_dir))[0]
    sector = sectors.get(symbol)
    if sector is None:
        g["industry"].append("Mã chưa có ngành trong danh sách ngành")
    else:
        store = StatementStore(Path(data_dir) / ("statements" if kind_of(sector) is None else "statements-financial"))
        growth = {}
        for s in load_watchlist(Path(data_dir)).symbols:
            if sectors.get(s) == sector:
                t = _ttm((store.read(s) or {}).get("quarters") or {}, "npat_parent")
                if t and t[1] > 0:
                    growth[s] = t[0] / t[1] - 1
        if symbol in growth and len(growth) >= 3:
            rank = sorted(growth, key=lambda s: -growth[s]).index(symbol) + 1
            f["industry"].append(f"{sector}: lợi nhuận 4 quý của {len(growth)} mã theo dõi tăng trung vị {_pct(Decimal(str(median(growth.values()))))}; "
                                 f"{symbol} {_pct(growth[symbol])}, đứng thứ {rank}/{len(growth)}.")
        else:
            f["industry"].append(f"Ngành {sector}.")
            g["industry"].append("Chưa đủ 3 mã cùng ngành có lợi nhuận 8 quý để so")
    # 4 · valuation: multiples against their own past
    for label, series in (("P/E", pe), ("P/B", pb)):
        recent = [v for v in series[-60:] if v > 0]
        if len(recent) >= 24:
            now = recent[-1]
            cheaper = sum(1 for v in recent[:-1] if v < now) / (len(recent) - 1)
            where = f"thấp nhất trong {len(recent)} tháng" if cheaper == 0 else f"chỉ {round(cheaper * 100)}% số tháng có {label} thấp hơn"
            f["valuation"].append(f"{label} hiện tại {format(now.quantize(Decimal('0.01')), 'f').replace('.', ',')} lần, trung vị {len(recent)} tháng "
                                  f"{format(Decimal(str(median(recent))).quantize(Decimal('0.01')), 'f').replace('.', ',')} lần; {where}.")
        else:
            g["valuation"].append(f"Chưa đủ 24 tháng {label} để so với chính nó")
    # 5 · monitoring: the lights and insiders
    if sum(lights.values()) - lights.get("none", 0) > 0:
        f["monitoring"].append(f"Chỉ báo: {lights['good']} Tốt, {lights['watch']} Theo dõi, {lights['bad']} Xấu.")
    else:
        g["monitoring"].append("Chưa có chỉ báo theo dõi có số (thêm bộ chỉ báo gợi ý)")
    from investment_agent.market.insider_deals import InsiderStore, _year
    from datetime import datetime, time, timezone
    insider = InsiderStore(Path(data_dir)).read(symbol)
    if insider and insider.get("deals") is not None:
        y = _year(insider["deals"], datetime.combine(today, time(12), timezone.utc))
        if y["buy_reports"] or y["sell_reports"]:
            n = lambda v: f"{v:,}".replace(",", ".")  # noqa: E731 - thousands with dots, the sentence's commas kept
            f["monitoring"].append(f"Nội bộ 12 tháng: mua {n(y['bought'])} CP ({y['buy_reports']} báo cáo), bán {n(y['sold'])} CP ({y['sell_reports']} báo cáo).")
        else:
            f["monitoring"].append("Nội bộ 12 tháng: không có giao dịch đã hoàn tất.")
    else:
        g["monitoring"].append("Chưa đọc giao dịch nội bộ (phần Giao dịch nội bộ trên trang mã sẽ đọc)")
    # 6 · timing: the trend board
    from investment_agent.market.trend import SnapshotStore
    snap = SnapshotStore(Path(data_dir) / "trend").latest() or {}
    row = next((r for grp in snap.get("groups", []) for r in grp.get("rows", []) if r.get("id") == symbol), None)
    if row:
        names, macd = {"M": "Tháng", "W": "Tuần", "D1": "Ngày"}, {"up,>0": "MACD tăng trên 0", "up,<0": "MACD tăng dưới 0", "down,>0": "MACD giảm trên 0",
                                                                  "down,<0": "MACD giảm dưới 0"}
        zone = {"overbought": " (quá mua)", "oversold": " (quá bán)"}
        parts = [f"{names[k]}: {macd.get(c.get('macd'), 'MACD chưa có')}, RSI {c['rsi']}{zone.get(c.get('zone'), '')}" for k in ("M", "W", "D1")
                 if (c := row["cells"].get(k)) and c.get("rsi") is not None]
        if parts:
            f["timing"].append(f"Xu hướng phiên {snap.get('session_date', '')[8:10]}/{snap.get('session_date', '')[5:7]}: " + "; ".join(parts) + ".")
    if not f["timing"]:
        g["timing"].append("Mã chưa có trên bảng Xu hướng")
    return f, g
