from signed_client import Clock, call, make_client  # Clock date: 2027-01-15
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository


def client():
    clock = Clock()
    return make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore())), clock


def add(c, clock, rid, **over):
    body = {"on": "2027-01-10", "kind": "course", "title": "Khóa AI cho phân tích đầu tư", "amount": "5000000", "skill": "Dùng AI tổng hợp số liệu",
            "request_id": rid, **over}
    return call(c, clock, "POST", "/internal/intangibles/entries", body)


def test_entries_are_appended_and_summed_for_the_year_against_the_income_target():
    c, clock = client()
    call(c, clock, "PUT", "/internal/wealth-check", {"income": "30000000", "expenses": "20000000", "birth_year": 1989, "expected_version": 0,
                                                     "request_id": "wc1"})
    assert add(c, clock, "i1").status_code == 200
    assert add(c, clock, "i2", on="2026-12-20", amount="4000000", title="Sách").status_code == 200
    assert add(c, clock, "i1").status_code == 200  # a retry of the same request adds nothing
    body = call(c, clock, "GET", "/internal/intangibles").json()
    assert [e["title"] for e in body["entries"]] == ["Khóa AI cho phân tích đầu tư", "Sách"]  # newest date first
    assert body["target_rate"] == "10" and body["year"] == {"year": 2027, "spent": "5000000", "target": "36000000", "progress": "0.1389"}


def test_the_target_share_can_be_changed():
    c, clock = client()
    assert call(c, clock, "PUT", "/internal/intangibles/target", {"target_rate": "15", "request_id": "t1"}).status_code == 200
    assert call(c, clock, "GET", "/internal/intangibles").json()["target_rate"] == "15"
    assert call(c, clock, "PUT", "/internal/intangibles/target", {"target_rate": "0", "request_id": "t2"}).status_code == 422


def test_bad_entries_are_refused():
    c, clock = client()
    assert add(c, clock, "b1", kind="yacht").status_code == 422
    assert add(c, clock, "b2", amount="abc").status_code == 422
    assert add(c, clock, "b3", title="").status_code == 422


def test_an_entry_can_be_edited_in_place():
    c, clock = client()
    add(c, clock, "e1")
    body = {"on": "2027-01-12", "kind": "book", "title": "Sách định giá", "amount": "450000", "skill": "Đọc báo cáo tài chính", "request_id": "u1"}
    r = call(c, clock, "PUT", "/internal/intangibles/entries/e1", body)
    assert r.status_code == 200
    [entry] = r.json()["entries"]
    assert entry == {"id": "e1", "on": "2027-01-12", "kind": "book", "title": "Sách định giá", "amount": "450000", "skill": "Đọc báo cáo tài chính"}
    assert r.json()["year"]["spent"] == "450000"
    assert call(c, clock, "PUT", "/internal/intangibles/entries/zz", body).status_code == 404
    assert call(c, clock, "PUT", "/internal/intangibles/entries/e1", {**body, "amount": "0"}).status_code == 422


def test_an_entry_can_be_deleted_and_a_retried_delete_is_harmless():
    c, clock = client()
    add(c, clock, "d1")
    add(c, clock, "d2", title="Sách")
    r = call(c, clock, "POST", "/internal/intangibles/entries/d1/delete", {"request_id": "x1"})
    assert r.status_code == 200 and [e["id"] for e in r.json()["entries"]] == ["d2"]
    r = call(c, clock, "POST", "/internal/intangibles/entries/d1/delete", {"request_id": "x1"})
    assert r.status_code == 200 and [e["id"] for e in r.json()["entries"]] == ["d2"]
