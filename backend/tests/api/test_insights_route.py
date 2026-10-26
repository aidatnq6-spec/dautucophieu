import json
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.insights.store import InsightStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def record(ref, published, view, sectors, status="ok"):
    return {"source": "acbs", "ref_id": ref, "title": f"Báo cáo {ref}", "page_url": f"https://acbs.com.vn/{ref}",
            "pdf_url": f"https://acbs.com.vn/{ref}.pdf", "published": published, "status": status, "telegram_sent": True,
            "model": "m/a", "cost_usd": "0.004",
            "insight": None if status != "ok" else {
                "macro_now": {"view": view, "reasons": [{"text": "GDP tốt", "quote": "GDP tăng", "page": 1}]},
                "macro_outlook": {"view": "neutral", "reasons": []},
                "sectors": [{"sector": s, "effect": e, "reason": "lý do", "quote": "q", "page": 2} for s, e in sectors], "dropped": 0}}


def app_with(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}}), encoding="utf-8")
    years = {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2020, 2026)}
    quarters = {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")}
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
                                                      "years": years, "quarters": quarters, "issues": [],
                                                      "dividends": [{"date": f"{y}-07-01", "cash": "500"} for y in range(2021, 2027)]})
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(y, 12, 31), "12") for y in range(2020, 2026)])
    store = InsightStore(tmp_path / "insights")
    store.save(record("a", "2027-01-01", "favourable", [("Công nghệ Thông tin", "benefit"), ("Ngân hàng", "harm")]))
    store.save(record("b", "2026-12-20", "favourable", [("Ngân hàng", "harm")]))
    store.save(record("old", "2026-09-01", "unfavourable", [("Ngân hàng", "benefit")]))
    store.save(record("img", "2027-01-02", "", [], status="no_text"))
    (tmp_path / "insights" / "ssi.json").write_text(json.dumps({"at": "x", "titles": [{"title": "Ngành thép", "kind": "ngành", "date": "2027-01-05",
                                                                                     "url": "https://www.ssi.com.vn/analysis-center/report/download/thep"}]},
                                                                ensure_ascii=False), encoding="utf-8")
    (tmp_path / "insights" / "status.json").write_text(json.dumps({"at": "2027-01-15T07:00:00+00:00", "status": "stopped:budget_exceeded"}),
                                                       encoding="utf-8")
    market = SyntheticMarket(prices={"FPT": PricePoint(Decimal(9000), date(2027, 1, 14))})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=market, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def test_insights_summarises_recent_reports_and_links_watched_tickers_locally(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client, clock = app_with(tmp_path)
    body = call(client, clock, "GET", "/internal/insights").json()
    assert body["summary"]["reports"] == 2  # 60-day window; unreadable report not counted
    assert body["summary"]["macro_now"]["consensus"] == "favourable"
    sectors = {s["sector"]: s for s in body["summary"]["sectors"]}
    assert sectors["Công nghệ Thông tin"]["tickers"][0]["symbol"] == "FPT"
    assert sectors["Công nghệ Thông tin"]["tickers"][0]["verdict"] in {"cheap", "fair", "expensive"}
    assert sectors["Ngân hàng"]["harm"] == 2 and sectors["Ngân hàng"]["tickers"] == [{"symbol": "VCB", "verdict": "insufficient", "held": False}]
    assert [r["ref_id"] for r in body["reports"]] == ["img", "a", "b", "old"]
    assert body["reports"][0] == {"source": "acbs", "ref_id": "img", "title": "Báo cáo img", "url": "https://acbs.com.vn/img",
                                  "published": "2027-01-02", "status": "no_text"}
    assert body["ssi"][0]["title"] == "Ngành thép" and body["run"]["status"] == "stopped:budget_exceeded"
    assert body["ai_configured"] is False and body["window_days"] == 60


def test_insights_without_any_data_is_empty_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={}), data_dir=tmp_path)
    body = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/insights").json()
    assert body["summary"]["reports"] == 0 and body["reports"] == [] and body["ssi"] == [] and body["run"] is None
    assert body["ai_configured"] is True
