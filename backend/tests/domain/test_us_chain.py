from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.us_chain import us_chain

TODAY = date(2026, 11, 16)


def daily(start_value, end_value, days=10):
    """A series from start_value (10 days ago) to end_value (today), one point a day."""
    step = (Decimal(end_value) - Decimal(start_value)) / (days - 1)
    return [(TODAY - timedelta(days=days - 1 - i), Decimal(start_value) + step * i) for i in range(days)]


SERIES = {
    "us_cpi_yoy": [(date(2026, 8, 1), Decimal("3.3")), (date(2026, 9, 1), Decimal("3.4")), (date(2026, 10, 1), Decimal("3.7"))],
    "us_core_cpi_yoy": [(date(2026, 8, 1), Decimal("2.45")), (date(2026, 9, 1), Decimal("2.56"))],
    "fed_effr": daily("3.88", "3.88"),
    "us10y": daily("4.10", "4.30"),
    "dxy": daily("101", "103.38"),
    "gold": daily("13900000", "13450000"),
    "usd_vnd_vcb": daily("26300", "26310"),
}


def test_a_rising_cpi_sets_a_tightening_chain_and_each_link_is_read_over_the_week():
    out = us_chain(SERIES, today=TODAY)
    assert out["mode"] == "tightening" and out["driver"] == "us_cpi"
    nodes = {n["id"]: n for n in out["nodes"]}
    cpi = nodes["us_cpi"]
    assert cpi["fit"] == "driver" and cpi["direction"] == "up" and cpi["change"] == "0.30" and cpi["latest"] == {"date": "2026-10-01", "value": "3.7"}
    assert cpi["core"] == {"date": "2026-09-01", "value": "2.56", "change": "0.11"}
    rates = nodes["us_rates"]
    assert rates["direction"] == "up" and rates["fit"] == "with"
    assert [(p["id"], p["direction"]) for p in rates["parts"]] == [("fed_effr", "flat"), ("us10y", "up")]
    assert rates["parts"][1]["from"] == "2026-11-09" and rates["parts"][1]["change"] == "0.16"  # a week before the latest point
    assert (nodes["dxy"]["direction"], nodes["dxy"]["fit"]) == ("up", "with")
    assert (nodes["gold"]["direction"], nodes["gold"]["fit"]) == ("down", "with")  # gold is expected to fall when the chain tightens
    assert (nodes["usd_vnd"]["direction"], nodes["usd_vnd"]["fit"]) == ("flat", "flat")
    assert out["with"] == ["us_rates", "dxy", "gold"] and out["against"] == [] and out["flat"] == ["usd_vnd"]


def test_a_link_going_the_other_way_is_against_the_chain_and_a_flat_cpi_hands_the_lead_to_rates():
    s = {**SERIES, "dxy": daily("103", "101")}
    assert {n["id"]: n["fit"] for n in us_chain(s, today=TODAY)["nodes"]}["dxy"] == "against"
    flat_cpi = {**SERIES, "us_cpi_yoy": SERIES["us_cpi_yoy"][:2] + [(date(2026, 10, 1), Decimal("3.45"))], "us10y": daily("4.40", "4.10")}
    out = us_chain(flat_cpi, today=TODAY)
    assert out["driver"] == "us_rates" and out["mode"] == "easing"
    nodes = {n["id"]: n for n in out["nodes"]}
    assert nodes["us_cpi"]["fit"] == "flat" and nodes["us_rates"]["fit"] == "driver"
    calm = us_chain({**flat_cpi, "us10y": daily("4.10", "4.12")}, today=TODAY)
    assert calm["mode"] is None and all(n["fit"] in ("flat", "none") for n in calm["nodes"])


def test_a_missing_or_short_series_is_said():
    out = us_chain({"us_cpi_yoy": SERIES["us_cpi_yoy"], "gold": [(TODAY - timedelta(days=2), Decimal("13450000")), (TODAY, Decimal("13450000"))]},
                   today=TODAY)
    nodes = {n["id"]: n for n in out["nodes"]}
    assert nodes["dxy"]["fit"] == "missing" and nodes["us_rates"]["fit"] == "missing"
    assert nodes["gold"]["short_history"] is True and nodes["gold"]["from"] == "2026-11-14"
    assert out["missing"] == ["us_rates", "dxy", "usd_vnd"]
