"""Số đã công bố bị sửa (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-phai-thu-ho-to-design.md): a closed period's figure that
changes by more than both 1% and 1 tỷ is logged with the old and new figure and the day seen; no cause is inferred."""

from datetime import date

from investment_agent.market.statement_revisions import find_revisions, read_revisions, record_revisions, revisions_note_run

OLD = {"2024": {"npat_parent": "100000000000", "pbt": "120000000000", "equity": "900000000000", "bad_debt_st": "-5000000000", "selling": "1"},
       "2025": {"npat_parent": "150000000000", "pbt": "180000000000"}}


def test_a_closed_period_changed_beyond_both_limits_is_found_and_the_latest_period_is_not():
    new = {"2024": {"npat_parent": "80000000000",       # −20 tỷ, −20%: found
                    "pbt": "120500000000",             # +0.5 tỷ: under 1 tỷ
                    "equity": "909000000000",          # +9 tỷ but exactly 1%: not beyond
                    "bad_debt_st": "-7000000000",      # provision 5 → 7 tỷ: found
                    "selling": "999999999999"},        # not a watched line
           "2025": {"npat_parent": "90000000000"}}     # the latest period: still moving, not a revision
    got = find_revisions(OLD, new)
    assert got == [{"period": "2024", "line": "bad_debt_st", "old": "-5000000000", "new": "-7000000000"},
                   {"period": "2024", "line": "npat_parent", "old": "100000000000", "new": "80000000000"}]
    assert find_revisions({}, new) == []  # the first sync only sets the baseline


def test_the_inventory_provision_of_a_closed_period_is_watched_too():
    """Dự phòng chốt khi kiểm toán (owner, 23/11/2026): the inventory provision joins the lines whose revisions are logged."""
    got = find_revisions({"2024": {"inventory_provision": "-504000000000"}, "2025": {}}, {"2024": {"inventory_provision": "-560000000000"}})
    assert got == [{"period": "2024", "line": "inventory_provision", "old": "-504000000000", "new": "-560000000000"}]


def test_the_log_keeps_each_revision_once_with_the_day_seen(tmp_path):
    rev = [{"period": "2024", "line": "npat_parent", "old": "100000000000", "new": "80000000000"}]
    record_revisions(tmp_path, "HAG", rev, kind="years", seen_on=date(2026, 11, 22))
    record_revisions(tmp_path, "HAG", rev, kind="years", seen_on=date(2026, 11, 29))  # the same change seen again
    assert read_revisions(tmp_path, "HAG") == [{**rev[0], "kind": "years", "seen_on": "2026-11-22"}]
    assert read_revisions(tmp_path, "FPT") == []


def test_a_held_tickers_new_revision_goes_once_in_danh_muc_hom_nay(tmp_path):
    record_revisions(tmp_path, "HAG", [{"period": "2024", "line": "npat_parent", "old": "100000000000", "new": "80000000000"}],
                     kind="years", seen_on=date(2026, 11, 22))
    record_revisions(tmp_path, "FPT", [{"period": "2025-Q2", "line": "pbt", "old": "3000000000000", "new": "2900000000000"}],
                     kind="quarters", seen_on=date(2026, 11, 22))
    sent = []
    keep = lambda t: sent.append(t) or True  # noqa: E731
    assert revisions_note_run(tmp_path, held={"HAG"}, send=lambda t: False, today=date(2026, 11, 22)) == {"new": 1, "sent": False}
    assert revisions_note_run(tmp_path, held={"HAG"}, send=keep, today=date(2026, 11, 22)) == {"new": 1, "sent": True}
    assert revisions_note_run(tmp_path, held={"HAG"}, send=keep, today=date(2026, 11, 23)) == {"new": 0, "sent": False}
    assert sent == ["Số đã công bố bị sửa\nHAG năm 2024, LNST công ty mẹ: 100 tỷ → 80 tỷ (thấy 22/11/2026)\n"
                    "Có thể do điều chỉnh hồi tố hoặc nguồn sửa lỗi nhập; xem thuyết minh và báo cáo kiểm toán."]


def test_revenue_cost_of_sales_and_gross_profit_are_watched_too_owner_25_11_2026():
    """Bài doanh thu, giá vốn (HAG): a restatement moved costs back into the cost of sales of earlier years; those lines join the watch."""
    got = find_revisions({"2024": {"revenue": "2075000000000", "cogs": "1848000000000", "gross_profit": "228000000000"}, "2025": {}},
                         {"2024": {"revenue": "2075000000000", "cogs": "1990000000000", "gross_profit": "86000000000"}})
    assert got == [{"period": "2024", "line": "cogs", "old": "1848000000000", "new": "1990000000000"},
                   {"period": "2024", "line": "gross_profit", "old": "228000000000", "new": "86000000000"}]
