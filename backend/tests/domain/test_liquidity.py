from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.liquidity import central_view, interbank_view, omo_view


def test_the_ceiling_is_five_percent_above_the_central_rate_and_the_bank_rate_is_measured_against_it():
    central = [(date(2026, 1, 2), Decimal("25000")), (date(2026, 11, 14), Decimal("25100"))]
    v = central_view(central, vcb=[(date(2026, 11, 13), Decimal("26300"))], today=date(2026, 11, 15))
    assert v["latest"] == {"date": "2026-11-14", "value": "25100"} and v["ceiling"] == "26355" and v["floor"] == "23845"
    assert v["room"] == "0.0021" and v["near_ceiling"] is True
    assert v["ytd"] == {"from": "2026-01-02", "value": "25000", "change": "0.004"} and v["ytd_missing"] is None


def test_without_a_rate_from_early_january_the_change_this_year_is_missing_not_guessed():
    v = central_view([(date(2026, 11, 14), Decimal("25100"))], vcb=[(date(2026, 10, 1), Decimal("26300"))], today=date(2026, 11, 15))
    assert v["ytd"] is None and "14/11/2026" in v["ytd_missing"]
    assert v["room"] is None and v["near_ceiling"] is None  # the bank's rate is six weeks older: not compared
    assert central_view([], vcb=[], today=date(2026, 11, 15))["latest"] is None


def session(day: date, repo: list[tuple[int, str]], bills: list[tuple[int, str]] = ()):
    rows = [{"kind": "repo", "term_days": t, "volume": v} for t, v in repo] + [{"kind": "bill", "term_days": t, "volume": v} for t, v in bills]
    return {"date": day.isoformat(), "rows": rows, "total": None}


def weekdays(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() < 5]


def test_the_latest_session_is_shown_and_the_balance_waits_for_91_days_of_sessions():
    days = weekdays(date(2026, 11, 2), date(2026, 11, 13))
    sessions = [session(d, [(7, "100")]) for d in days]
    v = omo_view(sessions, trading_days=days, today=date(2026, 11, 15))
    assert v["latest"]["date"] == "2026-11-13" and v["latest"]["inject"] == "100" and v["latest"]["absorb"] == "0"
    assert v["complete"] is False and v["outstanding"] is None and v["net"] is None and "02/11/2026" in v["missing_reason"]
    assert [p["inject"] for p in v["history"]] == ["100"] * 10
    assert v["maturing_7d"] == "500"  # sessions 09–13/11 come due 16–20/11, from the sessions kept


def test_with_every_session_kept_the_balance_and_the_net_injection_are_counted():
    days = weekdays(date(2026, 7, 1), date(2026, 11, 13))
    sessions = [session(d, [(7, "100")], [(14, "10")] if d == date(2026, 11, 13) else []) for d in days]
    v = omo_view(sessions, trading_days=days, today=date(2026, 11, 13))
    assert v["complete"] is True and v["missing_reason"] is None
    assert v["outstanding"] == {"repo": "500", "bill": "10", "net": "490"}  # the repos of 09–13/11 are still out
    assert v["net"] == "-10"  # 100 in, 100 due back from 06/11 (13/11), 10 taken in bills
    v2 = omo_view([s for s in sessions if s["date"] != "2026-10-01"], trading_days=days, today=date(2026, 11, 13))
    assert v2["complete"] is False and "1 phiên" in v2["missing_reason"]


def test_the_overnight_rate_jumping_more_than_a_point_in_five_sessions_is_flagged():
    on = [(date(2026, 11, d), Decimal(v)) for d, v in ((3, "4.0"), (4, "4.1"), (5, "4.2"), (6, "4.4"), (7, "4.8"), (10, "5.2"))]
    v = interbank_view({"vn_interbank_on": on, "vn_interbank_1w": [(date(2026, 11, 10), Decimal("4.6"))], "vn_interbank_1m": []})
    assert v["jump"] == {"from": "2026-11-03", "change": "1.2"} and [t["id"] for t in v["terms"]] == ["vn_interbank_on", "vn_interbank_1w"]
    assert interbank_view({"vn_interbank_on": on[:3]})["jump"] is None
