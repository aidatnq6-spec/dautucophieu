from datetime import datetime

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.market.trend import SnapshotStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # MARKET prices FPT at 60,000


def client(tmp_path):
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(datetime(2027, 1, 14), "1250.5")])
    SnapshotStore(tmp_path / "trend").save({"session_date": "2027-01-14", "groups": [{"id": "stocks", "label": "Cổ phiếu", "rows": [
        {"id": "FPT", "label": "FPT", "cells": {"D1": {"macd": "up,>0", "rsi": 61, "zone": "neutral"}}}]}]})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_an_entry_captures_reason_emotion_and_the_context_of_the_moment(tmp_path):
    c, clock = client(tmp_path)
    made = call(c, clock, "POST", "/internal/journal", {"symbol": "fpt", "kind": "buy", "reason": "Lợi nhuận tăng đều, P/E thấp hơn trung vị",
                                                         "emotion": "fomo", "emotion_note": "sợ lỡ sóng", "ledger_event_id": "b1", "request_id": "j-1"})
    assert made.status_code == 200
    body = call(c, clock, "GET", "/internal/journal").json()
    e = body["entries"][0]
    assert e["symbol"] == "FPT" and e["kind"] == "buy" and e["emotion"] == "fomo" and e["ledger_event_id"] == "b1"
    assert e["context"]["price"] == "60000" and e["context"]["macd_d1"] == "up,>0" and e["context"]["rsi_d1"] == 61
    assert e["context"]["vnindex"] == "1250.5" and "verdict" in e["context"]
    assert e["current_price"] == "60000" and e["change"] == "0.0000" and body["threshold"] == "0.15"
    assert body["held"] == ["FPT"]  # tickers the owner can write a "why I still hold" entry for


def test_notes_are_appended_and_the_original_stays(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "POST", "/internal/journal", {"symbol": "FPT", "kind": "hold", "reason": "Giữ vì cổ tức đều", "emotion": "calm",
                                                 "request_id": "j-2"})
    entry_id = call(c, clock, "GET", "/internal/journal").json()["entries"][0]["entry_id"]
    added = call(c, clock, "POST", f"/internal/journal/{entry_id}/notes", {"text": "Vẫn giữ sau KQKD", "request_id": "n-1"})
    assert added.status_code == 200
    e = call(c, clock, "GET", "/internal/journal").json()["entries"][0]
    assert e["reason"] == "Giữ vì cổ tức đều" and [n["text"] for n in e["notes"]] == ["Vẫn giữ sau KQKD"]
    assert call(c, clock, "POST", "/internal/journal/nope/notes", {"text": "x", "request_id": "n-2"}).status_code == 404


def test_invalid_input_is_refused(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "POST", "/internal/journal", {"symbol": "FPT", "kind": "short", "reason": "x", "request_id": "j-3"}).status_code == 422
    assert call(c, clock, "POST", "/internal/journal", {"symbol": "FPT", "kind": "buy", "reason": "x", "emotion": "joy", "request_id": "j-4"}).status_code == 422


def test_the_review_threshold_is_set_in_settings(tmp_path):
    c, clock = client(tmp_path)
    ok = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {"concentration_limit": "0.25", "journal_review_threshold": "0.2"},
                                                               "expected_version": 0, "request_id": "pf-j1"})
    assert ok.status_code == 200 and call(c, clock, "GET", "/internal/journal").json()["threshold"] == "0.2"
    bad = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {"journal_review_threshold": "0"}, "expected_version": 1, "request_id": "pf-j2"})
    assert bad.status_code == 422
