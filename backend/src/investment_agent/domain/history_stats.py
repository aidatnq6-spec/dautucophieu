"""Thống kê lịch sử (owner, 21/11/2026): how VN-Index went H sessions later, grouped by a state that was known on the day.

- forward_returns: the change from each session's close to the close H sessions later.
- group_summary: samples, the samples that do not overlap (days at least H sessions apart, chosen from the earliest), mean, median,
  share of rises, and a t-statistic on the non-overlapping samples only: overlapping windows share most of their days and are not
  independent, so a t on all of them overstates the evidence.
- pe_groups: each day's P/E placed among the P/E of the five years before it (known on the day; at least 250 sessions), in five
  groups from cheapest to dearest, with a scatter of P/E against the later change and its least-squares line.

Describes the past; never a forecast or a recommendation."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import mean, median, stdev

YEARS_5 = timedelta(days=round(365.25 * 5))
MIN_HISTORY = 250
GROUP_LABELS = ("Rẻ nhất", "Rẻ", "Giữa", "Đắt", "Đắt nhất")

Points = list[tuple[date, Decimal]]


def _q(v, places: str = "0.0001") -> str:
    return format(Decimal(v).quantize(Decimal(places), ROUND_HALF_UP), "f")


def forward_returns(closes: Points, h: int) -> dict[date, Decimal]:
    return {closes[i][0]: closes[i + h][1] / closes[i][1] - 1 for i in range(len(closes) - h) if closes[i][1]}


def forward_dips(closes: Points, h: int) -> dict[date, Decimal]:
    """The deepest fall within the h sessions after each day: the lowest close of those sessions against the day's close (0 when none
    is lower). Sliding minimum over the window, so a 500-session look stays quick."""
    from collections import deque
    values, n, out = [v for _, v in closes], len(closes), {}
    window: deque[int] = deque()  # indices of the window i+1 … i+h, their closes increasing
    for i in range(n - 1, -1, -1):
        j = i + 1  # the window for day i is j … j+h-1; add j, drop what falls out on the right
        if j < n:
            while window and values[window[-1]] >= values[j]:
                window.pop()
            window.append(j)
        while window and window[0] > i + h:
            window.popleft()
        if i + h < n and values[i]:
            low = values[window[0]] if window else values[i]
            out[closes[i][0]] = min(Decimal(0), low / values[i] - 1)
    return out


def independent(days: list[date], index: dict[date, int], *, h: int) -> list[date]:
    out, last = [], None
    for d in sorted(days, key=lambda x: index[x]):
        if last is None or index[d] >= last + h:
            out.append(d)
            last = index[d]
    return out


ENOUGH = 5  # fewer independent windows than this: the figures are hidden ("không đủ dữ liệu cho kỳ này")


def group_summary(days: list[date], returns: dict[date, Decimal], index: dict[date, int], *, h: int,
                  dips: dict[date, Decimal] | None = None) -> dict:
    """Also the ordinary bad and good outcomes (10th and 90th percentiles, inclusive) and, with dips, the deepest fall within the h
    sessions: its median and its worst. enough: at least ENOUGH independent windows."""
    days = [d for d in days if d in returns and d in index]
    if not days:
        return {"n": 0, "n_independent": 0, "mean": None, "median": None, "win_rate": None, "t": None, "p10": None, "p90": None,
                "dip_median": None, "dip_worst": None, "enough": False}
    from statistics import quantiles
    values = [returns[d] for d in days]
    free = [returns[d] for d in independent(days, index, h=h)]
    t = None
    if len(free) >= 3:
        sd = stdev(free)
        t = _q(mean(free) / (sd / Decimal(len(free)).sqrt()), "0.01") if sd > Decimal("1e-9") else None  # a spread of rounding only: no t
    cuts = quantiles(values, n=10, method="inclusive") if len(values) >= 2 else [values[0]] * 9
    falls = [dips[d] for d in days if dips and d in dips]
    return {"n": len(values), "n_independent": len(free), "mean": _q(mean(values)), "median": _q(median(values)),
            "win_rate": _q(Decimal(sum(1 for v in values if v > 0)) / len(values)), "t": t, "p10": _q(cuts[0]), "p90": _q(cuts[-1]),
            "dip_median": _q(median(falls)) if falls else None, "dip_worst": _q(min(falls)) if falls else None, "enough": len(free) >= ENOUGH}


SHOCKS = {"drop3": "VN-Index giảm từ 3% trong một phiên", "down5": "VN-Index giảm 5 phiên liền",
          "below200": "VN-Index cắt xuống đường trung bình 200 phiên", "dd20": "VN-Index giảm 20% từ đỉnh 52 tuần"}
PEAK_SESSIONS = 250  # the 52-week high the 20% fall is measured from (an all-time peak counted 2008, 2011, 2020 as one, 21/11/2026)


def shock_days(closes: Points) -> dict[str, list[date]]:
    """The days each shock happened. A run of falls counts once, on its fifth day; the 200-session average needs 200 closes; the fall
    from the 52-week high counts on the day it first reaches 20% (from under 20% the session before)."""
    out = {k: [] for k in SHOCKS}
    run, total, before = 0, Decimal(0), None
    values = [v for _, v in closes]
    for i, (d, v) in enumerate(closes):
        if i:
            prev = values[i - 1]
            if prev and v / prev - 1 <= Decimal("-0.03"):
                out["drop3"].append(d)
            run = run + 1 if v < prev else 0
            if run == 5:
                out["down5"].append(d)
        total += v
        if i >= 200:
            total -= values[i - 200]
        if i >= 200:
            ma, ma_prev = total / 200, (total - v + values[i - 200]) / 200
            if v < ma and values[i - 1] >= ma_prev:
                out["below200"].append(d)
        high = max(values[max(0, i - PEAK_SESSIONS + 1):i + 1])
        fall = v / high - 1 if high else Decimal(0)
        if fall <= Decimal("-0.20") and before is not None and before > Decimal("-0.20"):
            out["dd20"].append(d)
        before = fall
    return out


# Cú sốc chồng cú sốc (21/11/2026): a sharp fall split by where VN-Index stood that day, to see whether the risks add up
COMBOS = {
    "drop3_under200": ("drop3", "under200", "Giảm từ 3% trong một phiên khi đang dưới trung bình 200 phiên"),
    "drop3_over200": ("drop3", "over200", "Giảm từ 3% trong một phiên khi đang trên trung bình 200 phiên"),
    "drop3_dd20": ("drop3", "dd20", "Giảm từ 3% trong một phiên khi đã giảm 20% từ đỉnh 52 tuần"),
    "down5_under200": ("down5", "under200", "Giảm 5 phiên liền khi đang dưới trung bình 200 phiên"),
    "down5_over200": ("down5", "over200", "Giảm 5 phiên liền khi đang trên trung bình 200 phiên"),
    "down5_dd20": ("down5", "dd20", "Giảm 5 phiên liền khi đã giảm 20% từ đỉnh 52 tuần"),
}


def _standing(closes: Points) -> dict[str, set[date]]:
    """The sessions VN-Index closed under / at or over its 200-session average (once 200 sessions exist), and 20% or more under its
    52-week high."""
    values, out, total = [v for _, v in closes], {"under200": set(), "over200": set(), "dd20": set()}, Decimal(0)
    for i, (d, v) in enumerate(closes):
        total += v
        if i >= 200:
            total -= values[i - 200]
        if i >= 199:
            out["under200" if v < total / 200 else "over200"].add(d)
        high = max(values[max(0, i - PEAK_SESSIONS + 1):i + 1])
        if high and v / high - 1 <= Decimal("-0.20"):
            out["dd20"].add(d)
    return out


def combo_days(closes: Points) -> dict[str, list[date]]:
    shocks, standing = shock_days(closes), _standing(closes)
    return {k: [d for d in shocks[s] if d in standing[w]] for k, (s, w, _) in COMBOS.items()}


def _shock_rows(days: dict[str, list[date]], labels: dict[str, str], closes: Points, returns, dips, index, *, h: int) -> list[dict]:
    last = closes[-1][0] if closes else None
    return [{"id": k, "label": labels[k], "events": len(days[k]), "recent": [d.isoformat() for d in days[k][-3:]],
             "today": bool(days[k]) and days[k][-1] == last, **group_summary(days[k], returns, index, h=h, dips=dips)} for k in labels]


def shock_groups(closes: Points, *, h: int) -> dict:
    """Sau một cú sốc thì sao: VN-Index h sessions after each kind of shock, with the risk figures, the latest times it happened and
    whether it happened on the latest session; "combos" splits the sharp falls by where VN-Index stood; "all" is every session."""
    index = {d: i for i, (d, _) in enumerate(closes)}
    returns, dips = forward_returns(closes, h), forward_dips(closes, h)
    groups = _shock_rows(shock_days(closes), SHOCKS, closes, returns, dips, index, h=h)
    combos = _shock_rows(combo_days(closes), {k: c[2] for k, c in COMBOS.items()}, closes, returns, dips, index, h=h)
    return {"h": h, "groups": groups, "combos": combos, "all": group_summary([d for d, _ in closes], returns, index, h=h, dips=dips),
            "from": closes[0][0].isoformat() if closes else None}


TODAY_H = 60  # the brief and Telegram read a shock's past 60 sessions on


def shocks_today(closes: Points, *, session: date, h: int = TODAY_H) -> dict:
    """Cú sốc hôm nay for the brief: the shocks of the session, each with its past (the narrower split when one applies and has enough
    independent windows)."""
    closes = [(d, v) for d, v in closes if d <= session]
    if not closes or closes[-1][0] != session:
        return {"status": "missing", "reason": "Chưa có giá VN-Index phiên này"}
    out = shock_groups(closes, h=h)
    return {"status": "ok", "h": h, "today": _today_shocks(out), "all": out["all"], "from": out["from"]}


def _today_shocks(out: dict) -> list[dict]:
    today = []
    for g in (g for g in out["groups"] if g["today"]):
        narrow = [c for c in out.get("combos", []) if c["today"] and c["enough"] and c["id"].startswith(g["id"] + "_")]  # a split too thin says less
        narrow.sort(key=lambda c: not c["id"].endswith("dd20"))  # 20% under the high says more than the 200-session side
        today.append({**g, "within": narrow[0] if narrow else None})
    return today


def _shock_past(g: dict, everyday: dict, h: int, since: str | None) -> str:
    head = f"{g['events']} lần từ {since[:4]}" if since else f"{g['events']} lần"
    if g.get("enough", True) is False:
        return f"{head}, chỉ {g['n_independent']} khoảng {h} phiên không chồng lấn: không đủ dữ liệu cho kỳ này"
    return (f"{head} ({g['n_independent']} khoảng không chồng lấn), {h} phiên sau trung bình {_pct(g['mean'])} (mọi lúc {_pct(everyday['mean'])}), "
            f"xấu thường gặp {_pct(g['p10'])}, giảm sâu nhất trong kỳ trung vị {_pct(g['dip_median'])}")


def shock_line(section: dict | None) -> str | None:
    """One line when VN-Index had a shock on the session, by a fixed pattern (no model); None otherwise."""
    if not section or section.get("status") != "ok" or not section["today"]:
        return None
    return _shock_sentence(section["today"], section["all"], section["h"], section.get("from")) + " Chỉ mô tả quá khứ, không phải dự báo."


def _shock_sentence(today: list[dict], everyday: dict, h: int, since: str | None) -> str:
    parts = [f"{_lower(g['within']['label']) if g.get('within') else g['label']}: {_shock_past(g.get('within') or g, everyday, h, since)}" for g in today]
    return f"Cú sốc hôm nay: {'; '.join(g['label'] for g in today)}. Trong quá khứ, " + "; ".join(parts) + "."


def _percentiles(pe: Points) -> dict[date, Decimal]:
    out = {}
    for i, (d, v) in enumerate(pe):
        window = [x for e, x in pe[:i + 1] if e > d - YEARS_5]
        if len(window) >= MIN_HISTORY:
            out[d] = Decimal(sum(1 for x in window if x <= v)) / len(window)
    return out


def _bucket(p: Decimal) -> int:
    return min(4, int(p * 5))


def _trend(xs: list[Decimal], ys: list[Decimal]) -> dict | None:
    if len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    intercept = my - slope * mx
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    return {"slope": _q(slope, "0.000001"), "intercept": _q(intercept, "0.000001"), "r2": _q(1 - sse / sst if sst else 0, "0.01")}


KNOWN_FOR = timedelta(days=7)  # a light's measure stands for a session up to this many days after its own date


def light_measures(key: str, series: dict[str, Points]) -> Points:
    """The light's measure on every stored day, worked out as Đèn tín hiệu rủi ro vĩ mô does (domain.macro_signals)."""
    from investment_agent.domain import macro_signals as ms
    if key == "pe":
        pe = series.get("vnindex_pe") or []
        return ms._percentile(pe, pe[0][0]) if pe else []
    if key in ("oil", "usd"):
        return ms._against_30(series.get(ms.SOURCES[key]) or [], share=True)
    if key == "us10y":
        return ms._against_30(series.get("us10y") or [], share=False)
    raise ValueError(f"light without a long history: {key}")


def light_groups(key: str, series: dict[str, Points], closes: Points, *, h: int) -> dict:
    """VN-Index H sessions later by the light's level that day (green, yellow, red), and for every day."""
    from bisect import bisect_right

    from investment_agent.domain import macro_signals as ms
    measured = light_measures(key, series)
    days = [d for d, _ in measured]
    index = {d: i for i, (d, _) in enumerate(closes)}
    returns, dips = forward_returns(closes, h), forward_dips(closes, h)
    level_on: dict[date, str] = {}
    for d, _ in closes:
        i = bisect_right(days, d) - 1
        if i >= 0 and d - days[i] <= KNOWN_FOR:
            level_on[d] = ms._level(key, measured[i][1])
    groups = [{"level": lv, **group_summary([d for d, x in level_on.items() if x == lv], returns, index, h=h, dips=dips)} for lv in ("green", "yellow", "red")]
    spec = ms.SIGNALS[key]
    return {"id": key, "name": spec.name, "h": h, "yellow": str(spec.yellow), "red": str(spec.red), "bad_side": spec.bad, "groups": groups,
            "all": group_summary(list(level_on), returns, index, h=h, dips=dips), "today": ms._level(key, measured[-1][1]) if measured else None,
            "from": min(level_on).isoformat() if level_on else None}


LEVEL_WORD = {"yellow": "cảnh báo", "red": "nguy hiểm"}


def _pct(v) -> str:
    x = Decimal(str(v)) * 100
    return ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x):.1f}".replace(".", ",") + "%"


def _lower(label: str) -> str:
    """The first letter lower-cased when the word is an ordinary one ("Giá dầu" → "giá dầu"), not an acronym ("P/E", "USD")."""
    return label[0].lower() + label[1:] if len(label) > 1 and label[1].islower() else label


def _evidence(g: dict) -> str:
    """Too few windows and an unclear difference are two reasons, said apart."""
    t, n = g.get("t"), g["n_independent"]
    if n < 5:
        return f"nhưng chỉ có {n} khoảng không chồng lấn, quá ít để coi là chắc"
    tt = None if t is None else format(Decimal(t).normalize(), "f").replace(".", ",")
    if t is None or abs(Decimal(t)) < 2:
        return f"dựa trên {n} khoảng không chồng lấn nhưng chênh lệch chưa rõ{f' (t = {tt})' if tt else ''}, chưa đủ để coi là chắc"
    return f"{n} khoảng không chồng lấn, t = {tt}"


def history_summary(stats: dict, conditions: list[dict] | None) -> str:
    """Câu tóm tắt ở đầu Thống kê lịch sử, by a fixed pattern from the page's own figures (no model): today's P/E group and its past
    with the evidence it rests on, the lights off normal, and how many macro conditions hold today."""
    h, pe, parts = stats["h"], stats["pe"], []
    today = pe.get("today")
    if today:
        g = pe["groups"][today["bucket"]]
        parts.append(f"Hôm nay P/E VN-Index {today['pe'].replace('.', ',')}, thuộc nhóm {g['label'].lower()} so với 5 năm trước. ")
        if g["n"] and g.get("enough", True) is False:  # too few windows: no figure is read out
            parts.append(f"Ở nhóm này chỉ có {g['n_independent']} khoảng {h} phiên không chồng lấn: không đủ dữ liệu cho kỳ này. ")
        elif g["n"]:
            parts.append(f"Trong quá khứ, ở nhóm này VN-Index {h} phiên sau trung bình {_pct(g['mean'])} (mọi lúc {_pct(pe['all']['mean'])}), "
                         f"tăng ở {round(Decimal(g['win_rate']) * 100)}% số lần; {_evidence(g)}. ")
    else:
        parts.append("Chưa có P/E VN-Index hôm nay. ")
    off = [lg for lg in stats["lights"] if lg.get("today") in LEVEL_WORD]
    if not off:
        # only the lights with a long history are here, not all of Vĩ mô's: they are named so the two pages do not seem to disagree
        names = ", ".join(lg["name"] for lg in stats["lights"])
        parts.append(f"Cả {len(stats['lights'])} đèn có lịch sử dài ({names}) đang ở mức bình thường. ")
    for lg in off:
        g = next(x for x in lg["groups"] if x["level"] == lg["today"])
        if not g["n"]:
            past = "chưa có lần nào ở mức này trong dữ liệu đã lưu"
        elif g.get("enough", True) is False:
            past = f"ở mức này chỉ có {g['n_independent']} khoảng {h} phiên không chồng lấn: không đủ dữ liệu cho kỳ này"
        else:
            past = (f"trong quá khứ ở mức này VN-Index {h} phiên sau trung bình {_pct(g['mean'])} (mọi lúc {_pct(lg['all']['mean'])}, "
                    f"{g['n_independent']} khoảng không chồng lấn)")
        parts.append(f"Đèn {lg['name']} đang ở mức {LEVEL_WORD[lg['today']]}; {past}. ")
    if conditions:
        known = [c for c in conditions if c.get("state") is not None]
        true = [_lower(c["label"]) for c in known if c["state"]]
        unknown = len(conditions) - len(known)
        parts.append(f"Vĩ mô hôm nay: {len(true)}/{len(known)} điều kiện đã biết đang đúng ({'; '.join(true) if true else 'không điều kiện nào'})"
                     + (f"; {unknown} điều kiện chưa biết" if unknown else "") + ". ")
    if (shocks := stats.get("shocks")) and (today := _today_shocks(shocks)):
        parts.append(_shock_sentence(today, shocks["all"], h, shocks.get("from")) + " ")
    parts.append("Chỉ mô tả quá khứ, không phải dự báo hay khuyến nghị.")
    return "".join(parts)


def pe_groups(pe: Points, closes: Points, *, h: int) -> dict:
    index = {d: i for i, (d, _) in enumerate(closes)}
    returns, dips = forward_returns(closes, h), forward_dips(closes, h)
    places = _percentiles(pe)
    by_day = dict(pe)
    groups = []
    for b, label in enumerate(GROUP_LABELS):
        days = [d for d, p in places.items() if _bucket(p) == b]
        values = [by_day[d] for d in days]
        groups.append({"bucket": b, "label": label, "pe_low": _q(min(values), "0.01") if values else None,
                       "pe_high": _q(max(values), "0.01") if values else None, **group_summary(days, returns, index, h=h, dips=dips)})
    sample = [d for d in places if d in returns]
    scatter = [{"date": d.isoformat(), "pe": _q(by_day[d], "0.01"), "change": _q(returns[d]), "bucket": _bucket(places[d])}
               for d in sample[::5]]  # one day in five: enough to see the cloud, light enough to draw
    last = pe[-1][0] if pe else None
    today = {"date": last.isoformat(), "pe": _q(by_day[last], "0.01"), "position": _q(places[last], "0.01"), "bucket": _bucket(places[last])} \
        if last in places else None
    return {"h": h, "groups": groups, "all": group_summary(sample, returns, index, h=h, dips=dips), "scatter": scatter,
            "trend": _trend([by_day[d] for d in sample], [returns[d] for d in sample]), "today": today,
            "from": min(places).isoformat() if places else None}
