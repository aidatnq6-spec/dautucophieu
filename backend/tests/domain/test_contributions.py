from datetime import date
from decimal import Decimal

from investment_agent.domain.contributions import contribution_status, reminder_due

PLAN = {"amount": "8000000", "day": 10, "start": "2026-11"}


def flows(*items):
    """(date, signed amount): deposits positive, withdrawals negative."""
    return [(date.fromisoformat(d), Decimal(a)) for d, a in items]


def test_months_streak_and_totals():
    cash = flows(("2026-10-25", "1000000000"),  # opening the ledger, before the plan starts
                 ("2026-11-10", "8000000"), ("2026-12-09", "5000000"), ("2026-12-20", "3000000"),
                 ("2027-01-12", "6000000"), ("2027-02-10", "8000000"), ("2027-02-11", "-1000000"), ("2027-03-10", "9000000"))
    s = contribution_status(cash, PLAN, today=date(2027, 4, 5))
    assert [(m["month"], m["status"]) for m in s["months"]] == [("2026-11", "met"), ("2026-12", "met"), ("2027-01", "short"), ("2027-02", "short"),
                                                                ("2027-03", "met"), ("2027-04", "pending")]
    assert s["months"][2]["short_by"] == "2000000" and s["months"][3]["net"] == "7000000"
    assert s["streak"] == 1  # March only; January and February fell short
    assert s["planned"] == "40000000" and s["contributed"] == "38000000"  # five due months; April not due yet


def test_a_month_without_deposits_is_none_and_the_current_month_counts_once_met():
    s = contribution_status(flows(("2026-11-10", "8000000"), ("2026-12-10", "8000000")), PLAN, today=date(2027, 1, 15))
    assert [m["status"] for m in s["months"]] == ["met", "met", "none"] and s["streak"] == 0
    s = contribution_status(flows(("2026-11-10", "8000000"), ("2026-12-10", "8000000"), ("2027-01-03", "8000000")), PLAN, today=date(2027, 1, 5))
    assert s["months"][-1]["status"] == "met" and s["streak"] == 3


def test_before_the_plan_starts_nothing_is_due():
    s = contribution_status([], PLAN, today=date(2026, 10, 27))
    assert s["months"] == [] and s["streak"] == 0 and s["planned"] == "0"


def test_a_reminder_is_due_from_the_contribution_day_once_a_month_until_met():
    s = contribution_status(flows(("2026-11-10", "8000000")), PLAN, today=date(2026, 12, 10))
    assert reminder_due(s, today=date(2026, 12, 10), reminded_month=None) == "2026-12"
    assert reminder_due(s, today=date(2026, 12, 11), reminded_month="2026-12") is None          # already reminded this month
    early = contribution_status(flows(("2026-11-10", "8000000")), PLAN, today=date(2026, 12, 9))
    assert reminder_due(early, today=date(2026, 12, 9), reminded_month=None) is None             # before the day
    met = contribution_status(flows(("2026-11-10", "8000000"), ("2026-12-02", "8000000")), PLAN, today=date(2026, 12, 12))
    assert reminder_due(met, today=date(2026, 12, 12), reminded_month=None) is None              # already contributed
