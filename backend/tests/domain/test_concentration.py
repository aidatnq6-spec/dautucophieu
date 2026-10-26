from decimal import Decimal

from investment_agent.domain.concentration import concentration, simulate

HOLDINGS = [{"security_id": "KDH", "market_value": "248581750"}, {"security_id": "SSI", "market_value": "244728000"},
            {"security_id": "HPG", "market_value": "88051700"}, {"security_id": "MBB", "market_value": "1955000"},
            {"security_id": "XYZ", "market_value": None}]  # no price yet
SECTORS = {"KDH": "Bất động sản", "SSI": "Dịch vụ tài chính", "HPG": "Tài nguyên Cơ bản", "MBB": "Ngân hàng"}


def test_weights_on_investable_capital_flag_tickers_and_sectors_over_the_limit():
    out = concentration(HOLDINGS, capital="880000000", sectors=SECTORS, limit=Decimal("0.25"))
    by = {t["symbol"]: t for t in out["tickers"]}
    assert by["KDH"]["weight"] == "0.2825" and by["KDH"]["over"] is True
    assert by["SSI"]["weight"] == "0.2781" and by["SSI"]["over"] is True
    assert by["HPG"]["over"] is False and by["MBB"]["weight"] == "0.0022"
    assert by["XYZ"]["weight"] is None and by["XYZ"]["over"] is False  # no price: not guessed
    assert [t["symbol"] for t in out["tickers"]][:2] == ["KDH", "SSI"]  # largest first
    sectors = {s["sector"]: s for s in out["sectors"]}
    assert sectors["Bất động sản"]["over"] is True and sectors["Ngân hàng"]["symbols"] == ["MBB"]
    assert out["cash"] == {"value": "296683550", "weight": "0.3371"}
    assert out["limit"] == "0.25" and out["capital"] == "880000000" and out["missing_prices"] == ["XYZ"]


def test_unknown_sector_is_grouped_as_unclassified():
    out = concentration([{"security_id": "AAA", "market_value": "100"}], capital="1000", sectors={}, limit=Decimal("0.25"))
    assert out["sectors"][0]["sector"] == "Chưa phân ngành"


def test_simulation_moves_money_between_cash_and_a_ticker():
    base = concentration(HOLDINGS, capital="880000000", sectors=SECTORS, limit=Decimal("0.25"))
    after = simulate(base, symbol="KDH", amount=Decimal("-50000000"), sector="Bất động sản")
    kdh = next(t for t in after["tickers"] if t["symbol"] == "KDH")
    assert kdh["weight"] == "0.2257" and kdh["over"] is False
    assert after["cash"]["value"] == "346683550"
    bought = simulate(base, symbol="FPT", amount=Decimal("100000000"), sector="Công nghệ Thông tin")
    assert next(t for t in bought["tickers"] if t["symbol"] == "FPT")["weight"] == "0.1136"
    assert any(s["sector"] == "Công nghệ Thông tin" for s in bought["sectors"])


def test_no_investable_capital_means_no_weights():
    out = concentration(HOLDINGS, capital=None, sectors=SECTORS, limit=Decimal("0.25"))
    assert out["status"] == "no_capital" and out["tickers"] == []
