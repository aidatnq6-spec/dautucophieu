from decimal import Decimal

from investment_agent.domain.asset_pyramid import asset_pyramid

M = Decimal(1_000_000)


def layers(**amounts):
    base = {"reserve": 100, "cash": 0, "deposit": 0, "bond": 0, "gold": 0, "stocks": 0, "crypto": 0}
    return {k: Decimal(v) * M for k, v in {**base, **amounts}.items()}


def by_id(p):
    return {l["id"]: l for l in p["layers"]}


def test_targets_follow_the_risk_group_and_the_video_rules():
    p = asset_pyramid(layers(deposit=200, gold=100, stocks=600, crypto=50, bond=50), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    assert p["total"] == "1100000000" and p["base"] == "1000000000"
    t = {i: (l["target_min"], l["target_max"]) for i, l in by_id(p).items()}
    assert t == {"reserve": (None, None), "cash": (None, None), "deposit": ("0.10", "0.30"), "bond": ("0", "0.10"), "gold": ("0.10", "0.15"),
                 "stocks": ("0.55", "0.60"), "crypto": ("0", "0.05")}
    assert [l["id"] for l in p["layers"]] == ["reserve", "cash", "deposit", "bond", "gold", "stocks", "crypto"]  # bottom to top
    assert {i: l["status"] for i, l in by_id(p).items()} == {"reserve": "fixed", "cash": "with_deposit", "deposit": "ok", "bond": "ok", "gold": "ok", "stocks": "ok",
                                                              "crypto": "ok"}
    assert p["warnings"] == []


def test_a_short_layer_below_an_over_layer_is_flagged_build_from_the_bottom():
    p = asset_pyramid(layers(deposit=50, gold=50, stocks=850, crypto=50), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    l = by_id(p)
    assert l["deposit"]["status"] == "short" and l["deposit"]["gap"] == "50000000"   # 5% of 1 tỷ vs at least 10%
    assert l["gold"]["status"] == "short" and l["gold"]["gap"] == "50000000"
    assert l["stocks"]["status"] == "over" and l["stocks"]["gap"] == "250000000"     # 85% vs at most 60%
    assert p["warnings"] == [{"short": "deposit", "over": ["stocks"]}, {"short": "gold", "over": ["stocks"]}]


def test_a_cautious_group_leaves_more_room_for_deposits():
    p = asset_pyramid(layers(deposit=750, gold=100, stocks=100, crypto=0, bond=50), deductions=Decimal(100) * M, stock_ratio=Decimal("0.10"))
    assert (by_id(p)["deposit"]["target_min"], by_id(p)["deposit"]["target_max"]) == ("0.60", "0.80")
    assert by_id(p)["stocks"]["target_min"] == "0.05" and p["warnings"] == []


def test_nothing_left_after_the_reserve_has_no_shares():
    p = asset_pyramid(layers(reserve=100), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    assert p["base"] == "0" and all(l["share"] is None for l in p["layers"] if l["id"] != "reserve")


def test_cash_is_its_own_row_but_shares_the_deposit_target():
    p = asset_pyramid(layers(cash=60, deposit=40, gold=150, stocks=600, bond=100, crypto=50), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    l = by_id(p)
    assert l["cash"]["amount"] == "60000000" and l["cash"]["share"] == "0.0600" and l["cash"]["status"] == "with_deposit"
    assert l["deposit"]["amount"] == "40000000" and l["deposit"]["share"] == "0.1000" and l["deposit"]["status"] == "ok"  # 4% + 6% cash
    assert l["deposit"]["with_cash"] is True



def test_funding_for_more_stocks_fills_short_layers_first_then_goes_to_stocks():
    """27/10/2026, owner's rule: cash and deposits above their ceiling (and any layer above its ceiling) first fill layers below their
    minimum (here gold); only the rest is for stocks, capped by the room left in the stock target."""
    p = asset_pyramid(layers(cash=50, deposit=350, gold=50, stocks=400, bond=150), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    # base 1 000: deposit+cash 400 vs at most 300; bond 150 vs at most 100; gold 50 vs at least 100; stocks 400 vs at most 600
    f = p["funding"]
    assert f["sources"] == [{"id": "deposit", "surplus": "100000000"}, {"id": "bond", "surplus": "50000000"}, {"id": "gold", "surplus": "0"},
                            {"id": "crypto", "surplus": "0"}]
    assert f["pool"] == "150000000" and f["fills"] == [{"id": "gold", "amount": "50000000"}]
    assert f["left_for_stocks"] == "100000000" and f["stock_room"] == "200000000" and f["buyable"] == "100000000"
    assert f["from_cash"] == "50000000" and f["to_raise"] == "50000000"  # cash already in the brokerage account is used first


def test_funding_is_capped_by_the_stock_room():
    # bond 200 vs at most 100 gives 100; deposit 50 is short of its 100 minimum and takes 50; stocks are already over their target
    p = asset_pyramid(layers(deposit=50, bond=200, gold=100, stocks=650), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    f = p["funding"]
    assert f["pool"] == "100000000" and f["fills"] == [{"id": "deposit", "amount": "50000000"}] and f["left_for_stocks"] == "50000000"
    assert f["stock_room"] == "0" and f["buyable"] == "0" and f["from_cash"] == "0" and f["to_raise"] == "0"


def test_when_short_layers_take_the_whole_surplus_nothing_is_left_for_stocks():
    p = asset_pyramid(layers(deposit=320, gold=0, stocks=580, bond=100), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    f = p["funding"]
    assert f["pool"] == "20000000" and f["fills"] == [{"id": "gold", "amount": "20000000"}]  # gold is short 100, only 20 to give
    assert f["left_for_stocks"] == "0" and f["stock_room"] == "20000000" and f["buyable"] == "0"
