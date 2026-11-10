from decimal import Decimal as D

from investment_agent.domain.earnings_season import cash_rows, sector_table, season_rows, target_quarter

B = 10**9


def quarter(npat, cfo=None, liabilities=None, debt=0):
    out = {"npat_parent": str(npat * B), "npat": str(npat * B)}
    if cfo is not None:
        out["cfo"] = str(cfo * B)
    if liabilities is not None:
        out |= {"liabilities": str(liabilities * B), "st_debt": str(debt * B), "lt_debt": "0"}
    return out


def history(by_quarter: dict[str, int], **extra) -> dict:
    return {k: quarter(v, **extra.get(k, {})) for k, v in by_quarter.items()}


def year(y, a, b, c, d):
    return {f"{y}-Q1": a, f"{y}-Q2": b, f"{y}-Q3": c, f"{y}-Q4": d}


# Three made-up tickers of one sector; "BIG" drives the sector as VHM did in the owner's video.
BIG = history({**year(2023, 10, 10, 10, 10), **year(2024, 10, 10, 10, 10), **year(2025, 10, 10, 10, 10), "2026-Q1": 20, "2026-Q2": 30, "2026-Q3": 50})
PAPER = history({**year(2025, 10, 10, 10, 10), "2026-Q1": 10, "2026-Q2": 10, "2026-Q3": 8},
                **{"2026-Q1": {"cfo": -5}, "2026-Q2": {"cfo": -5}, "2026-Q3": {"cfo": -6}})
CASHY = history({**year(2025, 10, 10, 10, 10), "2026-Q1": 5, "2026-Q2": 5, "2026-Q3": 4},
                **{"2025-Q4": {"liabilities": 100, "debt": 40}, "2026-Q1": {"cfo": 20}, "2026-Q2": {"cfo": 20}, "2026-Q3": {"cfo": 20, "liabilities": 180, "debt": 40}})
LATE = history(year(2025, 10, 10, 10, 10))  # has not reported 2026-Q3 yet
RECORDS = {"BIG": BIG, "PAPER": PAPER, "CASHY": CASHY, "LATE": LATE}
SECTORS = {"BIG": "Bất động sản", "PAPER": "Bất động sản", "CASHY": "Bất động sản", "LATE": "Bất động sản"}


def rows(**more):
    out = season_rows(RECORDS, SECTORS, target="2026-Q3", held={"PAPER"}, **more)
    return {r["symbol"]: r for r in out}


def test_the_season_is_the_latest_quarter_anyone_has():
    assert target_quarter(RECORDS) == "2026-Q3" and target_quarter({}) is None


def test_each_ticker_against_the_same_quarter_the_quarter_before_and_the_year_so_far():
    r = rows()["BIG"]
    assert (r["reported"], r["npat"], r["yoy"], r["qoq"]) == (True, str(50 * B), "4.0000", "0.6667")
    assert (r["ytd"], r["ytd_yoy"]) == (str(100 * B), "2.3333")  # 100 against 30
    assert rows()["LATE"]["reported"] is False and rows()["LATE"]["yoy"] is None
    assert rows()["PAPER"]["held"] is True and rows()["BIG"]["held"] is False


def test_a_quarter_that_usually_carries_a_share_of_the_year_says_so():
    assert rows()["BIG"]["seasonal_share"] == "0.2500"  # three full years, a quarter each
    assert rows()["PAPER"]["seasonal_share"] == "0.2500"  # one full year is enough to state it


def test_the_owners_plan_and_forecast_are_set_against_the_result():
    r = rows(plans={"BIG": {"ratio": "0.8333", "label": "LNST"}}, forecasts={"BIG": D(40 * B)})["BIG"]
    assert (r["plan_ratio"], r["vs_forecast"], r["forecast"]) == ("0.8333", "0.2500", str(40 * B))
    assert rows()["BIG"]["vs_forecast"] is None


def test_the_review_after_the_report_is_shown_for_held_tickers():
    assert rows(reviews={"PAPER": "keep"})["PAPER"]["review"] == "keep" and rows()["PAPER"]["review"] is None


def test_a_sector_shows_how_much_one_ticker_carried_and_its_growth_without_it():
    s = sector_table(list(rows().values()))[0]
    assert (s["sector"], s["count"], s["reported"]) == ("Bất động sản", 4, 3)
    assert (s["ytd_now"], s["ytd_ago"], s["ytd_growth"]) == (str(142 * B), str(90 * B), "0.5778")
    assert (s["top"], s["top_share"], s["ytd_growth_without_top"]) == ("BIG", "1.3462", "-0.3000")  # BIG adds 70 of a 52 rise; the other two fall from 60 to 42
    assert (s["up"], s["down"]) == (1, 2)


def test_profit_without_cash_and_cash_far_above_profit_are_named_with_other_liabilities():
    c = {r["symbol"]: r for r in cash_rows(RECORDS, target="2026-Q3")}
    assert (c["PAPER"]["npat"], c["PAPER"]["cfo"], c["PAPER"]["kind"]) == (str(28 * B), str(-16 * B), "paper_profit")
    assert (c["CASHY"]["kind"], c["CASHY"]["ratio"], c["CASHY"]["other_liabilities_change"]) == ("cash_above", "4.2857", str(80 * B))
    assert "BIG" not in c  # no cash flow stored: not judged
