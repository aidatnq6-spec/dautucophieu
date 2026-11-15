"""Thanh khoản và tỷ giá on Vĩ mô (11/2026):

- V2 Tỷ giá trung tâm: the State Bank's central USD/VND rate, the ±5% band banks trade in (since 17/10/2022), how much room the
  Vietcombank selling rate has left below the ceiling, and the change since early January — only when a rate from then is stored.
- V4 Nghiệp vụ thị trường mở: the latest session (money put in by repos, taken out by bills), the repos coming due from the sessions
  kept, and the balance and net injection — counted only once every trading day of the last 91 days (the longest tenor) has a session
  kept; a gap leaves them missing, never estimated. Interbank rates by term, and a flag when the overnight rate jumps.
"""

from datetime import date, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal

BAND = Decimal("0.05")
NEAR_CEILING = Decimal("0.01")
BANK_RATE_AGE = 7
YTD_BY_DAY = 7            # a rate on or before 7 January stands for the start of the year
LONGEST_TENOR = 91
JUMP_SESSIONS, JUMP_POINTS = 5, Decimal("1")
TERMS = ("vn_interbank_on", "vn_interbank_1w", "vn_interbank_1m")
IN, OUT = ("repo", "outright"), ("bill",)

Points = list[tuple[date, Decimal]]


def _plain(v: Decimal) -> str:
    return "0" if v == 0 else format(v.normalize(), "f")


def _dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def central_view(central: Points, *, vcb: Points, today: date) -> dict:
    if not central:
        return {"latest": None, "ceiling": None, "floor": None, "vcb": None, "room": None, "near_ceiling": None, "ytd": None,
                "ytd_missing": "Chưa có tỷ giá trung tâm."}
    day, value = central[-1]
    ceiling, floor = (value * (1 + BAND)).quantize(Decimal(1), ROUND_DOWN), (value * (1 - BAND)).quantize(Decimal(1), ROUND_UP)
    bank = vcb[-1] if vcb and abs((day - vcb[-1][0]).days) <= BANK_RATE_AGE else None
    room = ((ceiling - bank[1]) / ceiling).quantize(Decimal("0.0001"), ROUND_HALF_UP) if bank else None
    early = [(d, v) for d, v in central if d.year == day.year and d <= date(day.year, 1, YTD_BY_DAY)]
    ytd = {"from": early[0][0].isoformat(), "value": _plain(early[0][1]),
           "change": _plain((value / early[0][1] - 1).quantize(Decimal("0.0001"), ROUND_HALF_UP))} if early else None
    missing = None if ytd else (f"Chưa có tỷ giá trung tâm đầu năm {day.year} (đã lưu từ {_dmy(central[0][0])}); "
                                "có thể nhập tay số ngày đầu tháng 1 kèm nguồn ở bảng chỉ số.")
    return {"latest": {"date": day.isoformat(), "value": _plain(value)}, "ceiling": _plain(ceiling), "floor": _plain(floor),
            "band": _plain(BAND), "vcb": {"date": bank[0].isoformat(), "value": _plain(bank[1])} if bank else None,
            "room": _plain(room) if room is not None else None, "near_ceiling": room < NEAR_CEILING if room is not None else None,
            "ytd": ytd, "ytd_missing": missing}


def _sum(session: dict, kinds: tuple[str, ...]) -> Decimal:
    return sum((Decimal(r["volume"]) for r in session["rows"] if r["kind"] in kinds), Decimal(0))


def _due(session: dict, row: dict) -> date:
    return date.fromisoformat(session["date"]) + timedelta(days=row["term_days"])


def _out_on(sessions: list[dict], day: date, kinds: tuple[str, ...]) -> Decimal:
    return sum((Decimal(r["volume"]) for s in sessions if date.fromisoformat(s["date"]) <= day for r in s["rows"]
                if r["kind"] in kinds and _due(s, r) > day), Decimal(0))


def _due_between(sessions: list[dict], after: date, until: date, kinds: tuple[str, ...]) -> Decimal:
    return sum((Decimal(r["volume"]) for s in sessions for r in s["rows"] if r["kind"] in kinds and after < _due(s, r) <= until), Decimal(0))


def omo_view(sessions: list[dict], *, trading_days: list[date], today: date) -> dict:
    if not sessions:
        return {"latest": None, "history": [], "complete": False, "outstanding": None, "net": None, "maturing_7d": None,
                "missing_reason": "Chưa lưu phiên thị trường mở nào."}
    sessions = sorted(sessions, key=lambda s: s["date"])
    last = sessions[-1]
    latest = date.fromisoformat(last["date"])
    kept = {s["date"] for s in sessions}
    window = [d for d in trading_days if latest - timedelta(days=LONGEST_TENOR) <= d <= latest]
    gaps = [d for d in window if d.isoformat() not in kept]
    first = date.fromisoformat(sessions[0]["date"])
    reach = bool(trading_days) and min(trading_days) <= latest - timedelta(days=LONGEST_TENOR)  # the calendar covers the whole window
    complete = reach and bool(window) and not gaps and first <= window[0]
    if complete:
        reason = None
    elif not trading_days:
        reason = "Chưa có lịch phiên giao dịch để kiểm tra các phiên đã lưu."
    elif first > latest - timedelta(days=LONGEST_TENOR) or not reach:
        reason = (f"Số dư và bơm/hút ròng cần đủ phiên của {LONGEST_TENOR} ngày gần nhất (kỳ hạn dài nhất); đã lưu từ {_dmy(first)}, "
                  f"đủ vào khoảng {_dmy(first + timedelta(days=LONGEST_TENOR))}.")
    else:
        reason = f"Thiếu {len(gaps)} phiên trong {LONGEST_TENOR} ngày gần nhất (trang NHNN chỉ hiện phiên mới nhất), nên chưa tính số dư."
    net = outstanding = None
    if complete:
        prev = date.fromisoformat(sessions[-2]["date"]) if len(sessions) > 1 else latest - timedelta(days=1)
        net = _sum(last, IN) - _sum(last, OUT) - _due_between(sessions, prev, latest, IN) + _due_between(sessions, prev, latest, OUT)
        repo, bill = _out_on(sessions, latest, IN), _out_on(sessions, latest, OUT)
        outstanding = {"repo": _plain(repo), "bill": _plain(bill), "net": _plain(repo - bill)}
    return {"latest": {"date": last["date"], "inject": _plain(_sum(last, IN)), "absorb": _plain(_sum(last, OUT)), "rows": last["rows"]},
            "history": [{"date": s["date"], "inject": _plain(_sum(s, IN)), "absorb": _plain(_sum(s, OUT))} for s in sessions[-120:]],
            "complete": complete, "outstanding": outstanding, "net": _plain(net) if net is not None else None,
            "maturing_7d": _plain(_due_between(sessions, today, today + timedelta(days=7), IN)), "missing_reason": reason}


def interbank_view(series: dict[str, Points]) -> dict:
    terms = [{"id": k, "date": series[k][-1][0].isoformat(), "value": _plain(series[k][-1][1])} for k in TERMS if series.get(k)]
    on = series.get("vn_interbank_on") or []
    jump = None
    if len(on) > JUMP_SESSIONS:
        then = on[-1 - JUMP_SESSIONS]
        change = on[-1][1] - then[1]
        if change > JUMP_POINTS:
            jump = {"from": then[0].isoformat(), "change": _plain(change)}
    return {"terms": terms, "jump": jump}
