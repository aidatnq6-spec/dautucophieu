import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cashflow_fixture import month_rows, workbook  # noqa: E402

from investment_agent.domain.cashflow_workbook import CashflowFileError, parse_cashflow_xlsx  # noqa: E402
from investment_agent.services.cashflow import cashflow_view, lifestyle_history, merge_import, passive_actual  # noqa: E402


def test_each_month_is_read_by_column_name_with_its_sources_and_groups():
    out = parse_cashflow_xlsx(workbook())
    assert out["year"] == 2026 and sorted(out["months"]) == [f"2026-{m:02d}" for m in range(1, 11)]
    jan = out["months"]["2026-01"]
    assert (jan["income"], jan["spending"]) == ("61000000", "40500000")
    assert jan["sources"]["Căn hộ cho thuê"] == "20000000" and jan["sources"]["Cổ phiếu"] == "3000000"
    meta = {s["label"]: s for s in out["sources"]}
    assert meta["Căn hộ cho thuê"]["passive"] and meta["Tiền gửi"]["passive"] and meta["Trái phiếu"]["passive"]
    assert not meta["Cổ phiếu"]["passive"] and not meta["Youtube, Tiktok, Affiliate"]["passive"]
    assert (meta["CA HĐĐT BHXH"]["group"], meta["Tiền gửi"]["group"]) == ("business", "portfolio")
    assert "Tổng Chi" not in meta and not any("%" in k for k in meta)


def test_a_month_not_yet_entered_is_left_out_and_one_excel_has_not_worked_out_is_named():
    rows = {**month_rows(range(1, 4)), 4: {"D": None, "E": None}}
    out = parse_cashflow_xlsx(workbook(rows, uncached={(3, "D")}))
    assert sorted(out["months"]) == ["2026-01", "2026-02"]
    assert any("Tháng 3" in w and "Excel" in w for w in out["warnings"])


def test_a_blank_source_is_nothing_that_month():
    rows = month_rows(range(1, 2))
    rows[1]["P"] = None
    assert parse_cashflow_xlsx(workbook(rows))["months"]["2026-01"]["sources"]["Cổ phiếu"] == "0"


@pytest.mark.parametrize("data,words", [(b"not a zip", "xlsx"), (workbook(total_name="Khác"), "Tổng")])
def test_a_wrong_file_is_refused_with_a_reason(data, words):
    with pytest.raises(CashflowFileError) as e:
        parse_cashflow_xlsx(data)
    assert words in str(e.value)


def test_the_view_gives_savings_passive_income_and_three_month_averages():
    stored = merge_import({}, parse_cashflow_xlsx(workbook()), imported_at="2026-11-10T08:00:00+07:00")
    v = cashflow_view(stored, today=date(2026, 11, 10), birth_year=1985)
    oct_ = v["months"][-1]
    assert oct_["month"] == "2026-10" and oct_["saved"] == "25000000" and oct_["passive"] == "23000000" and oct_["rate"] == "0.3571"
    assert v["age"] == 41 and v["average"]["months"] == ["2026-08", "2026-09", "2026-10"] and v["average"]["passive"] == "23000000"
    assert passive_actual(stored, today=date(2026, 11, 10)) == "23000000"


def test_the_month_being_written_is_marked_and_left_out_of_the_averages():
    stored = merge_import({}, parse_cashflow_xlsx(workbook(month_rows(range(9, 12)))), imported_at="x")
    v = cashflow_view(stored, today=date(2026, 11, 10), birth_year=None)
    assert v["months"][-1]["current"] is True and v["average"]["months"] == ["2026-09", "2026-10"] and v["age"] is None


def test_a_new_import_replaces_that_years_months_and_keeps_other_years():
    first = merge_import({}, parse_cashflow_xlsx(workbook(year=2025)), imported_at="a")
    both = merge_import(first, parse_cashflow_xlsx(workbook(month_rows(range(1, 3)))), imported_at="b")
    assert sorted(both["months"])[:2] == ["2025-01", "2025-02"] and "2026-03" not in both["months"] and "2026-02" in both["months"]


def test_lifestyle_reads_income_and_spending():
    stored = merge_import({}, parse_cashflow_xlsx(workbook(month_rows(range(1, 2)))), imported_at="a")
    assert lifestyle_history(stored) == {"2026-01": {"income": "61000000", "expenses": "40500000"}}
