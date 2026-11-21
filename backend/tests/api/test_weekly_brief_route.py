import json

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def client(tmp_path, clock):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()), data_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def test_the_kept_weekly_briefs_are_listed_newest_first_and_each_is_read_whole(tmp_path):
    folder = tmp_path / "weekly-brief"
    folder.mkdir()
    for week, text in (("2026-11-13", "BẢN TIN TUẦN 09/11–13/11/2026"), ("2026-11-20", "BẢN TIN TUẦN 16/11–20/11/2026")):
        (folder / f"{week}.json").write_text(json.dumps({"week": week, "sent_at": f"{week}T01:32:00+00:00", "text": text}), encoding="utf-8")
    clock = Clock()
    c = client(tmp_path, clock)
    body = call(c, clock, "GET", "/internal/weekly-briefs").json()
    assert [w["week"] for w in body["weeks"]] == ["2026-11-20", "2026-11-13"]
    assert body["latest"]["text"].startswith("BẢN TIN TUẦN 16/11")
    one = call(c, clock, "GET", "/internal/weekly-briefs/2026-11-13").json()
    assert one["text"].startswith("BẢN TIN TUẦN 09/11")
    assert call(c, clock, "GET", "/internal/weekly-briefs/2026-11-06").status_code == 404


def test_no_brief_kept_yet_says_so(tmp_path):
    clock = Clock()
    assert call(client(tmp_path, clock), clock, "GET", "/internal/weekly-briefs").json() == {"weeks": [], "latest": None}
