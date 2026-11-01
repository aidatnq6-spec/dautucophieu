from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.domain.hindsight import lesson
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock, repo=True):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_hindsight_reads_the_ledger_and_stored_closes(tmp_path):
    store = SeriesStore(tmp_path / "trend-sources")
    store.upsert("FPT-1d", [(datetime(2026, 1, 1) + timedelta(days=i), "50" if i < 100 else "60") for i in range(380)])
    store.upsert("VNINDEX-1d", [(datetime(2026, 1, 1) + timedelta(days=i), "1000") for i in range(380)])
    clock = Clock()  # 15/01/2027
    c = client(tmp_path, clock)
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "d1", "type": "deposit", "effective_at": "2026-02-02", "sequence": 0,
                                                                 "amount": "100000000"}, "expected_version": 0, "request_id": "l1"})
    call(c, clock, "POST", "/internal/ledger/events", {"event": {"event_id": "b1", "type": "buy", "effective_at": "2026-02-03", "sequence": 0,
                                                                 "security_id": "FPT", "quantity": 100, "price": "50000", "fee": "0", "tax": "0"},
                                                       "expected_version": 1, "request_id": "l2"})
    out = call(c, clock, "GET", "/internal/hindsight").json()
    buy = out["trades"][0]
    assert buy["symbol"] == "FPT" and buy["horizons"]["3"]["change"] == "0.2000" and buy["horizons"]["12"]["status"] == "not_yet"
    assert out["threshold"] == "0.30" and out["biases"]["disposition"]["enough"] is False


def test_without_personal_store_hindsight_is_unavailable(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock, repo=False), clock, "GET", "/internal/hindsight").status_code == 503


def test_the_owners_own_lesson_needs_five_past_holds():
    four = [{"held_on": True, "change": "-0.1000"}] * 4
    assert lesson(four) is None
    five = four + [{"held_on": True, "change": "0.0500"}, {"held_on": False, "change": "-0.5"}]
    assert lesson(five) == "5 lần trước bạn giữ tiếp sau khi điều kiện bị phá; so với bán ngay lúc báo đầu, trung bình −7,0% (đã xảy ra, không phải dự báo)."
