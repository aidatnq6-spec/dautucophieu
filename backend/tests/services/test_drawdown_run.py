from datetime import date, datetime
from decimal import Decimal

from investment_agent.api.auth import OwnerContext
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.drawdown import drawdown_run, render_alerts

OWNER = OwnerContext("owner-1", "owner", "test")


def repo_holding_kdh():
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "ledger_events", "main", {"events": [
        {"event_id": "d1", "type": "deposit", "effective_at": "2026-10-01", "sequence": 0, "amount": "500000000"},
        {"event_id": "b1", "type": "buy", "effective_at": "2026-10-02", "sequence": 0, "security_id": "KDH", "quantity": 1000, "price": "23400",
         "fee": "0", "tax": "0"}], "amendments": []}, expected_version=0, request_id="l1")
    return repo


def test_message_states_the_fall_against_cost_and_the_owners_threshold_without_advice():
    text = render_alerts([{"symbol": "KDH", "change": "-0.3700", "price": "14750", "cost": "23413"}], threshold=Decimal("0.30"), reasons={"KDH": "Quỹ đất lớn"})
    assert "KDH" in text and "−37,0%" in text and "14.750" in text and "23.413" in text and "30%" in text and "Quỹ đất lớn" in text
    assert "nên" not in text.lower()


def test_run_fills_history_alerts_once_and_remembers_it(tmp_path):
    repo = repo_holding_kdh()
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("KDH-1d", [(datetime(2026, 10, 26), "14.75")])
    series.upsert("VNINDEX-1d", [(datetime(2026, 10, 26), "1763.55")])
    fetched, sent = [], []

    def fetch(symbol, start: date, end: date):
        fetched.append(symbol)
        return [(datetime(2010, 2, 1), "30")] if end >= date(2010, 2, 1) else []
    out = drawdown_run(repo, OWNER, tmp_path, fetch=fetch, send=lambda t: sent.append(t) or True, request_id="r1")
    assert out["alerts"] == 1 and out["sent"] is True and sorted(set(fetched)) == ["KDH", "VNINDEX"]
    assert series.read("KDH-1d")[0][0] == datetime(2010, 2, 1)  # full history filled backwards
    again = drawdown_run(repo, OWNER, tmp_path, fetch=fetch, send=lambda t: sent.append(t) or True, request_id="r2")
    assert again["alerts"] == 0 and len(sent) == 1


def test_a_failed_send_is_retried_next_run(tmp_path):
    repo = repo_holding_kdh()
    SeriesStore(tmp_path / "trend-sources").upsert("KDH-1d", [(datetime(2026, 10, 26), "14.75")])
    out = drawdown_run(repo, OWNER, tmp_path, fetch=lambda *a: [], send=lambda t: False, request_id="r1")
    assert out == {"alerts": 1, "sent": False, "history": {"KDH": 0}}  # series with no stored closes yet are not backfilled
    out = drawdown_run(repo, OWNER, tmp_path, fetch=lambda *a: [], send=lambda t: True, request_id="r2")
    assert out["alerts"] == 1 and out["sent"] is True


def test_history_is_filled_for_watched_tickers_a_few_at_a_time_holdings_first(tmp_path):
    repo = repo_holding_kdh()
    (tmp_path / "market-symbols.txt").write_text("FPT\nHPG\nKDH\nVCB\n", encoding="utf-8")
    series = SeriesStore(tmp_path / "trend-sources")
    for s in ("KDH", "FPT", "HPG", "VCB", "VNINDEX", "VN30"):
        series.upsert(f"{s}-1d", [(datetime(2026, 10, 26), "10")])
    fetched = []

    def fetch(symbol, start, end):
        fetched.append(symbol)
        return []
    first = drawdown_run(repo, OWNER, tmp_path, fetch=fetch, send=lambda t: True, request_id="r1", backfill_limit=3)
    assert list(first["history"]) == ["VNINDEX", "VN30", "KDH"]  # indices and holdings first
    second = drawdown_run(repo, OWNER, tmp_path, fetch=fetch, send=lambda t: True, request_id="r2", backfill_limit=3)
    assert list(second["history"]) == ["FPT", "HPG", "VCB"]
    assert drawdown_run(repo, OWNER, tmp_path, fetch=fetch, send=lambda t: True, request_id="r3", backfill_limit=3)["history"] == {}


def test_the_alert_quotes_the_latest_decision_by_its_date_not_an_old_entry_imported_later(tmp_path):
    from investment_agent.domain.journal import JournalEntry
    from investment_agent.services.journal import append_entry, import_entries
    repo = repo_holding_kdh()
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("KDH-1d", [(datetime(2026, 10, 26), "14.75")])
    series.upsert("VNINDEX-1d", [(datetime(2026, 10, 26), "1763.55")])
    append_entry(repo, OWNER, JournalEntry(entry_id="new", symbol="KDH", kind="buy", created_on=date(2026, 10, 2), reason="Lý do mới"), request_id="j1")
    import_entries(repo, OWNER, [JournalEntry(entry_id="imp-old", symbol="KDH", kind="buy", created_on=date(2020, 1, 2), reason="Lý do từ 2020")], request_id="j2")
    sent = []
    drawdown_run(repo, OWNER, tmp_path, fetch=lambda *a: [], send=lambda t: sent.append(t) or True, request_id="r1")
    assert "Lý do mới" in sent[0] and "Lý do từ 2020" not in sent[0]


def _old(symbol, asset="Cổ phiếu", kind="buy"):
    from investment_agent.domain.journal import JournalEntry
    return JournalEntry(entry_id=f"imp-{symbol}-{kind}", symbol=symbol, kind=kind, created_on=date(2021, 1, 4), reason="",
                        imported={"asset": asset, "ticker": symbol, "qty": "1", "price": "1", "total": "1", "pnl": None})


def _run_old(repo, tmp_path, fetch, today=date(2026, 11, 9), limit=5):
    return drawdown_run(repo, OWNER, tmp_path, fetch=fetch, send=lambda t: True, request_id="r", today=today, old_price_limit=limit)


def test_prices_are_fetched_for_tickers_only_in_the_imported_journal_a_few_each_run(tmp_path):
    from investment_agent.services.journal import import_entries
    repo = repo_holding_kdh()
    import_entries(repo, OWNER, [_old("AAA"), _old("BBB", kind="sell"), _old("CCC"), _old("VANG", asset="Vàng"), _old("KDH")], request_id="j1")
    asked = []

    def fetch(symbol, start, end):
        asked.append(symbol)
        return [(datetime(2026, 11, 6), "20")] if end >= date(2026, 11, 6) and start <= date(2026, 11, 6) else []
    out = _run_old(repo, tmp_path, fetch, limit=2)
    series = SeriesStore(tmp_path / "trend-sources")
    assert out["old_prices"] == 2 and series.read("AAA-1d") and series.read("BBB-1d") and not series.read("CCC-1d")
    assert "VANG" not in asked  # gold is no ticker; KDH is held and filled as before
    _run_old(repo, tmp_path, fetch, limit=2)
    assert series.read("CCC-1d")


def test_a_ticker_with_no_prices_or_a_failing_call_does_not_stop_the_others_and_waits_a_month(tmp_path):
    from investment_agent.services.journal import import_entries
    repo = repo_holding_kdh()
    import_entries(repo, OWNER, [_old("AAA"), _old("BBB")], request_id="j1")
    asked = []

    def fetch(symbol, start, end):
        asked.append(symbol)
        if symbol == "AAA":
            raise RuntimeError("delisted")
        return [(datetime(2026, 11, 6), "20")] if symbol == "BBB" and start <= date(2026, 11, 6) else []
    _run_old(repo, tmp_path, fetch)
    assert SeriesStore(tmp_path / "trend-sources").read("BBB-1d")
    asked.clear()
    _run_old(repo, tmp_path, fetch, today=date(2026, 11, 20))
    assert "AAA" not in asked
    _run_old(repo, tmp_path, fetch, today=date(2026, 12, 15))
    assert "AAA" in asked


def test_an_old_tickers_prices_are_brought_up_to_date_after_a_week(tmp_path):
    from investment_agent.services.journal import import_entries
    repo = repo_holding_kdh()
    import_entries(repo, OWNER, [_old("AAA")], request_id="j1")
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("AAA-1d", [(datetime(2026, 11, 2), "10")])
    starts = []

    def fetch(symbol, start, end):
        if symbol == "AAA":
            starts.append(start)
            return [(datetime(2026, 11, 20), "12")] if end >= date(2026, 11, 20) else []
        return []
    _run_old(repo, tmp_path, fetch, today=date(2026, 11, 5))
    assert not [s for s in starts if s > date(2026, 1, 1)]  # still fresh: nothing newer asked for (the walk back to older years goes on)
    _run_old(repo, tmp_path, fetch, today=date(2026, 11, 21))
    assert date(2026, 11, 3) in starts and series.read("AAA-1d")[-1][0] == datetime(2026, 11, 20)
