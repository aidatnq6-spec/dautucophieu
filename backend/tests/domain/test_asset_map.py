from datetime import date

from investment_agent.domain.asset_map import asset_map
from investment_agent.domain.deposit_book import DepositBook

BOOK = DepositBook.model_validate({
    "accounts": [{"id": "a", "name": "Tài khoản A", "amount": "5000000", "liquid": True}],
    "deposits": [{"id": "d", "bank": "Ngân hàng A", "matures": "2027-02-05", "principal": "200000000", "rate": "6", "interest": None,
                  "payout": "end", "locked": False}],
    "bonds": [{"id": "f", "name": "Quỹ B", "amount": "900000", "fund": "VFF", "units": "50"}, {"id": "x", "name": "Quỹ mất NAV", "amount": "300000",
                                                                                              "fund": "GONE", "units": "1"}],
    "gold": [{"id": "g", "name": "Nhẫn", "amount": "8000000", "kind": "Nhẫn tròn", "chi": "1"}], "crypto": []})
HOLDINGS = [{"security_id": "FPT", "market_value": "6000000", "total_cost": "5000000"},
            {"security_id": "VCB", "market_value": None, "total_cost": "3000000"}]


def test_every_asset_is_a_tile_in_its_layer_with_its_gain_on_cost_where_a_price_gives_one():
    out = asset_map(HOLDINGS, ledger_cash="1000000", book=BOOK, navs={"VFF": {"name": "Quỹ trái phiếu B", "nav": "20000", "date": "2026-11-13"}},
                    profiles={"VFF": {"kind": "BOND"}}, gold={"kinds": {"Nhẫn tròn": {"buy": "9000000"}}, "as_of": "2026-11-14T08:00:00"},
                    sectors={"FPT": "Công nghệ Thông tin"}, today=date(2026, 11, 14))
    groups = {g["id"]: g for g in out["groups"]}
    assert [g["id"] for g in out["groups"]] == ["deposits", "gold", "stocks", "cash", "funds"]  # largest first
    assert groups["stocks"]["tiles"] == [{"id": "stock:FPT", "label": "FPT", "note": "Công nghệ Thông tin", "value": "6000000", "change": "0.2"}]
    assert groups["funds"]["tiles"] == [{"id": "bond:f", "label": "VFF", "note": "Trái phiếu", "value": "1000000", "change": "0.1111"},
                                        {"id": "bond:x", "label": "GONE", "note": "chưa có NAV, theo vốn", "value": "300000", "change": None}]
    assert groups["gold"]["tiles"][0]["value"] == "9000000" and groups["gold"]["tiles"][0]["change"] == "0.125"
    assert groups["cash"]["value"] == "6000000" and groups["deposits"]["tiles"][0]["change"] is None
    assert out["total"] == str(200000000 + 9000000 + 6000000 + 6000000 + 1300000) and out["unpriced"] == ["VCB"]



def test_term_deposits_are_one_tile_per_bank():
    book = DepositBook.model_validate({"accounts": [], "bonds": [], "gold": [], "crypto": [], "deposits": [
        {"id": f"d{i}", "bank": "NCB" if i < 3 else "SHB", "matures": f"2027-0{i + 1}-05", "principal": "50000000", "rate": "6", "interest": None,
         "payout": "end", "locked": False} for i in range(4)]})
    out = asset_map([], ledger_cash="0", book=book, navs={}, profiles={}, gold={}, sectors={}, today=date(2026, 11, 14))
    tiles = {t["label"]: t for t in out["groups"][0]["tiles"]}
    assert tiles["NCB"] == {"id": "bank:NCB", "label": "NCB", "note": "3 sổ · sớm nhất đến hạn 05/01/2027", "value": "150000000", "change": None}
    assert tiles["SHB"]["note"] == "đến hạn 05/04/2027"
