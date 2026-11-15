import pytest

from investment_agent.domain.related_receivables import RelatedError, review, validate_year


def row(name, amount, grouped=False, related=True, secured=None, interest=None, collect_within=None):
    return {"name": name, "amount": amount, "grouped": grouped, "related": related, "secured": secured, "interest": interest,
            "collect_within": collect_within}


# In the shape of the VJC case in the owner's notes (11/2026); the figures here are made up.
YEARS = {
    "2019": {"source": "BCTC hợp nhất 2019, thuyết minh 7", "rows": [
        row("Công ty Alpha", "2820", secured=False, interest=False, collect_within="6–12 tháng"),
        row("Công ty Lữ hành Beta", "1309", related=False),
        row("Công ty Gamma", "500", collect_within="12 tháng")]},
    "2020": {"source": "BCTC hợp nhất 2020, thuyết minh 5 và 38", "rows": [
        row("Bên liên quan khác", "2953", grouped=True),
        row("Công ty liên kết", "2043", grouped=True),
        row("  công ty gamma ", "400", secured=False, interest=False)]},
}


def test_a_named_party_dropped_the_next_year_is_found_with_the_group_that_may_hold_it():
    found = review(YEARS)["findings"]
    gone = [f for f in found if f["kind"] == "vanished"]
    assert gone == [{"kind": "vanished", "year": "2020", "from_year": "2019", "name": "Công ty Alpha", "amount": "2820",
                     "group": {"name": "Bên liên quan khác", "amount": "2953"}}]  # the largest related group at least half its size


def test_a_balance_promised_within_a_term_and_still_half_there_is_not_collected():
    found = [f for f in review(YEARS)["findings"] if f["kind"] == "not_collected"]
    assert found == [{"kind": "not_collected", "year": "2020", "name": "Công ty Gamma", "before": "500", "now": "400", "promised": "12 tháng"}]


def test_unsecured_interest_free_related_balances_of_the_latest_year_are_named():
    found = [f for f in review(YEARS)["findings"] if f["kind"] == "unsecured_free"]
    assert found == [{"kind": "unsecured_free", "year": "2020", "name": "  công ty gamma ".strip(), "amount": "400"}]


def test_each_year_adds_its_related_balances_and_the_named_part():
    years = {y["year"]: y for y in review(YEARS)["years"]}
    assert (years["2019"]["related_total"], years["2019"]["named_related"]) == ("3320", "3320")  # the travel agent is a third party
    assert (years["2020"]["related_total"], years["2020"]["named_related"]) == ("5396", "400")
    assert [y["year"] for y in review(YEARS)["years"]] == ["2020", "2019"]  # newest first


@pytest.mark.parametrize("source, rows, code", [
    ("", [row("A", "1")], "invalid_source"),
    ("BCTC 2020", [], "no_rows"),
    ("BCTC 2020", [row("", "1")], "invalid_row"),
    ("BCTC 2020", [row("A", "-1")], "invalid_row"),
    ("BCTC 2020", [row("A", "abc")], "invalid_row"),
    ("BCTC 2020", [row("A", "1"), row(" a ", "2")], "duplicate_name"),
])
def test_a_year_needs_its_source_and_named_rows_with_amounts(source, rows, code):
    with pytest.raises(RelatedError) as exc:
        validate_year(source, rows)
    assert exc.value.code == code


def test_a_valid_year_is_kept_with_names_trimmed_and_amounts_as_typed():
    year = validate_year(" BCTC 2020 ", [row(" Công ty A ", "1.234,5")])
    assert year == {"source": "BCTC 2020", "rows": [row("Công ty A", "1234.5")]}
