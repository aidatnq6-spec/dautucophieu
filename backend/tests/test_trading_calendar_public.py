"""Lịch giao dịch HOSE cho Claude (docs/superpowers/specs/2026-11-28-lich-giao-dich-mcp-design.md)."""

import json

import pytest

from investment_agent.public_tools import PublicData


def year_file(folder, year, holidays):
    (folder / f"trading-calendar-hose-{year}.json").write_text(json.dumps({
        "version": f"hose-{year}.1", "source": f"HOSE thông báo lịch nghỉ {year}", "verification": f"đã đối chiếu {year}",
        "first": f"{year}-01-01", "last": f"{year}-12-31", "holidays": holidays}, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def data(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    year_file(config, 2026, ["2026-01-01", "2026-11-24", "2026-12-26"])  # 26/12 is a Saturday: not a weekday holiday
    return PublicData(tmp_path / "data", config_dir=config)


def test_a_session_day_gives_the_sessions_either_side(data):
    out = data.lich_giao_dich("2026-11-25")
    assert out["co_phien"] is True and out["ly_do"] is None
    assert out["phien_truoc"] == "2026-11-23" and out["phien_sau"] == "2026-11-26"  # 24/11 is a holiday
    assert out["pham_vi"] == {"tu": "2026-01-01", "den": "2026-12-31"} and out["phien_ban"] == "hose-2026.1"
    assert out["nguon"] == "HOSE thông báo lịch nghỉ 2026" and out["xac_minh"] == "đã đối chiếu 2026"


def test_a_weekend_and_a_holiday_say_why_there_is_no_session(data):
    sat = data.lich_giao_dich("2026-11-28")
    assert (sat["co_phien"], sat["ly_do"], sat["phien_truoc"], sat["phien_sau"]) == (False, "cuối tuần", "2026-11-27", "2026-11-30")
    assert data.lich_giao_dich("2026-11-24")["ly_do"] == "ngày nghỉ theo lịch HOSE"


def test_sessions_between_two_days_count_both_ends_in_either_order(data):
    out = data.lich_giao_dich("2026-11-20", "2026-11-30")
    assert out["so_phien"] == 6 and out["cac_phien"] == ["2026-11-20", "2026-11-23", "2026-11-25", "2026-11-26", "2026-11-27", "2026-11-30"]
    assert data.lich_giao_dich("2026-11-30", "2026-11-20")["so_phien"] == 6


def test_the_holidays_left_are_weekday_holidays_from_the_day(data):
    assert data.lich_giao_dich("2026-11-20")["ngay_nghi_con_lai"] == ["2026-11-24"]


def test_a_neighbour_past_the_calendar_is_null_with_the_reason(data):
    out = data.lich_giao_dich("2026-12-31")
    assert out["phien_sau"] is None and out["ly_do_phien_sau"] == "chưa có lịch giao dịch HOSE năm 2027 trong kho"
    assert data.lich_giao_dich("2026-01-02")["phien_truoc"] is None  # 01/01 is a holiday, 2025 is not in the folder


def test_a_day_outside_the_calendar_or_badly_written_is_missing(data):
    out = data.lich_giao_dich("2027-01-05")
    assert out["thieu"] is True and out["ly_do"] == "chưa có lịch giao dịch HOSE năm 2027 trong kho"
    assert data.lich_giao_dich("2026-13-01") == {"thieu": True, "ly_do": "Ngày không hợp lệ (cần YYYY-MM-DD)."}
    assert data.lich_giao_dich("2026-11-25", "2027-02-01")["thieu"] is True


def test_joined_years_count_across_new_year_and_a_long_list_is_left_out(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    year_file(config, 2025, ["2025-12-31"])
    year_file(config, 2026, ["2026-01-01"])
    data = PublicData(tmp_path / "data", config_dir=config)
    assert data.lich_giao_dich("2025-12-31")["phien_truoc"] == "2025-12-30" and data.lich_giao_dich("2025-12-31")["phien_sau"] == "2026-01-02"
    long = data.lich_giao_dich("2025-01-01", "2026-12-31")
    assert long["so_phien"] > 260 and long["cac_phien"] is None
