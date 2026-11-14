from datetime import date
from decimal import Decimal

from investment_agent.domain.deposit_book import Bond
from investment_agent.domain.fund_board import composition, fund_board, index_returns

NAVS = {"DCDS": {"name": "Quỹ cổ phiếu A", "nav": "100", "date": "2026-11-13"}, "VFF": {"name": "Quỹ trái phiếu B", "nav": "20", "date": "2026-11-13"},
        "VIBF": {"name": "Quỹ cân bằng C", "nav": "10", "date": "2026-11-12"}, "NEW": {"name": "Quỹ mới", "nav": "10", "date": "2026-11-13"}}


def profile(kind, m12, ytd="1"):
    return {"kind": kind, "manager": "M", "fee": "1.5", "returns": {"ytd": ytd, "m1": None, "m3": None, "m6": None, "m12": m12, "m36": None, "m60": None,
                                                                   "annual36": None}}


PROFILES = {"DCDS": profile("STOCK", "-9.64"), "VFF": profile("BOND", "6.1"), "VIBF": profile("BALANCED", "2"), "NEW": profile("STOCK", None)}
INDEX = [("2024-11-13T00:00:00", "1200"), ("2025-11-12T00:00:00", "1500"), ("2025-11-13T00:00:00", "1600"), ("2025-12-31T00:00:00", "1800"),
         ("2026-11-13T00:00:00", "1734.93")]


def test_index_returns_over_the_same_periods_and_blank_where_the_history_is_short():
    out = index_returns(INDEX)
    assert out["as_of"] == "2026-11-13"
    assert out["ytd"] == "-3.62" and out["m12"] == "8.43" and out["m36"] is None and out["m60"] is None


def test_the_board_groups_funds_by_kind_best_year_first_and_marks_the_owners():
    out = fund_board(NAVS, PROFILES, index=INDEX, deposit_rate="5.8", held={"VFF"})
    assert [f["code"] for f in out["funds"]] == ["DCDS", "NEW", "VIBF", "VFF"]  # STOCK, BALANCED, BOND
    stock = [f["code"] for f in out["funds"] if f["kind"] == "STOCK"]
    assert stock == ["DCDS", "NEW"]  # a blank 12-month return goes last, not as zero
    vff = next(f for f in out["funds"] if f["code"] == "VFF")
    assert vff == {"code": "VFF", "name": "Quỹ trái phiếu B", "kind": "BOND", "manager": "M", "fee": "1.5", "nav": "20", "date": "2026-11-13",
                   "returns": PROFILES["VFF"]["returns"], "held": True, "beats_deposit": True}
    assert next(f for f in out["funds"] if f["code"] == "DCDS")["beats_deposit"] is False
    assert next(f for f in out["funds"] if f["code"] == "NEW")["beats_deposit"] is None
    assert out["counts"] == {"STOCK": 2, "BALANCED": 1, "BOND": 1}
    assert out["benchmark"]["deposit_12m"] == "5.8" and out["benchmark"]["vnindex"]["m12"] == "8.43"


def test_a_fund_without_its_profile_yet_has_no_kind():
    out = fund_board({"X": NAVS["VFF"]}, {}, index=[], deposit_rate=None, held=set())
    assert out["funds"][0]["kind"] is None and out["funds"][0]["returns"] is None and out["benchmark"]["vnindex"]["ytd"] is None


def bond(id, fund=None, units=None, amount=1000):
    return Bond.model_validate({"id": id, "name": "x", "amount": str(amount), "fund": fund, "units": str(units) if units else None})


def test_composition_splits_the_owners_funds_by_kind_at_their_nav():
    out = composition([bond("a", "DCDS", 30), bond("b", "VFF", 50), bond("c", "VFF", 50), bond("d"), bond("e", "GONE", 1, amount=500)], NAVS, PROFILES)
    groups = {g["kind"]: g for g in out["groups"]}
    assert groups["STOCK"] == {"kind": "STOCK", "value": "3000", "share": "0.5455", "funds": ["DCDS"]}
    assert groups["BOND"] == {"kind": "BOND", "value": "2000", "share": "0.3636", "funds": ["VFF"]}
    assert groups["unknown"] == {"kind": "unknown", "value": "500", "share": "0.0909", "funds": ["GONE"]}  # no NAV: at cost, kind unknown
    assert "BALANCED" not in groups and out["total"] == "5500"  # a row without a fund code is not a fund
    assert out["fund_count"] == 3 and out["at_cost"] == ["GONE"]
    assert out["notes"] == []


def test_composition_notes_too_few_funds_and_a_single_kind():
    out = composition([bond("a", "VFF", 10)], NAVS, PROFILES)
    assert out["notes"] == ["fewer_than_3", "single_kind"] and out["groups"][0]["share"] == "1"
    assert composition([], NAVS, PROFILES) == {"groups": [], "total": "0", "fund_count": 0, "at_cost": [], "notes": []}


def test_a_period_starting_on_a_close_in_another_unit_stays_blank():
    # The stored series before 10/2022 is in thousand points rounded to 0.01 (1.47 for about 1,470): not rescaled, left out.
    out = index_returns([("2021-11-12T00:00:00", "1.47"), ("2023-11-13T00:00:00", "1100"), ("2026-11-13T00:00:00", "1734.93")])
    assert out["m60"] is None and out["m36"] == "57.72"
