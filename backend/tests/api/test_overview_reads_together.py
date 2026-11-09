from investment_agent.api.routes import glance as glance_route
from investment_agent.services import equity_budget as eb

from signed_client import call
from test_deposit_book_route import client

BUDGET = {("settings", "equity_budget"), ("settings", "deposit_book"), ("risk_versions", "main"), ("profile_versions", "main"), ("settings", "risk_override"), ("ledger_events", "main")}


def test_the_budget_fetches_all_its_records_together(tmp_path, monkeypatch):
    c, clock = client(tmp_path)
    fetched = []
    monkeypatch.setattr(eb, "prefetch", lambda repo, owner, records: fetched.append(set(records)))
    assert call(c, clock, "GET", "/internal/equity-budget").status_code == 200
    assert fetched == [BUDGET]


def test_the_overview_fetches_the_asset_book_with_the_rest(tmp_path, monkeypatch):
    c, clock = client(tmp_path)
    fetched = []
    real = glance_route.prefetch
    monkeypatch.setattr(glance_route, "prefetch", lambda repo, owner, records: (fetched.append(set(records)), real(repo, owner, records))[1])
    assert call(c, clock, "GET", "/internal/glance").status_code == 200
    assert ("settings", "deposit_book") in fetched[0]
