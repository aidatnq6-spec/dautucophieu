from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("HPG" + chr(10), encoding="utf-8")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


GROUP = {"name": "Sản lượng bán", "unit": "nghìn tấn", "period": "quarter", "series": ["Thép XD", "HRC"], "chart": "stack"}


def test_the_owner_defines_a_group_enters_a_period_with_its_source_and_removes_them(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/operating/HPG").json() == {"symbol": "HPG", "version": 0, "groups": []}
    v = call(c, clock, "PUT", "/internal/operating/HPG/groups/san-luong", {**GROUP, "expected_version": 0, "request_id": "g1"}).json()
    assert v["version"] == 1 and v["groups"][0]["id"] == "san-luong" and v["groups"][0]["rows"] == []
    v = call(c, clock, "PUT", "/internal/operating/HPG/groups/san-luong/values/2026-Q3",
             {"values": {"Thép XD": "1340", "HRC": "2100"}, "source": "Bản tin SXKD 10/2026", "expected_version": 1, "request_id": "v1"}).json()
    assert v["groups"][0]["rows"][0]["total"] == "3440" and v["groups"][0]["rows"][0]["source"] == "Bản tin SXKD 10/2026"
    v = call(c, clock, "POST", "/internal/operating/HPG/groups/san-luong/values/2026-Q3/delete", {"expected_version": 2, "request_id": "v2"}).json()
    assert v["groups"][0]["rows"] == []
    v = call(c, clock, "POST", "/internal/operating/HPG/groups/san-luong/delete", {"expected_version": 3, "request_id": "g2"}).json()
    assert v["groups"] == []


def test_definitions_and_values_are_checked(tmp_path):
    c, clock = client(tmp_path)
    bad = call(c, clock, "PUT", "/internal/operating/HPG/groups/x", {**GROUP, "series": [], "expected_version": 0, "request_id": "b1"})
    assert bad.status_code == 422
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/x", {**GROUP, "series": ["A", "A"], "expected_version": 0, "request_id": "b2"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/Bad_Id", {**GROUP, "expected_version": 0, "request_id": "b3"}).status_code == 422
    call(c, clock, "PUT", "/internal/operating/HPG/groups/x", {**GROUP, "expected_version": 0, "request_id": "b4"})
    entry = {"values": {"Thép XD": "1"}, "source": "Bản tin", "expected_version": 1}
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/x/values/2026-09", {**entry, "request_id": "b5"}).status_code == 422  # a month in a quarterly group
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/x/values/2026-Q3", {**entry, "source": "", "request_id": "b6"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/x/values/2026-Q3", {**entry, "values": {"Khác": "1"}, "request_id": "b7"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/x/values/2026-Q3", {**entry, "values": {"HRC": "abc"}, "request_id": "b8"}).status_code == 422
    assert call(c, clock, "PUT", "/internal/operating/HPG/groups/nope/values/2026-Q3", {**entry, "request_id": "b9"}).status_code == 404
    assert call(c, clock, "GET", "/internal/operating/ZZZ").status_code == 404


def test_a_public_pdf_gives_proposed_values_for_the_group_s_lines_and_nothing_is_saved(tmp_path, monkeypatch):
    from investment_agent.api.routes import operating
    monkeypatch.setattr(operating, "_read_pdf", lambda url: ["Thép xây dựng đạt 412.300 tấn", "HRC 512.000 tấn"])
    monkeypatch.setattr(operating, "check_public_https", lambda url: None)
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/operating/HPG/groups/san-luong", {**GROUP, "series": ["Thép xây dựng", "HRC", "Tôn mạ"], "expected_version": 0,
                                                                      "request_id": "g1"})
    out = call(c, clock, "POST", "/internal/operating/HPG/groups/san-luong/read-pdf",
               {"url": "https://www.hoaphat.com.vn/bantin-10-2026.pdf", "request_id": "r1"}).json()
    assert out["url"] == "https://www.hoaphat.com.vn/bantin-10-2026.pdf" and out["missing"] == ["Tôn mạ"]
    assert out["values"]["Thép xây dựng"][0] == {"value": "412300", "page": 1, "text": "Thép xây dựng đạt 412.300 tấn"}
    assert call(c, clock, "GET", "/internal/operating/HPG").json()["version"] == 1  # proposals only, nothing written


def test_reading_a_pdf_needs_a_safe_link_and_an_existing_group(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/operating/HPG/groups/x", {**GROUP, "expected_version": 0, "request_id": "g1"})
    assert call(c, clock, "POST", "/internal/operating/HPG/groups/x/read-pdf", {"url": "http://example.com/a.pdf", "request_id": "r1"}).status_code == 422
    assert call(c, clock, "POST", "/internal/operating/HPG/groups/none/read-pdf", {"url": "https://example.com/a.pdf", "request_id": "r2"}).status_code == 404
