import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from investment_agent.ai.catalog import load_catalog
from investment_agent.ai.openrouter import load_ai_policy
from investment_agent.domain.pinned import CONFIG_DIR
from investment_agent.insights.run import ICB_LEVEL2, allowed_sectors, insights_run
from investment_agent.insights.sources import ReportRef

NOW = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
CATALOG = json.dumps({"data": [{"id": "m/a", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
                                "supported_parameters": ["response_format"], "context_length": 1000000}]})


def test_catalog_is_cached_for_a_week(tmp_path):
    calls = []
    get = lambda url: calls.append(url) or CATALOG
    first = load_catalog(tmp_path / "catalog.json", get, now=NOW)
    again = load_catalog(tmp_path / "catalog.json", get, now=NOW + timedelta(days=6))
    assert first.models["m/a"].prompt_price == Decimal("0.0000001") and again.fetched_at == NOW and len(calls) == 1
    later = load_catalog(tmp_path / "catalog.json", get, now=NOW + timedelta(days=8))
    assert later.fetched_at == NOW + timedelta(days=8) and len(calls) == 2


def test_approved_policy_has_the_insights_task_and_two_dollar_budget():
    policy = load_ai_policy(CONFIG_DIR / "ai-policy.json")
    assert policy.status == "approved" and policy.budget.monthly_usd == Decimal("2")
    assert policy.tasks["insights"].required_parameters == ("response_format",) and policy.provider.zdr is True


def test_allowed_sectors_are_the_closed_icb_list_plus_local_names(tmp_path):
    (tmp_path / "industries.json").write_text(json.dumps({"sectors": {"ABC": "Ngành lạ"}}, ensure_ascii=False), encoding="utf-8")
    names = allowed_sectors(tmp_path)
    assert set(ICB_LEVEL2) <= set(names) and "Ngành lạ" in names and len(names) == len(set(names))
    assert "Ngân hàng" in ICB_LEVEL2


REF = ReportRef("acbs", "r1", "Cập nhật vĩ mô", "https://acbs.com.vn/x", "https://acbs.com.vn/a.pdf", date(2026, 10, 1))
SSI = ('<a class="titlePost" href="javascript:void(0)">Báo cáo ngành thép</a><p><span>01/10/2026</span></p>'
       '<a href="https://www.ssi.com.vn/analysis-center/report/download/bao-cao-nganh-thep"> Tải xuống </a>')


class Gateway:
    def complete(self, task, messages, *, job_id, response_format=None, tools=None):
        from investment_agent.ai.openrouter import Completion
        raw = {"macro_now": {"view": "favourable", "reasons": [{"text": "GDP tốt", "quote": "GDP tăng mạnh trong quý", "page": 1}]},
               "macro_outlook": {"view": "neutral", "reasons": []}, "sectors": []}
        return Completion("m/a", "p", json.dumps(raw), (), 10, 10, Decimal("0.001"), "reported", None, "v")


def run(tmp_path, gateway, notify=None, ssi_get=lambda url: SSI):
    return insights_run(tmp_path, ssi_get=ssi_get, discover=lambda since: [REF], download=lambda url: b"pdf",
                        pages=lambda data: ["GDP tăng mạnh trong quý ba"], gateway=gateway, notify=notify, now=NOW, sleep=lambda s: None)


def test_run_without_key_reports_not_configured_and_keeps_ssi_titles(tmp_path):
    out = run(tmp_path, None)
    assert out["status"] == "not_configured" and out["reason"] == "key_missing"
    status = json.loads((tmp_path / "insights" / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "not_configured" and status["at"] == NOW.isoformat()
    ssi = json.loads((tmp_path / "insights" / "ssi.json").read_text(encoding="utf-8"))
    assert ssi["titles"][0]["title"] == "Báo cáo ngành thép"


def test_run_processes_reports_then_notifies(tmp_path):
    seen = []
    out = run(tmp_path, Gateway(), notify=lambda store: seen.append(len(store.all())) or {"sent": 1, "failed": 0})
    assert out["status"] == "ok" and out["processed"] == ["acbs:r1"] and out["telegram"] == {"sent": 1, "failed": 0} and seen == [1]


def test_ssi_failure_does_not_stop_the_run(tmp_path):
    def boom(url):
        raise OSError("down")
    assert run(tmp_path, Gateway(), ssi_get=boom)["status"] == "ok"


def test_recent_run_is_not_repeated_within_the_interval(tmp_path):
    from investment_agent.insights.run import due
    assert due(tmp_path, now=NOW, min_hours=6) is True
    run(tmp_path, Gateway())
    assert due(tmp_path, now=NOW + timedelta(hours=5), min_hours=6) is False
    assert due(tmp_path, now=NOW + timedelta(hours=7), min_hours=6) is True


def test_cli_skips_without_network_when_the_last_run_is_recent(tmp_path, capsys):
    from investment_agent.cli import insights_cli
    (tmp_path / "insights").mkdir()
    (tmp_path / "insights" / "status.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    assert insights_cli(tmp_path, tmp_path / "cal.json", min_hours=6) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "skipped", "reason": "recent_run"}
