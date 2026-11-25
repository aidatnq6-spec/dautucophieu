import json

from signed_client import call
from test_passive_income_route import client as base_client


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("HPG\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2, "sectors": {"HPG": "Tài nguyên Cơ bản", "VCB": "Ngân hàng"}}),
                                              encoding="utf-8")
    return base_client(tmp_path)


URL = "/internal/stock/HPG/fixed-asset-notes"


def test_notes_are_kept_per_company_and_change_their_due_quarter_only_by_postponing(tmp_path):
    c, clock = client(tmp_path)
    empty = call(c, clock, "GET", URL).json()
    assert empty["symbol"] == "HPG" and empty["version"] == 0 and empty["projects"] == [] and empty["ranges"] == {"period": None, "groups": {}}
    saved = call(c, clock, "PUT", URL, {"projects": [{"name": "Dung Quất 2", "due": "Q3/2025"}], "ranges": {"machinery": {"from": "1", "to": "25"}},
                                       "expected_version": 0, "request_id": "fan-1"}).json()
    assert saved["version"] == 1 and saved["projects"][0]["due"] == "2025-Q3" and saved["ranges"]["groups"]["machinery"] == {"from": 1, "to": 25}
    pid = saved["projects"][0]["id"]
    locked = call(c, clock, "PUT", URL, {"projects": [{"id": pid, "name": "Dung Quất 2", "due": "Q4/2025"}], "ranges": {}, "expected_version": 1, "request_id": "fan-2"})
    assert locked.status_code == 422 and locked.json()["code"] == "due_locked"
    later = call(c, clock, "POST", f"{URL}/postpone", {"id": pid, "to": "Q2/2026", "reason": "chậm", "expected_version": 1, "request_id": "fan-3"}).json()
    assert later["version"] == 2 and later["projects"][0]["due"] == "2026-Q2" and len(later["projects"][0]["postpones"]) == 1
    done = call(c, clock, "POST", f"{URL}/complete", {"id": pid, "expected_version": 2, "request_id": "fan-4"}).json()
    assert done["projects"][0]["status"] == "done" and done["projects"][0]["state"] == "done"
    stale = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "expected_version": 1, "request_id": "fan-5"})  # written over since
    assert stale.status_code == 409
    assert call(c, clock, "GET", "/internal/stock/VCB/fixed-asset-notes").status_code == 404
    assert call(c, clock, "GET", "/internal/stock/FPT/fixed-asset-notes").status_code == 404


def test_the_prepaid_allocation_is_kept_beside_the_projects_and_survives_a_postponement(tmp_path):
    c, clock = client(tmp_path)
    saved = call(c, clock, "PUT", URL, {"projects": [{"name": "Dung Quất 2", "due": "Q3/2025"}], "ranges": {}, "prepaid": {"2021": {"total": "425"}},
                                       "expected_version": 0, "request_id": "pp-1"}).json()
    assert saved["prepaid"][0]["year"] == "2021" and saved["prepaid"][0]["total"] == "425" and saved["prepaid_kinds"]["overhaul"] == "Sửa chữa lớn"
    later = call(c, clock, "POST", f"{URL}/postpone", {"id": saved["projects"][0]["id"], "to": "Q1/2026", "expected_version": 1, "request_id": "pp-2"}).json()
    assert later["prepaid"][0]["total"] == "425"
    kept = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "expected_version": 2, "request_id": "pp-3"}).json()  # an older page sends none
    assert kept["prepaid"][0]["total"] == "425"


def test_deals_are_kept_beside_the_other_notes_and_survive_writes_that_leave_them_out(tmp_path):
    c, clock = client(tmp_path)
    saved = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "prepaid": {"2021": {"total": "425"}},
                                       "deals": [{"name": "Công ty B", "date": "2024-03-15", "share": "60", "price": "1000", "net_assets": "1000", "years": "10"}],
                                       "expected_version": 0, "request_id": "dl-1"}).json()
    assert saved["deals"][0]["goodwill"] == "400" and saved["deals"][0]["per_year"] == "40"
    kept = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "prepaid": {}, "expected_version": 1, "request_id": "dl-2"}).json()
    assert kept["deals"][0]["goodwill"] == "400" and kept["prepaid"] == []  # prepaid sent empty is cleared; deals left out are kept


def test_the_goodwill_amortisation_is_kept_and_the_view_carries_the_movement_and_the_bargains(tmp_path):
    c, clock = client(tmp_path)
    saved = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "goodwill_amort": {"2021": "821"},
                                       "deals": [{"name": "Final", "date": "30/06/2021", "share": "99.98", "price": "5598", "net_assets": "7315",
                                                  "note_goodwill": "-1670"}], "expected_version": 0, "request_id": "hn-1"}).json()
    assert saved["deals"][0]["gap"] == "-45.537" and saved["bargains"][0]["gain"] == "1670" and saved["bargains"][0]["flag"] is None  # no statements here
    assert saved["goodwill_moves"] == []
    kept = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "expected_version": 1, "request_id": "hn-2"}).json()
    assert kept["deals"][0]["note_goodwill"] == "-1670"


def test_loans_and_their_notes_are_kept_and_summed_and_survive_writes_that_leave_them_out(tmp_path):
    c, clock = client(tmp_path)
    saved = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "loans": [{"lender": "HSBC", "currency": "USD", "term": "long", "balance": "503"}],
                                       "debt_notes": {"period": "2021", "fx_shock": "5"}, "expected_version": 0, "request_id": "ln-1"}).json()
    assert saved["debt"]["total"] == "503" and saved["debt"]["fx_loss"] == "25.15" and saved["loans"][0]["lender"] == "HSBC" and "USD" in saved["currencies"]
    kept = call(c, clock, "PUT", URL, {"projects": [], "ranges": {}, "expected_version": 1, "request_id": "ln-2"}).json()
    assert kept["debt"]["total"] == "503" and kept["debt_notes"]["fx_shock"] == "5"
