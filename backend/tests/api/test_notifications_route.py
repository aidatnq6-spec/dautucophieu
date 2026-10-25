import httpx

from investment_agent.api.auth import OwnerContext
from investment_agent.notifications.outbox import DeliveryStore
from investment_agent.notifications.telegram import TelegramSender
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client
from test_delivery_fixtures import REPORT

TOKEN = "123456789:" + "A" * 35
OWNER = OwnerContext("owner-1", "owner", "t")


def setup(tmp_path, responses):
    calls = []

    def transport(request):
        calls.append(request)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "reports", REPORT["report_id"], REPORT, expected_version=0, request_id="rep")
    sender = TelegramSender(TOKEN, client=httpx.Client(transport=httpx.MockTransport(transport)), sleep=lambda s: None)
    clock = Clock()
    client = make_client(clock, repo, telegram=sender, deliveries=DeliveryStore(tmp_path / "d.sqlite"))
    return client, clock, calls


SETTINGS = {"enabled": True, "chat_id": "-100123", "members_may_view_personal_data": True, "scheduled_enabled": False}


def save_settings(client, clock, settings=SETTINGS, version=0):
    return call(client, clock, "PUT", "/internal/notifications/settings", {"settings": settings, "expected_version": version, "request_id": f"s{version}"})


def test_settings_never_expose_or_accept_the_token(tmp_path):
    client, clock, _ = setup(tmp_path, [])
    status = call(client, clock, "GET", "/internal/notifications/settings").json()
    assert status["bot_token_configured"] is True and TOKEN not in str(status) and status["settings"]["enabled"] is False
    bad = save_settings(client, clock, {**SETTINGS, "bot_token": TOKEN})
    assert bad.status_code == 422 and TOKEN not in bad.text


def test_enabling_without_member_acknowledgement_is_rejected(tmp_path):
    client, clock, _ = setup(tmp_path, [])
    response = save_settings(client, clock, {**SETTINGS, "members_may_view_personal_data": False})
    assert response.status_code == 422


def test_preview_does_not_send(tmp_path):
    client, clock, calls = setup(tmp_path, [])
    save_settings(client, clock)
    preview = call(client, clock, "POST", "/internal/notifications/preview", {"report_id": REPORT["report_id"]}).json()
    assert preview["parts"][0].startswith("(1/1)") and calls == []


def test_test_send_requires_explicit_action_and_records_message_id(tmp_path):
    client, clock, calls = setup(tmp_path, [httpx.Response(200, json={"ok": True, "result": {"message_id": 77}})])
    save_settings(client, clock)
    result = call(client, clock, "POST", "/internal/notifications/test-send", {"report_id": REPORT["report_id"], "confirm": True}).json()
    assert result["status"] == "sent" and len(calls) == 1
    parts = call(client, clock, "GET", f"/internal/notifications/deliveries/{REPORT['report_id']}").json()["parts"]
    assert parts == [{"index": 0, "count": 1, "status": "sent", "message_id": 77}]
    assert call(client, clock, "POST", "/internal/notifications/test-send", {"report_id": REPORT["report_id"], "confirm": False}).status_code == 422


def test_unknown_part_needs_owner_resolution(tmp_path):
    client, clock, calls = setup(tmp_path, [httpx.ReadTimeout("slow"), httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})])
    save_settings(client, clock)
    send = lambda: call(client, clock, "POST", "/internal/notifications/test-send", {"report_id": REPORT["report_id"], "confirm": True}).json()
    assert send()["status"] == "unknown" and send()["status"] == "unknown" and len(calls) == 1
    call(client, clock, "POST", "/internal/notifications/resolve", {"report_id": REPORT["report_id"], "part": 0, "outcome": "not_received"})
    assert send()["status"] == "sent" and len(calls) == 2


def test_without_bot_token_sending_is_unavailable(tmp_path):
    clock = Clock()
    client = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()), deliveries=DeliveryStore(tmp_path / "d.sqlite"))
    assert call(client, clock, "GET", "/internal/notifications/settings").json()["bot_token_configured"] is False
    response = call(client, clock, "POST", "/internal/notifications/test-send", {"report_id": "c" * 32, "confirm": True})
    assert response.status_code == 503 and response.json()["code"] == "telegram_not_configured"
