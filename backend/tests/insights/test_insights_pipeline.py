import json
from datetime import date, datetime, timezone
from decimal import Decimal

from investment_agent.ai.openrouter import AIUnavailable, Completion
from investment_agent.insights.pipeline import run_insights
from investment_agent.insights.sources import ReportRef
from investment_agent.insights.store import InsightStore

NOW = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
REF = ReportRef("acbs", "vi-mo-10-2026", "Cập nhật vĩ mô tháng 10/2026", "https://acbs.com.vn/x", "https://acbs.com.vn/a.pdf", date(2026, 10, 1))
PAGES = ["Tăng trưởng GDP quý III đạt 7,5%.", "Lãi suất thấp hỗ trợ ngành ngân hàng."]
RAW = {"macro_now": {"view": "favourable", "reasons": [{"text": "GDP tốt", "quote": "Tăng trưởng GDP quý III đạt 7,5%", "page": 1}]},
       "macro_outlook": {"view": "neutral", "reasons": []},
       "sectors": [{"sector": "Ngân hàng", "effect": "benefit", "reason": "lãi suất", "quote": "Lãi suất thấp hỗ trợ ngành ngân hàng", "page": 2}]}


class Gateway:
    def __init__(self, fail=None, content=None):
        self.calls, self.fail, self.content = [], fail, content

    def complete(self, task, messages, *, job_id, response_format=None, tools=None):
        if self.fail:
            raise AIUnavailable(self.fail)
        self.calls.append((task, messages, response_format))
        content = self.content if self.content is not None else json.dumps(RAW, ensure_ascii=False)
        return Completion("m/x", "p", content, (), 100, 50, Decimal("0.003"), "reported", "g1", "v")


def deps(tmp_path, gateway, **over):
    base = dict(store=InsightStore(tmp_path / "insights"), discover=lambda since: [REF], download=lambda url: b"%PDF",
                pages=lambda data: PAGES, gateway=gateway, sectors=["Ngân hàng", "Dầu khí"], now=NOW, sleep=lambda s: None)
    return {**base, **over}


def test_new_report_is_extracted_verified_and_saved_once(tmp_path):
    g = Gateway()
    first = run_insights(**deps(tmp_path, g))
    assert first == {"status": "ok", "processed": ["acbs:vi-mo-10-2026"], "skipped": 0}
    rec = InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026")
    assert rec["status"] == "ok" and rec["insight"]["sectors"][0]["sector"] == "Ngân hàng" and rec["cost_usd"] == "0.003"
    assert rec["telegram_sent"] is False and "pages" not in rec  # no PDF or full text kept
    assert g.calls[0][0] == "insights" and g.calls[0][2]["type"] == "json_schema"
    assert run_insights(**deps(tmp_path, g))["processed"] == [] and len(g.calls) == 1


def test_discovery_window_is_sixty_days(tmp_path):
    seen = []
    run_insights(**deps(tmp_path, Gateway(), discover=lambda since: seen.append(since) or []))
    assert seen == [date(2026, 8, 27)]


def test_at_most_three_new_reports_per_run(tmp_path):
    refs = [ReportRef("acbs", f"r{i}", "t", "u", "p", date(2026, 10, 1)) for i in range(5)]
    out = run_insights(**deps(tmp_path, Gateway(), discover=lambda since: refs))
    assert len(out["processed"]) == 3


def test_missing_key_or_budget_stops_without_marking_reports_processed(tmp_path):
    for code in ("key_missing", "budget_exceeded"):
        out = run_insights(**deps(tmp_path, Gateway(fail=code)))
        assert out["status"] == f"stopped:{code}" and InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026") is None


def test_report_without_text_is_recorded_and_not_sent_to_ai(tmp_path):
    g = Gateway()
    run_insights(**deps(tmp_path, g, pages=lambda data: []))
    assert InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026")["status"] == "no_text" and g.calls == []


def test_unparseable_or_unverified_answer_is_recorded_as_unreliable(tmp_path):
    run_insights(**deps(tmp_path, Gateway(content="not json")))
    assert InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026")["status"] == "no_reliable_claims"


def test_failed_download_is_retried_next_run(tmp_path):
    def boom(url):
        raise OSError("timeout")
    out = run_insights(**deps(tmp_path, Gateway(), download=boom))
    assert out["status"] == "ok" and out["processed"] == [] and InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026") is None


def test_store_recent_filters_by_window(tmp_path):
    store = InsightStore(tmp_path / "insights")
    for ref, published in (("new", "2026-10-01"), ("old", "2026-06-01")):
        store.save({"source": "acbs", "ref_id": ref, "published": published})
    assert [r["ref_id"] for r in store.recent(date(2026, 10, 26))] == ["new"]
