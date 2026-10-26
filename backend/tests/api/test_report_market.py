import json
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.jobs.runner import JobStore
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call

SNAP = {"session_date": "2027-01-14", "updated_at": "x",
        "indices": {"status": "ok", "rows": [{"id": "VNINDEX", "status": "ok", "close": "1650.12", "change": "-8.40", "pct": "-0.0051"}]},
        "board": {"status": "ok", "value_matched_bn": "1.00", "volume_matched": 1, "breadth": {"up": 1, "down": 0, "flat": 0, "no_trade": 0},
                  "foreign": {"buy_volume": 0, "sell_volume": 0, "buy_value_bn": "0.00", "sell_value_bn": "0.00", "net_value_bn": "0.00",
                              "top_sell": [], "top_buy": []}, "sectors": [],
                  "symbols": {"FPT": {"price": 61000, "ref": 60000, "change": 1000, "pct": "0.0167", "sector": "Công nghệ Thông tin"}}},
        "hose": {"status": "missing", "reason": "HOSE chưa công bố"}, "proprietary": {"status": "missing", "reason": "Chưa có nguồn miễn phí"},
        "news": {"status": "ok", "items": [{"title": "FPT ký hợp đồng", "url": "https://cafef.vn/a.chn", "source": "CafeF",
                                            "published": "2027-01-14T10:00:00+07:00"}]}}


def app_client(tmp_path, clock, with_snapshot=True):
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    if with_snapshot:
        (tmp_path / "brief").mkdir()
        (tmp_path / "brief" / "2027-01-14.json").write_text(json.dumps(SNAP, ensure_ascii=False), encoding="utf-8")
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=SyntheticMarket(prices={"FPT": PricePoint(Decimal(60000), date(2027, 1, 14))}), jobs=JobStore(tmp_path / "jobs.sqlite"),
                     outbox=type("Outbox", (), {"enqueue": lambda self, rid: None})(), data_dir=tmp_path)
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    accepted = call(client, clock, "POST", "/internal/jobs/after-close", {"session_date": "2027-01-14"}).json()
    report_id = call(client, clock, "GET", f"/internal/jobs/{accepted['job_id']}").json()["report_id"]
    return client, report_id


def test_report_carries_its_sessions_market_section(tmp_path):
    clock = Clock()
    client, rid = app_client(tmp_path, clock)
    body = call(client, clock, "GET", f"/internal/reports/{rid}").json()
    assert body["market"]["indices"]["rows"][0]["change"] == "-8.40"
    assert body["market"]["tickers"][0]["symbol"] == "FPT" and body["market"]["news"]["items"][0]["reason"] == "FPT"
    assert "symbols" not in body["market"]["board"]
    parts = call(client, clock, "POST", "/internal/notifications/preview", {"report_id": rid}).json()["parts"]
    assert "BẢN TIN SAU PHIÊN 14/01/2027" in parts[0] and "VN-Index 1.650,12" in parts[0]


def test_without_a_snapshot_the_market_is_null_and_telegram_keeps_the_old_text(tmp_path):
    clock = Clock()
    client, rid = app_client(tmp_path, clock, with_snapshot=False)
    assert call(client, clock, "GET", f"/internal/reports/{rid}").json()["market"] is None
    parts = call(client, clock, "POST", "/internal/notifications/preview", {"report_id": rid}).json()["parts"]
    assert "BẢN TIN SAU PHIÊN 2027-01-14" in parts[0]
