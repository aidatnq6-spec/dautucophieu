from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.ai.budget import SpendLedger
from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import NOW, SECRET, TOKEN, Clock, call


def client(tmp_path):
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock


def test_ai_status_shows_key_hint_policy_and_this_months_spend(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-" + "x" * 60 + "AbCd")
    ledger = SpendLedger(tmp_path / "ai" / "spend.sqlite")
    when = datetime.fromtimestamp(NOW, timezone.utc)
    for amount in ("0.0010605", "0.00233491"):
        rid = ledger.reserve("j", Decimal("0.01"), monthly=Decimal("2"), per_request=Decimal("0.2"), per_job=Decimal("0.2"), now=when)
        ledger.settle(rid, Decimal(amount))
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/settings/ai").json()
    assert body["key"] == {"configured": True, "hint": "…AbCd"}
    assert "sk-or" not in str(body)  # the key itself never leaves the server
    assert body["policy"]["status"] == "approved" and body["policy"]["monthly_usd"] == "2"
    assert body["policy"]["models"] == ["openai/gpt-6-luna", "deepseek/deepseek-v4-flash"]
    assert body["spend"] == {"month": when.strftime("%Y-%m"), "used_usd": "0.0034", "calls": 2}


def test_ai_status_without_key_or_spend(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/settings/ai").json()
    assert body["key"] == {"configured": False, "hint": None} and body["spend"]["calls"] == 0 and body["spend"]["used_usd"] == "0.0000"
    assert not (tmp_path / "ai").exists()  # reading the status creates nothing
