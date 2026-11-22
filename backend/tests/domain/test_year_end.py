"""Việc cuối năm (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md): a fixed list from 1 December to
31 December, the checks the app can make ticked by themselves, the others by the owner; reminders on 1/12, 20/12 and 5/1."""

from datetime import date

from investment_agent.domain.year_end import (ITEMS, checklist_year, reminder_due, render_reminder, theses_fact, tower_fact,
                                              year_end_view)


def test_the_list_is_open_in_december_and_january_for_the_year_ending():
    assert checklist_year(date(2026, 11, 30)) is None
    assert checklist_year(date(2026, 12, 1)) == 2026
    assert checklist_year(date(2027, 1, 31)) == 2026
    assert checklist_year(date(2027, 2, 1)) is None


def test_held_tickers_without_an_open_thesis_or_untouched_for_90_days_are_named():
    theses = [{"symbol": "AAA", "created_on": "2026-03-01", "closed_on": None, "history": [{"type": "edit", "on": "2026-10-01"}]},
              {"symbol": "BBB", "created_on": "2026-05-01", "closed_on": None, "history": []},
              {"symbol": "CCC", "created_on": "2026-11-01", "closed_on": "2026-11-20", "history": []}]
    done, detail = theses_fact(theses, held={"AAA", "BBB", "CCC"}, today=date(2026, 12, 2))
    assert done is False and detail == "chưa rà trong 90 ngày: BBB; chưa có luận điểm đang mở: CCC"
    assert theses_fact(theses[:1], held={"AAA"}, today=date(2026, 12, 2)) == (True, "mọi mã đang giữ đã rà trong 90 ngày")
    assert theses_fact([], held=set(), today=date(2026, 12, 2)) == (True, "không giữ mã nào")


def test_the_tower_is_done_when_no_layer_is_short_or_over():
    pyramid = {"layers": [{"id": "deposit", "status": "ok"}, {"id": "gold", "status": "short"}, {"id": "stocks", "status": "over"},
                          {"id": "reserve", "status": "fixed"}]}
    assert tower_fact(pyramid) == (False, "Vàng thiếu; Cổ phiếu vượt")
    assert tower_fact({"layers": [{"id": "deposit", "status": "ok"}]}) == (True, "mọi tầng trong khoảng")
    assert tower_fact(None) == (None, "chưa có Tháp tài sản")


def test_the_view_takes_the_checks_and_the_owners_ticks():
    facts = {"theses": (True, "x"), "tower": (False, "Vàng thiếu"), "calendar": (None, "không đọc được"), "drill": (True, "y"), "goals": (False, "z")}
    view = year_end_view(2026, facts=facts, ticks={"dividends"})
    by = {i["id"]: i for i in view["items"]}
    assert [i["id"] for i in view["items"]] == [k for k, _, _ in ITEMS]
    assert by["tower"] == {"id": "tower", "label": "Cân lại Tháp tài sản", "auto": True, "done": False, "detail": "Vàng thiếu"}
    assert by["calendar"]["done"] is None and by["dividends"]["done"] is True and by["cashflow"]["done"] is False
    assert view["year"] == 2026 and view["left"] == 4  # tower, calendar (not known counts as left), goals, cashflow


def test_reminders_go_once_on_or_after_each_day_while_something_is_left():
    assert reminder_due(date(2026, 11, 30), reminded=[]) is None
    assert reminder_due(date(2026, 12, 3), reminded=[]) == "2026-12-01"   # the machine was off on the first
    assert reminder_due(date(2026, 12, 3), reminded=["2026-12-01"]) is None
    assert reminder_due(date(2026, 12, 25), reminded=["2026-12-01"]) == "2026-12-20"
    assert reminder_due(date(2027, 1, 5), reminded=["2026-12-01", "2026-12-20"]) == "2027-01-05"
    assert reminder_due(date(2027, 2, 1), reminded=[]) is None


def test_the_reminder_lists_what_is_left():
    view = year_end_view(2026, facts={"theses": (False, "chưa rà trong 90 ngày: BBB"), "tower": (True, "ok"), "calendar": (True, "ok"),
                                      "drill": (True, "ok"), "goals": (True, "ok")}, ticks={"dividends"})
    assert render_reminder(view) == ("Việc cuối năm 2026: còn 2 việc\n"
                                     "- Rà luận điểm các mã đang giữ (chưa rà trong 90 ngày: BBB)\n"
                                     "- Nhập Thu chi tháng 12\n"
                                     "Xem và đánh dấu ở trang Năm tài chính.")
    done = year_end_view(2026, facts={k: (True, "") for k in ("theses", "tower", "calendar", "drill", "goals")}, ticks={"dividends", "cashflow"})
    assert render_reminder(done) is None
