import json

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.source_alerts import check_sources, macro_labels

from signed_client import SECRET, TOKEN, Clock, call


def test_cai_dat_lists_the_sources_failing_since_the_last_run(tmp_path):
    (tmp_path / "macro").mkdir()
    (tmp_path / "macro" / "_last_run.json").write_text(json.dumps({"at": "2026-11-16T00:36:00+00:00",
                                                                   "results": {"vn_retail_yoy": "error:ConnectError", "wti": "ok"}}), encoding="utf-8")
    check_sources(tmp_path, send=lambda text: True, labels=macro_labels())
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    body = call(c, clock, "GET", "/internal/settings/sources").json()
    assert body["checked"] == 2 and body["threshold"] == 3
    assert [(f["source"], f["fails"], f["error"]) for f in body["failing"]] == [("Cục Thống kê (nso.gov.vn)", 1, "ConnectError")]
