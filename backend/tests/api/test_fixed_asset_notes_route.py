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
