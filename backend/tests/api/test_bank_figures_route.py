import json

from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client

ACB = {"group1": "447734", "group2": "7808", "group3": "1517", "group4": "1220", "group5": "2293",
       "demand_deposits": "166971", "margin_deposits": "10354", "customer_deposits": "537304.578", "car": "11.5"}


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("ACB\nFPT\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"ACB": "Ngân hàng", "FPT": "Công nghệ Thông tin"}}), encoding="utf-8")
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    c.app.state.data_dir = tmp_path
    return c, clock


def save(c, clock, quarter, values, version, rid, **source):
    return call(c, clock, "PUT", f"/internal/bank-figures/ACB/{quarter}",
                {"values": values, "source": source or {"kind": "manual"}, "expected_version": version, "request_id": rid})


def test_a_quarter_is_saved_with_its_ratios_and_listed_newest_first(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/bank-figures/ACB").json()["quarters"] == []
    r = save(c, clock, "2024-Q4", ACB, 0, "b1")
    assert r.status_code == 200
    r = save(c, clock, "2025-Q4", {**ACB, "car": None}, 1, "b2", kind="pdf", url="https://acb.com.vn/bctc.pdf", pages={"group1": 12})
    body = r.json()
    assert [q["quarter"] for q in body["quarters"]] == ["2025-Q4", "2024-Q4"] and body["version"] == 2
    latest = body["quarters"][0]
    assert latest["values"]["car"] is None and latest["derived"]["casa"] == "0.3300" and latest["derived"]["npl"] == "0.0109"
    assert latest["source"] == {"kind": "pdf", "url": "https://acb.com.vn/bctc.pdf", "pages": {"group1": 12}}


def test_edit_delete_and_bad_input(tmp_path):
    c, clock = client(tmp_path)
    save(c, clock, "2024-Q4", ACB, 0, "e1")
    assert save(c, clock, "2024-Q4", {**ACB, "group2": "8000"}, 1, "e2").json()["quarters"][0]["values"]["group2"] == "8000"
    assert save(c, clock, "2024-Q4", ACB, 1, "e3").status_code == 409  # stale version
    assert save(c, clock, "2024-Q5", ACB, 2, "e4").status_code == 422
    assert save(c, clock, "2024-Q3", {**ACB, "car": "150"}, 2, "e5").status_code == 422
    assert save(c, clock, "2024-Q3", {**ACB, "group1": "-1"}, 2, "e6").status_code == 422
    r = call(c, clock, "POST", "/internal/bank-figures/ACB/2024-Q4/delete", {"expected_version": 2, "request_id": "d1"})
    assert r.status_code == 200 and r.json()["quarters"] == []
    assert call(c, clock, "GET", "/internal/bank-figures/FPT").status_code == 404  # only watched banks


def test_a_public_pdf_is_read_into_proposed_values(tmp_path, monkeypatch):
    from investment_agent.api.routes import bank_figures
    pages = ["11. Chất lượng nợ cho vay\nĐơn vị: triệu đồng\nNợ đủ tiêu chuẩn 447.734.000 1\nNợ cần chú ý 7.808.000 1\n"
             "Nợ dưới tiêu chuẩn 1.517.000 1\nNợ nghi ngờ 1.220.000 1\nNợ có khả năng mất vốn 2.293.000 1"]
    monkeypatch.setattr(bank_figures, "_read_pdf", lambda url: pages)
    monkeypatch.setattr(bank_figures, "check_public_https", lambda url: None)
    c, clock = client(tmp_path)
    r = call(c, clock, "POST", "/internal/bank-figures/ACB/read-pdf", {"url": "https://acb.com.vn/bctc.pdf", "request_id": "p1"})
    assert r.status_code == 200 and r.json()["fields"]["group1"] == {"value": "447734", "page": 1}
    monkeypatch.setattr(bank_figures, "check_public_https", _refuse)
    r = call(c, clock, "POST", "/internal/bank-figures/ACB/read-pdf", {"url": "http://10.0.0.1/a.pdf", "request_id": "p2"})
    assert r.status_code == 422 and r.json()["code"] == "unsafe_url"


def _refuse(url):
    from investment_agent.domain.bank_figures import UnsafeUrl
    raise UnsafeUrl("Chỉ nhận đường dẫn https.")


def test_saved_figures_reach_the_bank_health_score_on_the_valuation_board(tmp_path):
    from investment_agent.market.financial_ratios import FinancialRatioStore
    c, clock = client(tmp_path)
    FinancialRatioStore(tmp_path / "financial-ratios").save({"symbol": "ACB", "kind": "bank", "fetched_at": "2026-10-31T00:00:00+00:00", "source": "t",
                                                             "quarters": {"2025-09-30": {"ROAA_TR_AVG4Q": "0.019"}, "2026-09-30": {"ROAA_TR_AVG4Q": "0.02"}}})
    save(c, clock, "2025-Q3", {**ACB, "group2": "9000"}, 0, "h1")
    save(c, clock, "2026-Q3", ACB, 1, "h2")
    rows = {r["symbol"]: r for r in call(c, clock, "GET", "/internal/fairvalue").json()["rows"]}
    ids = {cr["id"]: cr for cr in rows["ACB"]["quality"]["f_score"]["criteria"]}
    assert ids["group2_down"]["passed"] is True and "casa_up" in ids
