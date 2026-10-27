import random
from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.sensitivity import exposure, sensitivity

END = date(2026, 10, 23)  # a Friday


def walk(returns, start=Decimal(100)):
    """Weekly closes on Fridays ending at END from a list of weekly returns."""
    n, level, points = len(returns), start, []
    for i, r in enumerate([0.0, *returns]):
        level = level * (1 + Decimal(str(r)))
        points.append((END - timedelta(weeks=n - i), level))
    return points


def market(weeks=160, seed=7):
    rng = random.Random(seed)
    index = [rng.gauss(0.002, 0.025) for _ in range(weeks)]
    oil = [rng.gauss(0, 0.05) for _ in range(weeks)]
    usd = [rng.gauss(0, 0.01) for _ in range(weeks)]
    return rng, index, oil, usd


def stock(rng, index, oil, usd, *, b_oil=0.0, b_usd=0.0):
    return [i + b_oil * o + b_usd * u + rng.gauss(0, 0.01) for i, o, u in zip(index, oil, usd)]


def test_a_stock_that_moves_with_oil_beyond_the_market_is_read_as_benefiting():
    rng, index, oil, usd = market()
    s = sensitivity(walk(stock(rng, index, oil, usd, b_oil=0.2)), index=walk(index), oil=walk(oil), usd=walk(usd))
    assert s["status"] == "ok" and s["weeks"] == 156  # the last three years
    assert abs(Decimal(s["oil"]["beta"]) - Decimal("0.2")) < Decimal("0.03") and s["oil"]["class"] == "benefit"
    assert s["usd"]["class"] == "unclear"


def test_a_stock_hurt_by_oil_and_helped_by_a_strong_dollar():
    rng, index, oil, usd = market(seed=11)
    s = sensitivity(walk(stock(rng, index, oil, usd, b_oil=-0.3, b_usd=0.8)), index=walk(index), oil=walk(oil), usd=walk(usd))
    assert s["oil"]["class"] == "hurt" and Decimal(s["oil"]["beta"]) < 0
    assert s["usd"]["class"] == "benefit"


def test_noise_alone_is_unclear_and_less_than_a_year_is_not_enough():
    # |t| >= 2 is crossed by chance about 1 time in 20: across 40 noise-only stocks (80 readings) few should be classed
    classed = 0
    for seed in range(40):
        rng, index, oil, usd = market(seed=seed)
        s = sensitivity(walk(stock(rng, index, oil, usd)), index=walk(index), oil=walk(oil), usd=walk(usd))
        classed += (s["oil"]["class"] != "unclear") + (s["usd"]["class"] != "unclear")
    assert classed <= 10
    young = walk(stock(rng, index[-40:], oil[-40:], usd[-40:]))
    assert sensitivity(young, index=walk(index), oil=walk(oil), usd=walk(usd)) == {"status": "insufficient", "weeks": 40}


def test_daily_closes_are_reduced_to_the_last_close_of_each_week():
    rng, index, oil, usd = market(seed=5)
    weekly = walk(stock(rng, index, oil, usd, b_oil=0.2))
    daily = []
    for day, close in weekly:  # add Monday..Thursday closes that the weekly reading must ignore
        daily += [(day - timedelta(days=k), close * Decimal("1.3")) for k in (4, 3, 2, 1)] + [(day, close)]
    a = sensitivity(weekly, index=walk(index), oil=walk(oil), usd=walk(usd))
    b = sensitivity(daily, index=walk(index), oil=walk(oil), usd=walk(usd))
    assert a == b


def test_exposure_is_the_share_of_held_cost_in_each_class():
    results = {"GAS": {"status": "ok", "oil": {"class": "benefit"}, "usd": {"class": "unclear"}},
               "HAH": {"status": "ok", "oil": {"class": "hurt"}, "usd": {"class": "hurt"}},
               "FPT": {"status": "ok", "oil": {"class": "unclear"}, "usd": {"class": "unclear"}},
               "NEW": {"status": "insufficient", "weeks": 10}}
    e = exposure(results, {"GAS": Decimal(300), "HAH": Decimal(100), "FPT": Decimal(500), "NEW": Decimal(100)})
    assert e == {"total": "1000", "oil": {"benefit": "0.3", "hurt": "0.1"}, "usd": {"benefit": "0", "hurt": "0.1"}, "insufficient": "0.1"}
    assert exposure(results, {}) is None
