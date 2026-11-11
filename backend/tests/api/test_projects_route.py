import json

from signed_client import call
from test_passive_income_route import client as base_client


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("TCH\nFPT\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2, "sectors": {"TCH": "Bất động sản", "FPT": "Công nghệ Thông tin"}}),
                                              encoding="utf-8")
    return base_client(tmp_path)


def test_projects_are_kept_per_developer_and_add_up_by_year(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/stock/TCH/projects").json() == {"symbol": "TCH", "version": 0, "years": [], "projects": []}
    saved = call(c, clock, "PUT", "/internal/stock/TCH/projects", {"projects": [{"name": "New City", "total": "7500", "booked": "1100",
                                                                                "by_year": {"2026": "1500", "2027": "4900"}}],
                                                                   "expected_version": 0, "request_id": "proj-1"}).json()
    assert saved["version"] == 1 and saved["years"][-1] == {"year": "2027", "amount": "4900", "projects": 1} and saved["projects"][0]["unplaced"] == "0"
    bad = call(c, clock, "PUT", "/internal/stock/TCH/projects", {"projects": [{"name": "", "by_year": {}}], "expected_version": 1, "request_id": "proj-2"})
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_name"
    assert call(c, clock, "GET", "/internal/stock/FPT/projects").status_code == 404
