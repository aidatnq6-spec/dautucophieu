from decimal import Decimal

from investment_agent.valuation.forward import Assumptions, forward_valuation

BASE = {"year": "2025", "profit": Decimal(1000), "equity": Decimal(10000), "shares": Decimal(100), "price": Decimal(120)}
BANDS = {"pe": {"median": "12.00", "sd": "2.00"}, "pb": {"median": "1.50", "sd": "0.60"}}


def test_profit_and_equity_growth_give_forward_eps_bvps_and_prices_at_each_band():
    a = Assumptions(profit_growth=["0.10", "0.20"], equity_growth=["0.15", "0.15"], dilution=["0", "0.10"])
    out = forward_valuation(BASE, BANDS, a)
    y1, y2 = out["years"]
    assert y1["year"] == "2026" and y1["eps"] == "11.00" and y1["bvps"] == "115.00"  # 1.100 / 100, 11.500 / 100
    assert y2["year"] == "2027" and y2["eps"] == "12.00" and y2["bvps"] == "120.23"  # 1.320 / 110, 13.225 / 110
    pe = {b["k"]: b for b in y1["pe"]}
    assert pe[0] == {"k": 0, "multiple": "12.00", "price": "132.00", "gap": "0.1000"}
    assert pe[1]["price"] == "154.00" and pe[-3]["price"] == "66.00"  # 14× and 6×
    pb = {b["k"]: b for b in y1["pb"]}
    assert pb[-3] == {"k": -3, "multiple": None, "price": None, "gap": None}  # 1,5 − 3×0,6 < 0: not applicable
    assert out["base"] == {"year": "2025", "eps": "10.00", "bvps": "100.00", "price": "120"}


def test_a_custom_multiple_prices_each_year_and_missing_base_or_bands_give_reasons():
    a = Assumptions(profit_growth=["0.10"], equity_growth=["0.10"], dilution=["0"])
    out = forward_valuation(BASE, BANDS, a, custom={"pe": "8", "pb": None})
    assert out["years"][0]["custom"] == {"pe": "88.00", "pb": None}
    assert forward_valuation({**BASE, "profit": None}, BANDS, a)["reason"] == "Chưa có lợi nhuận công ty mẹ năm gần nhất"
    no_pe = forward_valuation(BASE, {"pe": {"median": None, "sd": None}, "pb": BANDS["pb"]}, a)
    assert no_pe["years"][0]["pe"] == [] and no_pe["notes"] == ["Chưa đủ lịch sử P/E theo tháng để tính các mức"]
    assert forward_valuation({**BASE, "profit": Decimal(-5)}, BANDS, a)["years"][0]["pe"] == []  # a loss: no P/E price


def test_assumptions_are_bounded():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Assumptions(profit_growth=["5"], equity_growth=["0"], dilution=["0"])  # +500%
    with pytest.raises(ValidationError):
        Assumptions(profit_growth=["0.1", "0.1", "0.1", "0.1"], equity_growth=["0"] * 4, dilution=["0"] * 4)  # four years
    with pytest.raises(ValidationError):
        Assumptions(profit_growth=["0.1", "0.1"], equity_growth=["0.1"], dilution=["0", "0"])  # lengths differ
