"""One reader of a bank's public figures for the bank page and the signs board (review 23/11/2026 (3)): the shape of both stores is
checked where they are read; a file of the wrong shape makes the bank unread, never an error further on."""

import json

import pytest

from investment_agent.market.bank_notes import load_public

B = 1_000_000_000


def put(tmp_path, folder, data):
    (tmp_path / folder).mkdir(exist_ok=True)
    (tmp_path / folder / "VCB.json").write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def test_both_stores_give_the_asset_quality_quarters_and_vndirects_quarters(tmp_path):
    put(tmp_path, "bank-notes", {"symbol": "VCB", "quarters": {"2026-09-30": {**{f"group{i}": str(v * B) for i, v in enumerate((90, 4, 2, 2, 2), 1)},
                                                                              "loans": str(100 * B)}}})
    put(tmp_path, "statements-financial", {"symbol": "VCB", "quarters": {"2026-Q3": {"loan_reserve": str(-6 * B)}}, "quarters_zeros": []})
    public, statements = load_public(tmp_path, "VCB")
    assert public["2026-Q3"]["values"]["reserve"] == "6" and public["2026-Q3"]["sources"]["group1"] == "Vietcap"
    assert statements == {"2026-Q3": {"loan_reserve": str(-6 * B)}}


def test_no_store_yet_is_nothing_to_show_not_unread(tmp_path):
    assert load_public(tmp_path, "VCB") == ({}, {})


@pytest.mark.parametrize("folder, data", [
    ("bank-notes", '{"symbol": "VCB", "quart'),  # cut short
    ("bank-notes", ["2026-09-30"]),  # valid JSON, not an object
    ("bank-notes", {"symbol": "VCB", "quarters": ["2026-09-30"]}),
    ("bank-notes", {"symbol": "VCB", "quarters": {"bad": {"group1": "1"}}}),  # a key that is no quarter-end day
    ("bank-notes", {"symbol": "VCB", "quarters": {"2026-09-30": ["1"]}}),
    ("statements-financial", [1]),
    ("statements-financial", {"symbol": "VCB", "quarters": {"2026-Q3": "x"}}),
    ("statements-financial", {"symbol": "VCB", "quarters": {}, "quarters_zeros": "x"}),
])
def test_a_store_of_the_wrong_shape_makes_the_bank_unread(tmp_path, folder, data):
    put(tmp_path, folder, data)
    assert load_public(tmp_path, "VCB") is None

