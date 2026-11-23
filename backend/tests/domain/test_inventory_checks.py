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
