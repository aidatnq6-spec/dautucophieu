from datetime import datetime, timedelta
from decimal import Decimal

from investment_agent.domain.stress import stress_inputs

D = Decimal


def test_each_holding_gets_its_value_beta_and_only_clear_factor_relations():
    sens = {"FPT": {"status": "ok", "oil": {"beta": "-0.150", "t": "-2.5", "class": "hurt"}, "usd": {"beta": "0.050", "t": "0.8", "class": "unclear"}},
            "HPG": {"status": "insufficient", "weeks": 20}}
    out = stress_inputs(shares={"FPT": 100, "HPG": 200, "VCB": 10}, costs={"FPT": D("50000"), "HPG": D("25000"), "VCB": D("90000")},
                        prices={"FPT": D("60000"), "HPG": D("20000"), "VCB": None}, betas={"FPT": {"beta": "1.2", "date": "2026-10-30"}},
                        sensitivity=sens, index=[], answer10=None, threshold=D("0.3"))
    fpt, hpg, vcb = out["rows"]
    assert fpt == {"symbol": "FPT", "shares": 100, "price": "60000", "value": "6000000", "cost": "50000", "beta": "1.2",
                   "oil": "-0.150", "usd": None, "oil_note": None, "usd_note": "Quan hệ không rõ (|t| < 2)"}
    assert hpg["beta"] is None and hpg["oil"] is None and hpg["oil_note"] == "Chưa đủ dữ liệu để đo"
    assert vcb["value"] is None and vcb["price"] is None
    assert out["tolerance"] is None and out["worst"] is None and out["threshold"] == "0.3"


def test_the_owners_own_loss_tolerance_and_the_deepest_past_fall_of_vn_index():
    index = [(datetime(2020, 1, 1) + timedelta(days=i), v) for i, v in enumerate([1000, 1200, 600, 900])]
    out = stress_inputs(shares={}, costs={}, prices={}, betas={}, sensitivity={}, index=index, answer10="B", threshold=D("0.3"))
    assert out["tolerance"] == {"answer": "B", "limit": "0.10", "label": "Trên 5 đến 10 triệu trên 100 triệu"}
    assert out["worst"] == {"depth": "-0.5000", "peak": "2020-01-02", "trough": "2020-01-03"}
    assert [p["id"] for p in out["presets"]] == ["vn10", "vn20", "worst", "oil30", "usd5"]
    assert out["presets"][2] == {"id": "worst", "label": "Lặp lại đợt giảm sâu nhất của VN-Index (−50,0%, 02/01/2020 → 03/01/2020)",
                                 "market": "-0.5000", "oil": "0", "usd": "0"}
    assert stress_inputs(shares={}, costs={}, prices={}, betas={}, sensitivity={}, index=[], answer10="D", threshold=D("0.3"))["tolerance"]["limit"] is None


def test_no_deepest_fall_preset_when_the_stored_index_never_fell():
    rising = [(datetime(2020, 1, 1) + timedelta(days=i), 1000 + i) for i in range(5)]
    out = stress_inputs(shares={}, costs={}, prices={}, betas={}, sensitivity={}, index=rising, answer10=None, threshold=D("0.3"))
    assert out["worst"] is None and "worst" not in [p["id"] for p in out["presets"]]
