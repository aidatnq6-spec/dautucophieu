"""Tồn kho: ba căn cứ kiểm kê và giá hàng hóa (owner, 23/11/2026; docs/superpowers/specs/2026-11-23-ton-kho-kiem-ke-design.md). Made-up figures."""

from investment_agent.domain.balance_watch import gross_loss

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
