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


def test_a_gold_layer_outside_its_range_is_listed_with_a_link_to_the_pyramid(tmp_path, monkeypatch):
    from decimal import Decimal
    from investment_agent.domain.asset_pyramid import asset_pyramid
    import investment_agent.services.attention as attention
    repo, data = setup(tmp_path)
    pyramid = asset_pyramid({"reserve": Decimal(0), "cash": Decimal(0), "deposit": Decimal("940000000"), "gold": Decimal("60000000")},
                            deductions=Decimal(0), stock_ratio=Decimal(0))  # synthetic figures
    monkeypatch.setattr(attention, "budget_view", lambda repo, owner, quotes: ({"status": "ok", "pyramid": pyramid}, 0))
    gold = [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] == "gold_rebalance"]
    assert len(gold) == 1 and gold[0]["level"] == "low" and gold[0]["href"] == "/profile?tab=tai-san" and gold[0]["text"].startswith("Vàng chiếm 6,0%")
    monkeypatch.setattr(attention, "budget_view", lambda repo, owner, quotes: ({"status": "no_total"}, 0))
    assert not [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] == "gold_rebalance"]


def test_a_holding_past_both_giveback_thresholds_and_a_covered_goal_need_a_decision(tmp_path):
    from investment_agent.services.giveback import write_goals
    repo, data = setup(tmp_path)
    SeriesStore(data / "trend-sources").upsert("KDH-1d", [(datetime(2026, 10, 2), "30"), (datetime(2026, 10, 3), "45")])
    repo.write(OWNER, "settings", "portfolio", {"concentration_limit": "0.25", "journal_review_threshold": "0.15", "drawdown_threshold": "0.6",
                                                "giveback_min_gain": "0.3", "giveback_share": "0.5"}, expected_version=0, request_id="s1")
    write_goals(repo, OWNER, [{"id": "g1", "name": "Mua xe", "amount": "40000000", "basis": "value", "created_on": "2026-10-01", "closed": None}],
                expected_version=0, request_id="g1")
    items = [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] in ("giveback", "goal")]
    assert kinds(items) == [("high", "giveback", "KDH")]  # 45 → 15 against 30: the peak gain and as much again went back; 15 000 000 is short of the goal
    assert items[0]["href"] == "/portfolio" and "200,0%" in items[0]["text"]
    SeriesStore(data / "trend-sources").upsert("KDH-1d", [(datetime(2026, 11, 7), "42")])
    items = [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] in ("giveback", "goal")]
    assert kinds(items) == [("high", "goal", None)] and "Mua xe" in items[0]["text"]


def test_a_project_due_this_quarter_is_listed_with_the_company_s_figures_and_left_out_of_the_weekly_note(tmp_path):
    """Thuyết minh TSCĐ (25/11/2026): due once its quarter's report is stored; a low line until the owner confirms or postpones; not on Telegram."""
    from investment_agent.domain.fixed_asset_notes import validate_notes
    from investment_agent.market.statements import StatementStore
    from investment_agent.services.attention import weekly_todo
    repo, data = setup(tmp_path)
    projects, ranges = validate_notes([{"name": "Dung Quất 2", "due": "Q3/2026", "read_period": "2025"}], {}, stored=[])
    repo.write(OWNER, "settings", "fixed_asset_notes_HPG", {"symbol": "HPG", "projects": projects, "ranges": ranges}, expected_version=0, request_id="n1")
    B = 10**9
    StatementStore(data / "statements").save({"symbol": "HPG", "fetched_at": "x", "source": "t", "years": {"2025": {"cip": str(10721 * B), "ppe_gross": str(182309 * B)}},
                                              "quarters": {"2026-Q3": {"cip": str(16113 * B)}}})
    items = [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] == "cip_project"]
    assert [(i["level"], i["symbol"], i["href"]) for i in items] == [("low", "HPG", "/research/HPG")]
    assert items[0]["text"] == ("HPG: dự án Dung Quất 2 đến quý hoàn thành dự kiến Q3/26. XDCB dở dang cuối Q3/26: 16.113 tỷ (kỳ đã đọc 2025: 10.721 tỷ); "
                                "nguyên giá TSCĐ hữu hình: chưa có (182.309 tỷ). Xác nhận đã hoàn thành hoặc lùi hạn.")
    assert weekly_todo(items + [{"kind": "thesis", "text": "x"}]) == ["x"]


def test_a_tax_incentive_ending_this_year_is_listed_and_left_out_of_the_weekly_note(tmp_path):
    """Ưu đãi thuế (25/11/2026): a low line in the year the incentive ends; not on Telegram."""
    from investment_agent.domain.fixed_asset_notes import validate_incentives
    from investment_agent.services.attention import weekly_todo
    repo, data = setup(tmp_path)
    incentives = validate_incentives([{"entity": "Thép Dung Quất", "kind": "rate", "rate": "10", "until": "2026"}, {"entity": "Dự án B", "kind": "exempt", "until": "2030"}])
    repo.write(OWNER, "settings", "fixed_asset_notes_HPG", {"symbol": "HPG", "projects": [], "ranges": {}, "tax_incentives": incentives}, expected_version=0, request_id="ti1")
    items = [i for i in attention_items(repo, OWNER, data, now=NOW) if i["kind"] == "tax_incentive"]
    assert [(i["level"], i["symbol"], i["href"]) for i in items] == [("low", "HPG", "/research/HPG")]
    assert items[0]["text"] == ("HPG: ưu đãi thuế của Thép Dung Quất (thuế suất ưu đãi 10%) hết trong năm 2026; từ năm sau thuế suất thực tế có thể tăng. "
                                "Xem thuyết minh thuế TNDN của báo cáo năm.")
    assert weekly_todo(items) == []
