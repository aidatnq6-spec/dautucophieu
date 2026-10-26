from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.corporate_events import EventStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call  # Clock date: 2027-01-15


def ev(i, sym, kind, key, title="t"):
    return {"id": f"{sym}-{i}", "symbol": sym, "code": "X", "kind": kind, "title": title, "key_date": key, "exright": key, "record": None,
            "payout": None, "ratio": None, "value_per_share": None}


def test_events_page_lists_upcoming_and_recent_with_insider_deals_apart(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nMBB\n", encoding="utf-8")
    store = EventStore(tmp_path)
    store.save("FPT", [ev(1, "FPT", "dividend_cash", "2027-01-20"), ev(2, "FPT", "meeting", "2027-04-10"), ev(3, "FPT", "insider", "2027-01-12"),
                       ev(4, "FPT", "issue", "2026-12-01"), ev(5, "FPT", "dividend_cash", None)], fetched_at="2027-01-15T15:40:00+07:00")
    store.save("MBB", [ev(1, "MBB", "meeting", "2027-01-18")], fetched_at="2027-01-15T15:40:00+07:00")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    body = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/events").json()
    assert [e["id"] for e in body["upcoming"]] == ["MBB-1", "FPT-1"]  # next 60 days, by date; the April meeting is later
    assert [e["id"] for e in body["undated"]] == ["FPT-5"]
    assert [e["id"] for e in body["recent"]] == []  # 01/12/2026 is more than 30 days back
    assert [e["id"] for e in body["insider"]] == ["FPT-3"]
    assert body["updated_at"] == "2027-01-15T15:40:00+07:00" and body["remind_days"] == 5
