from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.macro_chain import macro_chain

TODAY = date(2026, 10, 27)


def daily(start: date, values: list[str]) -> list[tuple[date, Decimal]]:
    return [(start + timedelta(days=i), Decimal(v)) for i, v in enumerate(values)]


def by_id(chain):
    return {n["id"]: n for n in chain["nodes"]}


def full():
    return {
        "wti": [(date(2026, 9, 20), Decimal("100")), (date(2026, 10, 20), Decimal("100")), (date(2026, 10, 24), Decimal("108"))],
        "vn_cpi_yoy": [(date(2026, 8, 31), Decimal("3.0")), (date(2026, 9, 30), Decimal("3.3"))],
        "vn_interbank_on": [(date(2026, 9, 20), Decimal("4.0")), (date(2026, 10, 25), Decimal("3.5"))],
        "vn10y": [(date(2026, 9, 20), Decimal("4.40")), (date(2026, 10, 26), Decimal("4.45"))],
        "foreign_net": daily(date(2026, 10, 20), ["-500", "200", "-300"]),
        "vnindex": [(date(2026, 9, 25), Decimal("1700")), (date(2026, 10, 27), Decimal("1650.5"))],
    }


def test_each_link_reads_its_one_month_direction_and_whether_it_weighs_on_stocks():
    chain = macro_chain(full(), today=TODAY)
    n = by_id(chain)
    assert [x["id"] for x in chain["nodes"]] == ["oil", "fuel", "inflation", "liquidity", "rates", "foreign", "vnindex"]
    # oil: 108 against the last price at least a month before the latest (100 on 20/09): +8% → up, weighs on stocks
    assert (n["oil"]["direction"], n["oil"]["effect"], n["oil"]["change"], n["oil"]["from"]) == ("up", "pressure", "0.08", "2026-09-20")
    assert (n["inflation"]["direction"], n["inflation"]["effect"], n["inflation"]["change"]) == ("up", "pressure", "0.30")  # points
    rates = n["rates"]
    assert (rates["direction"], rates["effect"]) == ("down", "support")  # interbank −0,5 point, 10-year +0,05 (flat)
    assert [(p["id"], p["direction"], p["change"]) for p in rates["parts"]] == [("vn_interbank_on", "down", "-0.50"), ("vn10y", "flat", "0.05")]
    assert (n["foreign"]["direction"], n["foreign"]["effect"], n["foreign"]["latest"]["value"], n["foreign"]["sessions"]) == ("sell", "pressure", "-600", 3)
    assert (n["vnindex"]["direction"], n["vnindex"]["effect"], n["vnindex"]["change"]) == ("flat", "neutral", "-0.0291")  # −2,9% is within ±3%
    assert chain["pressure"] == ["oil", "inflation", "foreign"] and chain["support"] == ["rates"] and chain["missing"] == ["fuel", "liquidity"]


def test_the_fuel_price_ceiling_sits_between_oil_and_inflation():
    s = {**full(), "vn_ron95_price": [(date(2026, 9, 20), Decimal("26000")), (date(2026, 10, 22), Decimal("25213"))]}
    n = by_id(macro_chain(s, today=TODAY))["fuel"]
    # 25,213 against 26,000 a month before: −3,0% → down, which eases prices
    assert (n["direction"], n["effect"], n["change"], n["from"], n["stale"]) == ("down", "support", "-0.0303", "2026-09-20", False)
    old = {**full(), "vn_ron95_price": [(date(2026, 9, 1), Decimal("26000")), (date(2026, 9, 20), Decimal("26100"))]}
    assert by_id(macro_chain(old, today=TODAY))["fuel"]["stale"] is True  # no new period for over a month


def test_a_series_with_no_data_is_missing_and_one_younger_than_a_month_says_since_when():
    s = full()
    s["vn_cpi_yoy"] = []
    s["vn_interbank_on"] = [(date(2026, 10, 7), Decimal("4.0")), (date(2026, 10, 25), Decimal("4.5"))]
    s["vn10y"] = [(date(2026, 10, 8), Decimal("4.40")), (date(2026, 10, 26), Decimal("4.70"))]
    chain = macro_chain(s, today=TODAY)
    n = by_id(chain)
    assert (n["inflation"]["effect"], n["inflation"]["latest"]) == ("missing", None)
    assert n["rates"]["direction"] == "up" and n["rates"]["short_history"] is True
    assert [p["from"] for p in n["rates"]["parts"]] == ["2026-10-07", "2026-10-08"]
    assert chain["missing"] == ["fuel", "inflation", "liquidity"] and "rates" in chain["pressure"]


def test_mixed_rate_moves_read_flat_and_an_old_value_is_marked_stale():
    s = full()
    s["vn10y"] = [(date(2026, 9, 20), Decimal("4.40")), (date(2026, 10, 26), Decimal("4.80"))]  # up while interbank is down
    s["wti"] = [(date(2026, 8, 1), Decimal("90")), (date(2026, 9, 10), Decimal("85"))]  # last price 47 days ago
    n = by_id(macro_chain(s, today=TODAY))
    assert (n["rates"]["direction"], n["rates"]["effect"]) == ("flat", "neutral")
    assert n["oil"]["stale"] is True and n["oil"]["direction"] == "down" and n["oil"]["effect"] == "support"
    assert n["vnindex"]["stale"] is False


def test_liquidity_reads_the_vnd_usd_spread_and_shows_the_latest_open_market_session():
    s = {**full(), "vnd_usd_spread": [(date(2026, 9, 20), Decimal("0.5")), (date(2026, 10, 24), Decimal("-0.3"))]}
    omo = {"date": "2026-10-24", "inject": "1000", "absorb": "0", "net": None}
    n = by_id(macro_chain(s, today=TODAY, omo=omo))["liquidity"]
    assert (n["direction"], n["effect"], n["change"]) == ("down", "pressure", "-0.80") and n["latest"] == {"date": "2026-10-24", "value": "-0.3"}
    assert n["omo"] == omo
    positive = {**full(), "vnd_usd_spread": [(date(2026, 10, 24), Decimal("0.4"))]}
    assert by_id(macro_chain(positive, today=TODAY))["liquidity"]["effect"] == "support"
