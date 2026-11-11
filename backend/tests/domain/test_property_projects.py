import pytest

from investment_agent.domain.property_projects import ProjectError, timeline, validate_projects


def test_a_project_keeps_its_figures_in_ty_dong_and_the_years_the_owner_expects_them():
    out = validate_projects([{"name": " New City ", "total": "7.500", "booked": "1100", "by_year": {"2026": "1500", "2027": "4900"},
                              "source_url": "https://example.com/bc.pdf", "note": ""}])
    assert out == [{"id": out[0]["id"], "name": "New City", "total": "7500", "booked": "1100", "by_year": {"2026": "1500", "2027": "4900"},
                    "source_url": "https://example.com/bc.pdf", "note": ""}]
    assert len(out[0]["id"]) == 12


def test_bad_projects_are_refused_with_a_reason():
    for raw, code in (([{"name": "", "by_year": {}}], "invalid_name"), ([{"name": "A", "total": "-1", "by_year": {}}], "invalid_amount"),
                      ([{"name": "A", "by_year": {"20x6": "1"}}], "invalid_year"), ([{"name": "A", "by_year": {"2026": "abc"}}], "invalid_amount"),
                      ([{"name": "A", "by_year": {}, "source_url": "ftp://x"}], "invalid_source"), ([{"name": str(i), "by_year": {}} for i in range(31)], "too_many")):
        with pytest.raises(ProjectError) as err:
            validate_projects(raw)
        assert err.value.code == code


def test_the_timeline_adds_up_each_year_and_says_what_is_left_unplaced():
    projects = validate_projects([{"name": "A", "total": "7500", "booked": "1100", "by_year": {"2026": "1500", "2027": "4900"}},
                                  {"name": "B", "total": None, "booked": None, "by_year": {"2027": "800", "2028": "1200"}}])
    view = timeline(projects)
    assert view["years"] == [{"year": "2026", "amount": "1500", "projects": 1}, {"year": "2027", "amount": "5700", "projects": 2},
                             {"year": "2028", "amount": "1200", "projects": 1}]
    a, b = view["projects"]
    assert a["remaining"] == "6400" and a["planned"] == "6400" and a["unplaced"] == "0"
    assert b["remaining"] is None and b["unplaced"] is None  # no total: nothing to compare against
