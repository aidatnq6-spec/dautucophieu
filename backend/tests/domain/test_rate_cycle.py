from datetime import date

from investment_agent.domain.rate_cycle import rate_cycle, six_month_direction

TODAY = date(2026, 10, 27)


def test_direction_compares_the_latest_value_with_about_six_months_earlier():
    up = [(date(2026, 3, 31), "4.50"), (date(2026, 4, 30), "4.60"), (date(2026, 10, 26), "5.10")]
    assert six_month_direction(up, today=TODAY) == {"direction": "up", "change": "0.60", "from": "2026-03-31", "latest": "5.10"}
    flat = [(date(2026, 4, 1), "4.00"), (date(2026, 10, 26), "4.20")]
    assert six_month_direction(flat, today=TODAY)["direction"] == "flat"     # within ±0.25 points
    down = [(date(2026, 4, 1), "6.00"), (date(2026, 10, 26), "5.50")]
    assert six_month_direction(down, today=TODAY)["direction"] == "down"


def test_less_than_six_months_of_data_is_not_enough():
    assert six_month_direction([(date(2026, 10, 8), "3.1"), (date(2026, 10, 26), "3.2")], today=TODAY) is None
    assert six_month_direction([], today=TODAY) is None


def test_vietnam_rates_are_used_when_they_cover_six_months():
    series = {"deposit_12m": [(date(2026, 4, 1), "6.0"), (date(2026, 10, 26), "5.4")], "vn10y": [(date(2026, 4, 1), "3.3"), (date(2026, 10, 26), "3.0")],
              "fed_effr": [(date(2026, 4, 1), "4.3"), (date(2026, 10, 26), "4.8")], "us10y": [(date(2026, 4, 1), "4.2"), (date(2026, 10, 26), "4.9")]}
    c = rate_cycle(series, today=TODAY)
    assert c["basis"] == "vietnam" and c["phase"] == "down" and [s["id"] for s in c["series"]] == ["deposit_12m", "vn10y"]


def test_without_six_months_of_vietnam_data_the_us_is_the_reference():
    series = {"deposit_12m": [(date(2026, 10, 25), "5.63")], "vn10y": [(date(2026, 10, 8), "3.1"), (date(2026, 10, 26), "3.2")],
              "fed_effr": [(date(2026, 4, 1), "4.33"), (date(2026, 10, 23), "3.86")], "us10y": [(date(2026, 4, 1), "4.20"), (date(2026, 10, 23), "4.05")]}
    c = rate_cycle(series, today=TODAY)
    assert c["basis"] == "us_reference" and c["phase"] == "down"
    assert c["vietnam_since"] == "2026-10-08" and c["vietnam_ready_on"] == "2027-04-08"
    assert [s["id"] for s in c["series"]] == ["fed_effr", "us10y"]


def test_mixed_directions_are_flat():
    series = {"deposit_12m": [(date(2026, 4, 1), "6.0"), (date(2026, 10, 26), "5.4")], "vn10y": [(date(2026, 4, 1), "3.0"), (date(2026, 10, 26), "3.5")]}
    assert rate_cycle(series, today=TODAY)["phase"] == "flat"


def test_nothing_usable_at_all():
    assert rate_cycle({}, today=TODAY)["phase"] is None
