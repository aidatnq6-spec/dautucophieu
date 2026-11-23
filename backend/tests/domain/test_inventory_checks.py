"""Tồn kho: ba căn cứ kiểm kê và giá hàng hóa (owner, 23/11/2026; docs/superpowers/specs/2026-11-23-ton-kho-kiem-ke-design.md). Made-up figures."""

from investment_agent.domain.balance_watch import cover_thinning, gross_loss

B = 1_000_000_000


def q(gp, gross, provision, net=None, assets=1000):
    """A quarter in đồng: gross profit, inventory at cost and its provision (negative, as VNDirect gives it), net, total assets."""
    net = gross - provision if net is None else net
    return {"gross_profit": str(gp * B), "inventory_gross": str(gross * B), "inventory_provision": str(-provision * B), "inventory": str(net * B),
            "total_assets": str(assets * B)}


def test_a_gross_loss_with_the_share_provided_for_not_up_is_flagged_with_its_figures():
    v = gross_loss({"2026-Q2": q(20, 300, 6), "2026-Q3": q(-5, 320, 6)})
    assert v == {"quarter": "2026-Q3", "gross_profit": "-5000000000", "coverage": "0.0188", "coverage_prev": "0.0200", "share": "0.3140", "flag": True}


def test_a_loss_met_by_a_larger_provision_or_a_profit_is_no_sign():
    assert gross_loss({"2026-Q2": q(20, 300, 6), "2026-Q3": q(-5, 300, 9)})["flag"] is False  # cover 2% → 3%: the loss is being provided for
    assert gross_loss({"2026-Q2": q(20, 300, 6), "2026-Q3": q(0, 320, 6)})["flag"] is False  # a nil gross profit is not a loss


def test_small_inventory_property_and_missing_figures():
    assert gross_loss({"2026-Q2": q(20, 30, 1), "2026-Q3": q(-5, 30, 1)})["flag"] is False  # net inventory 2,9% of assets: under the 10%
    assert gross_loss({"2026-Q2": q(20, 300, 6), "2026-Q3": q(-5, 320, 6)}, property=True)["flag"] is False
    v = gross_loss({"2026-Q3": q(-5, 320, 6)})
    assert v["flag"] is None and v["coverage_prev"] is None  # no quarter before: never flagged on a guess
    assert gross_loss({})["quarter"] is None


def year(cogs, gross, provision, assets=1000, last="2026"):
    """Two years at 100 of cost of sales a quarter, then `cogs` a quarter; inventory at cost and provision at the last two Q3s."""
    out = {}
    for y, c in ((int(last) - 2, 100), (int(last) - 1, 100), (int(last), cogs)):
        for n in range(1, 5):
            out[f"{y}-Q{n}"] = {"cogs": str(c * B)}
    out[f"{int(last) - 1}-Q3"].update(q(10, 200, 10, assets=assets))
    out[f"{last}-Q3"].update(q(10, gross, provision, assets=assets))
    return {k: v for k, v in out.items() if k <= f"{last}-Q3"}


def test_days_up_20_percent_while_the_share_provided_for_thins_20_percent_is_flagged():
    """Dự phòng mỏng dần trong khi hàng tồn lâu hơn (owner, 23/11/2026): days of inventory (net / four quarters' cost × 365) up from 20% on a
    year, the share provided for down from 20% of its level a year before; material inventory only."""
    v = cover_thinning(year(100, 260, 10))  # net 250 against 190: days 228 against 173 (+32%); cover 3,85% against 5% (−23%)
    assert (v["quarter"], v["days"], v["days_year_ago"], v["coverage"], v["coverage_year_ago"], v["flag"]) == ("2026-Q3", 228, 173, "0.0385", "0.0500", True)
    assert cover_thinning(year(100, 260, 11))["flag"] is False  # cover 4,23%: down 15%, under the 20%
    assert cover_thinning(year(130, 260, 10))["flag"] is False  # cost of sales up too: 186 days, up 8%, not 20%


def test_cover_thinning_needs_its_figures_material_inventory_and_no_property():
    assert cover_thinning(year(100, 260, 10, assets=10000))["flag"] is False  # net 2,5% of assets
    assert cover_thinning(year(100, 260, 10), property=True)["flag"] is False
    qs = year(100, 260, 10)
    del qs["2025-Q3"]["inventory_provision"]
    assert cover_thinning(qs)["flag"] is None and cover_thinning({})["quarter"] is None


def test_each_year_shows_its_provision_change_and_the_part_q4_carried_from_the_audited_year():
    """Dự phòng chốt khi kiểm toán cuối năm (owner, 23/11/2026): shown, not flagged (Q4 carries 80% or more in 40% of years)."""
    from investment_agent.domain.balance_watch import year_end_provision
    prov = lambda v: {"inventory_provision": str(-v * B)}  # noqa: E731
    years = {"2024": prov(504), "2025": prov(682)}
    quarters = {"2025-Q3": prov(530), "2025-Q4": prov(682)}
    v = year_end_provision(quarters, years, **SEEN)
    assert v["rows"] == [{"year": "2025", "change": "178000000000", "q4_change": "152000000000", "q4_share": "0.8539",
                          "q4_balance": "682000000000", "year_balance": "682000000000", "updated_on": "2026-04-01", "gap": False,
                          "spike": False}]
    assert v["flag"] is False and v["year"] == "2025"


# The year updated by the source after Q4 first showed (owner, 23/11/2026: VNDirect's year first carries the company's own Q4 figures)
SEEN = {"years_modified": {"2025": "2026-04-01"}, "quarters_created": {"2025-Q4": "2026-01-30"}}


def test_a_q4_balance_the_audit_changed_is_flagged_from_1_ty_and_1_percent():
    from investment_agent.domain.balance_watch import year_end_provision
    prov = lambda v: {"inventory_provision": str(-v * B)}  # noqa: E731
    v = year_end_provision({"2025-Q3": prov(530), "2025-Q4": prov(600)}, {"2024": prov(504), "2025": prov(682)}, **SEEN)
    assert v["flag"] is True and v["rows"][-1]["gap"] is True  # self-prepared 600, the year as updated 682: 82 tỷ added
    assert year_end_provision({"2025-Q4": prov(681.5)}, {"2025": prov(682)}, **SEEN)["flag"] is False  # 0,5 tỷ: under 1 tỷ
    assert year_end_provision({"2025-Q4": prov(1000)}, {"2025": prov(1005)}, **SEEN)["flag"] is False  # 5 tỷ but 0,5%: under 1%
    small = year_end_provision({"2025-Q3": prov(10), "2025-Q4": prov(10.5)}, {"2024": prov(10), "2025": prov(10.5)}, **SEEN)
    assert small["rows"][-1]["q4_share"] is None  # a change under 1 tỷ: no share worth stating
    assert year_end_provision({}, {})["flag"] is None and year_end_provision({"2025-Q4": prov(1)}, {})["rows"] == []


def test_a_year_not_updated_after_q4_first_showed_is_not_compared():
    """Owner, 23/11/2026: between January and the audit the year is the company's own Q4; no gap can be read, and none is guessed."""
    from investment_agent.domain.balance_watch import year_end_provision
    prov = lambda v: {"inventory_provision": str(-v * B)}  # noqa: E731
    same_day = {"years_modified": {"2025": "2026-01-30"}, "quarters_created": {"2025-Q4": "2026-01-30"}}
    for seen in (same_day, {}):  # updated only the day Q4 showed, or no update day kept yet
        v = year_end_provision({"2025-Q4": prov(600)}, {"2025": prov(682)}, **seen)
        assert v["rows"][-1]["gap"] is None and v["flag"] is None


def test_a_balance_that_jumps_and_comes_back_is_marked_as_a_possible_source_error():
    """VCG (public figures, 23/11/2026): the year 2025 and Q1/2026 at 405,8 tỷ between quarters of about 35 tỷ; shown, and marked."""
    from investment_agent.domain.balance_watch import inventory_view, year_end_provision
    prov = lambda v: {"inventory_provision": str(-v * B), "inventory_gross": str(1000 * B)}  # noqa: E731
    quarters = {"2025-Q3": prov(34.2), "2025-Q4": prov(35.5), "2026-Q1": prov(405.8), "2026-Q2": prov(34.6), "2026-Q3": prov(34.6)}
    rows = {r["quarter"]: r for r in inventory_view(quarters)["rows"]}
    assert rows["2026-Q1"]["spike"] is True and rows["2025-Q4"]["spike"] is False and rows["2026-Q3"]["spike"] is False  # no quarter after
    v = year_end_provision(quarters, {"2024": prov(34.2), "2025": prov(405.8)},
                           years_modified={"2025": "2026-07-31"}, quarters_created={"2025-Q4": "2026-01-30"})
    assert v["rows"][-1]["spike"] is True and v["rows"][-1]["gap"] is True  # still compared and shown: the owner checks the report


def test_an_output_price_down_10_percent_on_a_year_while_the_share_provided_for_did_not_rise_is_flagged():
    """Giá đầu ra giảm nhưng dự phòng không đổi (owner, 23/11/2026): the price at the quarter's end against a year before, from the series
    the value chain ties to the ticker."""
    from datetime import date
    from decimal import Decimal

    from investment_agent.domain.balance_watch import price_check
    quarters = {"2025-Q3": q(10, 200, 10), "2026-Q3": q(10, 260, 10)}  # cover 5% → 3,85%
    points = [(date(2025, 9, 1), Decimal("400")), (date(2026, 9, 1), Decimal("340"))]  # −15%
    v = price_check(quarters, points, indicator="com_urea", label="Giá urê thế giới")
    assert (v["quarter"], v["price"], v["price_year_ago"], v["change"], v["coverage"], v["coverage_year_ago"], v["flag"], v["why_not"]) == (
        "2026-Q3", "340", "400", "-0.1500", "0.0385", "0.0500", True, None)
    assert price_check(quarters, [(date(2025, 9, 1), Decimal("400")), (date(2026, 9, 1), Decimal("370"))], indicator="com_urea", label="x")["flag"] is False  # −7,5%
    risen = {"2025-Q3": q(10, 200, 10), "2026-Q3": q(10, 200, 20)}  # cover 5% → 10%: provided for
    assert price_check(risen, points, indicator="com_urea", label="x")["flag"] is False


def test_a_price_series_too_short_or_stale_says_so_and_raises_nothing():
    from datetime import date
    from decimal import Decimal

    from investment_agent.domain.balance_watch import price_check
    quarters = {"2025-Q3": q(10, 200, 10), "2026-Q3": q(10, 260, 10)}
    short = price_check(quarters, [(date(2026, 9, 25), Decimal("3300"))], indicator="com_steel_hrc", label="HRC")
    assert short["flag"] is None and short["why_not"] == "Chưa đủ lịch sử giá: cần giá của cả cuối quý này và cùng kỳ năm trước."
    stale = price_check(quarters, [(date(2025, 5, 1), Decimal("400")), (date(2026, 9, 1), Decimal("340"))], indicator="com_urea", label="x")
    assert stale["flag"] is None  # the year-before price is 153 days before 30/09/2025: more than 75 days, not used
    assert price_check(quarters, [], indicator="com_urea", label="x", property=True)["flag"] is False
