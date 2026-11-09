import json
from datetime import datetime, timedelta, timezone

from investment_agent.api.auth import OwnerContext
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.attention import attention_items
from investment_agent.services.theses import COLLECTION, RECORD

OWNER = OwnerContext("owner-1", "owner", "test")
NOW = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)


def setup(tmp_path):
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "ledger_events", "main", {"events": [
        {"event_id": "d1", "type": "deposit", "effective_at": "2026-10-01", "sequence": 0, "amount": "500000000"},
        {"event_id": "b1", "type": "buy", "effective_at": "2026-10-02", "sequence": 0, "security_id": "KDH", "quantity": 1000, "price": "30000", "fee": "0", "tax": "0"}],
        "amendments": []}, expected_version=0, request_id="l1")
    data = tmp_path / "data"
    data.mkdir()
    (data / "market-symbols.txt").write_text("KDH\nFPT\nHPG\n", encoding="utf-8")
    SeriesStore(data / "trend-sources").upsert("KDH-1d", [(datetime(2026, 11, 6), "15")])
    return repo, data


def theses(repo, *items):
    repo.write(OWNER, COLLECTION, RECORD, {"theses": list(items)}, expected_version=0, request_id="t1")


def thesis(symbol, status="broken", hold=None, closed_on=None):
    return {"symbol": symbol, "closed_on": closed_on, "conditions": [{"id": "c1", "kind": "loss_limit", "status": status, "hold": hold, "broken_on": "2026-11-01", "broken_price": "20000"}]}


def seen(data, symbol, on):
    FundamentalsStore(data / "fundamentals").save({"symbol": symbol, "fetched_at": "x", "source": "t", "years": {}, "quarters": {}, "dividends": [], "issues": [],
                                                   "latest_quarter_seen": {"quarter": "2026-Q3", "on": on}})


def kinds(items):
    return [(i["level"], i["kind"], i.get("symbol")) for i in items]


def test_what_needs_a_decision_comes_first_then_what_is_new(tmp_path):
    repo, data = setup(tmp_path)
    theses(repo, thesis("FPT"), thesis("HPG", hold={"until": "2026-12-01"}), thesis("VNM", closed_on="2026-11-02"), thesis("MWG", status="ok"))
    seen(data, "HPG", (NOW - timedelta(days=2)).date().isoformat())
    seen(data, "FPT", (NOW - timedelta(days=30)).date().isoformat())
    items = [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] != "system"]
    assert kinds(items) == [("high", "thesis", "FPT"), ("high", "drawdown", "KDH"), ("low", "quarter", "HPG")]
    assert "-50,0%" in items[1]["text"] and items[2]["href"] == "/research/HPG" and "Q3/2026" in items[2]["text"]


def test_a_problem_with_the_unattended_work_is_listed_and_sent_to_settings(tmp_path):
    repo, data = setup(tmp_path)
    items = attention_items(repo, OWNER, data, now=NOW)
    system = [i for i in items if i["kind"] == "system"]
    assert system and all(i["level"] == "high" and i["href"] == "/settings" for i in system) and any("Lịch sau phiên" in i["text"] for i in system)
    json.dumps(items)  # plain values, ready for the page and the weekly note
