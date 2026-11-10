import json
from datetime import datetime, timezone

from investment_agent.market.statements import StatementStore

from signed_client import call
from test_overview_route import buy_fpt  # FPT 100 shares at 50.000
from test_passive_income_route import client as base_client

B = 10**9


def quarters(values: dict[str, int]) -> dict:
    return {q: {"npat_parent": str(v * B), "npat": str(v * B), "cfo": str(v * B)} for q, v in values.items()}


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nHPG\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2, "sectors": {"FPT": "Công nghệ Thông tin", "HPG": "Tài nguyên Cơ bản"}}), encoding="utf-8")
    store = StatementStore(tmp_path / "statements")
    store.save({"symbol": "FPT", "quarters": quarters({"2025-Q1": 10, "2025-Q2": 10, "2025-Q3": 10, "2025-Q4": 10, "2026-Q1": 12, "2026-Q2": 12, "2026-Q3": 15}), "years": {}})
    store.save({"symbol": "HPG", "quarters": quarters({"2025-Q3": 20, "2025-Q4": 20, "2026-Q1": 20, "2026-Q2": 20}), "years": {}})
    return base_client(tmp_path)


def test_the_season_lists_each_ticker_and_marks_the_held_ones(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/earnings").json()
    assert body["quarter"] == "2026-Q3" and body["reported"] == 1 and body["watched"] == 2
    fpt = next(r for r in body["rows"] if r["symbol"] == "FPT")
    assert fpt["held"] is True and fpt["yoy"] == "0.5000" and fpt["review"] is None
    assert next(r for r in body["rows"] if r["symbol"] == "HPG")["reported"] is False
    assert body["sectors"] and body["cash"]


def test_a_review_is_kept_per_ticker_and_quarter(tmp_path):
    c, clock = client(tmp_path)
    r = call(c, clock, "PUT", "/internal/earnings/reviews", {"symbol": "FPT", "quarter": "2026-Q3", "verdict": "watch", "note": "biên giảm", "expected_version": 0, "request_id": "rv1"})
    assert r.status_code == 200 and next(x for x in r.json()["rows"] if x["symbol"] == "FPT")["review"] == "watch"
    r = call(c, clock, "PUT", "/internal/earnings/reviews", {"symbol": "FPT", "quarter": "2026-Q3", "verdict": "keep", "note": "", "expected_version": 1, "request_id": "rv2"})
    assert [x["verdict"] for x in r.json()["reviews"]] == ["keep"]  # the same quarter is replaced, not added
    assert call(c, clock, "PUT", "/internal/earnings/reviews", {"symbol": "FPT", "quarter": "2026-Q3", "verdict": "sell", "note": "", "expected_version": 2, "request_id": "rv3"}).status_code == 422


def test_a_held_ticker_with_a_new_report_and_no_review_is_in_vic_can_xem(tmp_path):
    from investment_agent.api.auth import OwnerContext
    from investment_agent.services.attention import attention_items
    c, clock = client(tmp_path)
    buy_fpt(c, clock)  # second buy is harmless: FPT is held
    repo, owner = c.app.state.personal_repository, OwnerContext("owner-1", "owner", "test")
    items = attention_items(repo, owner, tmp_path, now=datetime(2027, 1, 15, 3, tzinfo=timezone.utc))
    assert any(i["kind"] == "thesis_review" and i["symbol"] == "FPT" and "Q3/2026" in i["text"] and i["href"] == "/earnings#ra-soat" for i in items)
    call(c, clock, "PUT", "/internal/earnings/reviews", {"symbol": "FPT", "quarter": "2026-Q3", "verdict": "keep", "note": "", "expected_version": 0, "request_id": "rv1"})
    items = attention_items(repo, owner, tmp_path, now=datetime(2027, 1, 15, 3, tzinfo=timezone.utc))
    assert not any(i["kind"] == "thesis_review" for i in items)
