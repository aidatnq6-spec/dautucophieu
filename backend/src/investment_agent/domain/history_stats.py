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


def independent(days: list[date], index: dict[date, int], *, h: int) -> list[date]:
    out, last = [], None
    for d in sorted(days, key=lambda x: index[x]):
        if last is None or index[d] >= last + h:
            out.append(d)
            last = index[d]
    return out


def group_summary(days: list[date], returns: dict[date, Decimal], index: dict[date, int], *, h: int) -> dict:
    days = [d for d in days if d in returns and d in index]
    if not days:
        return {"n": 0, "n_independent": 0, "mean": None, "median": None, "win_rate": None, "t": None}
    values = [returns[d] for d in days]
    free = [returns[d] for d in independent(days, index, h=h)]
    t = None
    if len(free) >= 3:
        sd = stdev(free)
        t = _q(mean(free) / (sd / Decimal(len(free)).sqrt()), "0.01") if sd > 0 else None
    return {"n": len(values), "n_independent": len(free), "mean": _q(mean(values)), "median": _q(median(values)),
            "win_rate": _q(Decimal(sum(1 for v in values if v > 0)) / len(values)), "t": t}


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
    returns = forward_returns(closes, h)
    level_on: dict[date, str] = {}
    for d, _ in closes:
        i = bisect_right(days, d) - 1
        if i >= 0 and d - days[i] <= KNOWN_FOR:
            level_on[d] = ms._level(key, measured[i][1])
    groups = [{"level": lv, **group_summary([d for d, x in level_on.items() if x == lv], returns, index, h=h)} for lv in ("green", "yellow", "red")]
    spec = ms.SIGNALS[key]
    return {"id": key, "name": spec.name, "h": h, "yellow": str(spec.yellow), "red": str(spec.red), "bad_side": spec.bad, "groups": groups,
            "all": group_summary(list(level_on), returns, index, h=h), "today": ms._level(key, measured[-1][1]) if measured else None,
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
        if g["n"]:
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
        past = (f"trong quá khứ ở mức này VN-Index {h} phiên sau trung bình {_pct(g['mean'])} (mọi lúc {_pct(lg['all']['mean'])}, "
                f"{g['n_independent']} khoảng không chồng lấn)") if g["n"] else "chưa có lần nào ở mức này trong dữ liệu đã lưu"
        parts.append(f"Đèn {lg['name']} đang ở mức {LEVEL_WORD[lg['today']]}; {past}. ")
    if conditions:
        known = [c for c in conditions if c.get("state") is not None]
        true = [_lower(c["label"]) for c in known if c["state"]]
        unknown = len(conditions) - len(known)
        parts.append(f"Vĩ mô hôm nay: {len(true)}/{len(known)} điều kiện đã biết đang đúng ({'; '.join(true) if true else 'không điều kiện nào'})"
                     + (f"; {unknown} điều kiện chưa biết" if unknown else "") + ". ")
    parts.append("Chỉ mô tả quá khứ, không phải dự báo hay khuyến nghị.")
    return "".join(parts)


def pe_groups(pe: Points, closes: Points, *, h: int) -> dict:
    index = {d: i for i, (d, _) in enumerate(closes)}
    returns = forward_returns(closes, h)
    places = _percentiles(pe)
    by_day = dict(pe)
    groups = []
    for b, label in enumerate(GROUP_LABELS):
        days = [d for d, p in places.items() if _bucket(p) == b]
        values = [by_day[d] for d in days]
        groups.append({"bucket": b, "label": label, "pe_low": _q(min(values), "0.01") if values else None,
                       "pe_high": _q(max(values), "0.01") if values else None, **group_summary(days, returns, index, h=h)})
    sample = [d for d in places if d in returns]
    scatter = [{"date": d.isoformat(), "pe": _q(by_day[d], "0.01"), "change": _q(returns[d]), "bucket": _bucket(places[d])}
               for d in sample[::5]]  # one day in five: enough to see the cloud, light enough to draw
    last = pe[-1][0] if pe else None
    today = {"date": last.isoformat(), "pe": _q(by_day[last], "0.01"), "position": _q(places[last], "0.01"), "bucket": _bucket(places[last])} \
        if last in places else None
    return {"h": h, "groups": groups, "all": group_summary(sample, returns, index, h=h), "scatter": scatter,
            "trend": _trend([by_day[d] for d in sample], [returns[d] for d in sample]), "today": today,
            "from": min(places).isoformat() if places else None}
