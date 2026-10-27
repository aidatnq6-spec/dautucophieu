from decimal import Decimal

from investment_agent.domain.asset_pyramid import asset_pyramid

M = Decimal(1_000_000)


def layers(**amounts):
    base = {"reserve": 100, "deposit": 0, "bond": 0, "gold": 0, "stocks": 0, "crypto": 0}
    return {k: Decimal(v) * M for k, v in {**base, **amounts}.items()}


def by_id(p):
    return {l["id"]: l for l in p["layers"]}


def test_targets_follow_the_risk_group_and_the_video_rules():
    p = asset_pyramid(layers(deposit=200, gold=100, stocks=600, crypto=50, bond=50), deductions=Decimal(100) * M, stock_ratio=Decimal("0.60"))
    assert p["total"] == "1100000000" and p["base"] == "1000000000"
    t = {i: (l["target_min"], l["target_max"]) for i, l in by_id(p).items()}
    assert t == {"reserve": (None, None), "deposit": ("0.10", "0.30"), "bond": ("0", "0.10"), "gold": ("0.10", "0.15"),
                 "stocks": ("0.55", "0.60"), "crypto": ("0", "0.05")}
    assert [l["id"] for l in p["layers"]] == ["reserve", "deposit", "bond", "gold", "stocks", "crypto"]  # bottom to top
    assert {i: l["status"] for i, l in by_id(p).items()} == {"reserve": "fixed", "deposit": "ok", "bond": "ok", "gold": "ok", "stocks": "ok",
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
