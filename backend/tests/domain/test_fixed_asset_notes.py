from datetime import date

import pytest

from investment_agent.domain.fixed_asset_notes import NoteError, complete, due_view, postpone, validate_notes

B = 10**9


def project(**more):
    return {"name": " Dung Quất 2 ", "due": "Q3/2025", "read_period": "2024", "cip_value": "60.000", "budget": "85000",
            "source_url": "https://example.com/bctc.pdf", "note": "lò cao số 5", **more}


def test_a_project_keeps_its_due_quarter_figures_and_starts_open():
    projects, ranges = validate_notes([project()], {"machinery": {"from": "1", "to": "25"}, "period": "2021"}, stored=[])
    p = projects[0]
    assert {k: p[k] for k in ("name", "due", "read_period", "cip_value", "budget", "status", "done_on", "postpones")} == {
        "name": "Dung Quất 2", "due": "2025-Q3", "read_period": "2024", "cip_value": "60000", "budget": "85000", "status": "open", "done_on": None,
        "postpones": []}
    assert len(p["id"]) == 12
    assert ranges == {"period": "2021", "groups": {"machinery": {"from": 1, "to": 25}}}


def test_bad_notes_are_refused_with_a_reason():
    for raw, ranges, code in (([project(name="")], {}, "invalid_name"), ([project(due="")], {}, "invalid_quarter"), ([project(due="Q5/2025")], {}, "invalid_quarter"),
                              ([project(read_period="2025-13")], {}, "invalid_period"), ([project(budget="-1")], {}, "invalid_amount"),
                              ([project(source_url="ftp://x")], {}, "invalid_source"), ([project() for _ in range(21)], {}, "too_many"),
                              ([], {"machinery": {"from": "30", "to": "5"}}, "invalid_range"), ([], {"buildings": {"from": "1", "to": "101"}}, "invalid_range"),
                              ([], {"spaceships": {"from": "1", "to": "2"}}, "invalid_group")):
        with pytest.raises(NoteError) as err:
            validate_notes(raw, ranges, stored=[])
        assert err.value.code == code


def test_the_due_quarter_changes_only_through_a_postponement_and_status_stays_as_stored():
    stored, _ = validate_notes([project()], {}, stored=[])
    pid = stored[0]["id"]
    with pytest.raises(NoteError) as err:
        validate_notes([project(id=pid, due="Q4/2025")], {}, stored=stored)
    assert err.value.code == "due_locked"
    kept, _ = validate_notes([project(id=pid, name="DQ2", status="done", postpones=[{"x": 1}])], {}, stored=stored)  # status and history from the store
    assert kept[0]["name"] == "DQ2" and kept[0]["status"] == "open" and kept[0]["postpones"] == []
    later = postpone(stored, pid, "Q2/2026", " chậm lắp đặt ", today=date(2025, 11, 1))
    assert later[0]["due"] == "2026-Q2" and later[0]["postpones"] == [{"from": "2025-Q3", "to": "2026-Q2", "on": "2025-11-01", "reason": "chậm lắp đặt"}]
    for to, code in (("Q3/2025", "not_later"), ("Q1/2025", "not_later"), ("x", "invalid_quarter")):
        with pytest.raises(NoteError) as err:
            postpone(stored, pid, to, "", today=date(2025, 11, 1))
        assert err.value.code == code
    done = complete(later, pid, today=date(2026, 8, 1))
    assert done[0]["status"] == "done" and done[0]["done_on"] == "2026-08-01"
    with pytest.raises(NoteError) as err:
        postpone(done, pid, "Q4/2026", "", today=date(2026, 8, 2))
    assert err.value.code == "not_open"
    with pytest.raises(NoteError) as err:
        complete(stored, "nope", today=date(2026, 8, 1))
    assert err.value.code == "not_found"


def test_an_open_project_is_due_once_its_quarter_s_report_is_stored_with_the_company_s_figures():
    projects, _ = validate_notes([project(), project(name="Nhà máy B", due="Q1/2026", read_period="")], {}, stored=[])
    statements = {"years": {"2024": {"cip": str(63656 * B), "ppe_gross": str(108147 * B)}},
                  "quarters": {"2025-Q3": {"cip": str(15000 * B), "ppe_gross": str(170000 * B)}, "2025-Q4": {"cip": str(10721 * B), "ppe_gross": str(182309 * B)}}}
    view = due_view(projects, statements, today=date(2026, 4, 20))
    a, b = view
    assert a["state"] == "due" and a["at_read"] == {"period": "2024", "cip": str(63656 * B), "ppe_gross": str(108147 * B)}
    assert a["at_due"] == {"period": "2025-Q3", "cip": str(15000 * B), "ppe_gross": str(170000 * B)}
    assert a["latest"] == {"period": "2025-Q4", "cip": str(10721 * B), "ppe_gross": str(182309 * B)}
    assert b["state"] == "waiting_report" and b["at_due"] is None and b["at_read"] is None  # Q1/2026 over, its report not stored yet
    assert due_view(projects, {"years": statements["years"]}, today=date(2025, 8, 1))[0]["state"] == "upcoming"  # Q3/2025 not over
    assert due_view(complete(projects, a["id"], today=date(2026, 4, 21)), statements, today=date(2026, 4, 21))[0]["state"] == "done"
