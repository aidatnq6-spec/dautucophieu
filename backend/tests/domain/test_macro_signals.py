from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.macro_signals import macro_signals, signal_changes

TODAY = date(2026, 10, 28)

def days(end: date, values: list[str]) -> list[tuple[date, Decimal]]:
    return [(end - timedelta(days=len(values) - 1 - i), Decimal(v)) for i, v in enumerate(values)]


def base():
    return {
        "factor_oil": [(date(2026, 9, 18), Decimal("101.44")), (date(2026, 10, 20), Decimal("107.89"))],  # +6,4%
        "factor_usd": [(date(2026, 9, 23), Decimal("120")), (date(2026, 10, 23), Decimal("121.2"))],      # +1%
        "usd_vnd_free": [(date(2026, 10, 25), Decimal("26450")), (date(2026, 10, 27), Decimal("26500"))],
        "usd_vnd_vcb": [(date(2026, 10, 25), Decimal("26010")), (date(2026, 10, 27), Decimal("26020"))],   # 1,84% → yellow
        "foreign_net": days(date(2026, 10, 27), ["300", "-200", "-100", "-50"]),                          # 3 selling sessions
        "vn_interbank_on": [(date(2026, 10, 25), Decimal("3.10"))],
    }


def by_id(signals):
    return {s["id"]: s for s in signals}


def test_each_light_against_its_yellow_and_red_thresholds():
    s = by_id(macro_signals(base(), today=TODAY))
    assert [x["id"] for x in macro_signals(base(), today=TODAY)] == ["oil", "usd", "fx_gap", "foreign", "interbank"]
    assert (s["oil"]["level"], s["oil"]["value"], s["oil"]["yellow"], s["oil"]["red"]) == ("green", "0.0636", "0.10", "0.20")
    assert (s["usd"]["level"], s["usd"]["value"]) == ("green", "0.01")
    assert (s["fx_gap"]["level"], s["fx_gap"]["value"], s["fx_gap"]["latest_date"]) == ("yellow", "0.0184", "2026-10-27")
    assert (s["foreign"]["level"], s["foreign"]["value"]) == ("green", "3")
    assert (s["interbank"]["level"], s["interbank"]["value"]) == ("green", "3.1")


def test_red_at_or_past_the_red_threshold():
    data = base()
    data["factor_oil"] = [(date(2026, 9, 20), Decimal("100")), (date(2026, 10, 20), Decimal("120"))]
    data["factor_usd"] = [(date(2026, 9, 23), Decimal("100")), (date(2026, 10, 23), Decimal("103"))]
    data["foreign_net"] = days(date(2026, 10, 27), ["-1"] * 10)
    data["vn_interbank_on"] = [(date(2026, 10, 25), Decimal("7"))]
    s = by_id(macro_signals(data, today=TODAY))
    assert {k: v["level"] for k, v in s.items()} == {"oil": "red", "usd": "yellow", "fx_gap": "yellow", "foreign": "red", "interbank": "red"}


def test_missing_data_and_a_short_history_say_so():
    data = base()
    data["usd_vnd_vcb"] = []
    data["vn_interbank_on"] = []
    s = by_id(macro_signals(data, today=TODAY))
    assert s["fx_gap"]["level"] == "missing" and s["interbank"]["level"] == "missing"
    assert s["foreign"]["since"] == "2026-10-24"  # under 30 days stored


def test_the_spark_is_the_last_30_days_of_what_is_measured():
    data = base()
    data["factor_oil"] = days(date(2026, 10, 20), [str(80 + i) for i in range(60)])
    s = by_id(macro_signals(data, today=TODAY))
    spark = s["oil"]["spark"]
    assert spark[0]["date"] == "2026-09-20" and spark[-1] == {"date": "2026-10-20", "value": "139"} and s["oil"]["since"] is None
    assert [p["value"] for p in s["fx_gap"]["spark"]] == ["0.0169", "0.0184"]  # the gap itself, on the days both rates exist


def test_changes_are_reported_only_when_a_light_moves_and_never_on_the_first_run():
    current = macro_signals(base(), today=TODAY)
    assert signal_changes(None, current) == []
    assert signal_changes({"oil": "green", "usd": "green", "fx_gap": "yellow", "foreign": "green", "interbank": "green"}, current) == []
    moved = signal_changes({"oil": "red", "usd": "green", "fx_gap": "green", "foreign": "green", "interbank": "missing"}, current)
    assert moved == ["Giá dầu WTI: đỏ → xanh (+6,4% trong 30 ngày)", "Tỷ giá tự do so với Vietcombank: xanh → vàng (tự do cao hơn 1,84%)"]


def test_a_figure_past_its_age_is_said_to_be_old_and_not_coloured():
    """Each light's own limit (spec 21/11/2026): oil 10 days, USD 14, the rest 7. An old figure never stands for today."""
    data = base()
    data["vn_interbank_on"] = [(date(2026, 10, 20), Decimal("7.5"))]  # 8 days before TODAY
    s = by_id(macro_signals(data, today=TODAY))
    assert (s["interbank"]["level"], s["interbank"]["value"], s["interbank"]["latest_date"]) == ("stale", "7.5", "2026-10-20")
    assert s["oil"]["level"] == "green"  # 20/10 is 8 days old, within oil's 10
    assert by_id(macro_signals(data, today=date(2026, 10, 31)))["oil"]["level"] == "stale"
    assert signal_changes({"interbank": "red"}, macro_signals(data, today=TODAY)) == []  # to or from old says nothing
