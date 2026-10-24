import hashlib
import hmac
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings


TOKEN = "test-internal-token-" + "a" * 32
SECRET = "test-hmac-secret-" + "b" * 32
NOW = 1_800_000_000


@pytest.fixture
def client():
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=lambda: NOW)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def signed_headers(*, uid="owner-1", timestamp=NOW, nonce="0123456789abcdef0123456789abcdef", body=b"", method="GET", target="/internal/identity", role="owner"):
    canonical = "\n".join(["v1", str(timestamp), nonce, uid, role, "correlation-1", method, target, hashlib.sha256(body).hexdigest()])
    return {
        "authorization": f"Bearer {TOKEN}", "x-owner-uid": uid,
        "x-owner-role": role, "x-correlation-id": "correlation-1",
        "x-request-timestamp": str(timestamp), "x-request-nonce": nonce,
        "x-request-signature": hmac.new(SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest(),
    }


def test_health_is_public_and_minimal(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_context(client):
    response = client.get("/internal/identity", headers=signed_headers())
    assert response.status_code == 200
    assert response.json() == {"uid": "owner-1", "role": "owner", "correlation_id": "correlation-1"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("header", list(signed_headers()))
def test_every_auth_field_is_required(client, header):
    headers = signed_headers()
    del headers[header]
    response = client.get("/internal/identity", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert TOKEN not in response.text and SECRET not in response.text


@pytest.mark.parametrize("changes", [{"uid": "intruder"}, {"role": "admin"}, {"timestamp": NOW - 61}, {"timestamp": NOW + 61}])
def test_unapproved_or_expired_signed_context_is_rejected(client, changes):
    assert client.get("/internal/identity", headers=signed_headers(**changes)).status_code == 401


@pytest.mark.parametrize("header,value", [("authorization", "Bearer wrong"), ("x-owner-uid", "intruder"), ("x-correlation-id", "changed"), ("x-request-signature", "invalid"), ("x-request-timestamp", "nan")])
def test_tampering_fails(client, header, value):
    headers = signed_headers()
    headers[header] = value
    assert client.get("/internal/identity", headers=headers).status_code == 401


def test_replay_rejected(client):
    headers = signed_headers()
    assert client.get("/internal/identity", headers=headers).status_code == 200
    assert client.get("/internal/identity", headers=headers).status_code == 401


@pytest.mark.parametrize("change", ["body", "method", "query", "path"])
def test_signature_binds_request(client, change):
    headers = signed_headers()
    method, target, body = "GET", "/internal/identity", b""
    if change == "body":
        body = b'{"amount":"100"}'
    elif change == "method":
        method = "POST"
    elif change == "query":
        target += "?owner=intruder"
    else:
        target = "/other"
    assert client.request(method, target, content=body, headers=headers).status_code == 401


def test_failed_signature_does_not_consume_nonce(client):
    headers = signed_headers()
    invalid = deepcopy(headers)
    invalid["x-request-signature"] = "0" * 64
    assert client.get("/internal/identity", headers=invalid).status_code == 401
    assert client.get("/internal/identity", headers=headers).status_code == 200


def test_all_future_routes_are_private_by_default(client):
    @client.app.get("/future-personal-data")
    def future_route():
        return {"private": True}
    assert client.get("/future-personal-data").status_code == 401


def test_non_loopback_peer_rejected():
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=lambda: NOW)
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("192.0.2.5", 50000)) as remote:
        assert remote.get("/internal/identity", headers=signed_headers()).status_code == 401


@pytest.mark.parametrize("token,secret", [("", SECRET), (TOKEN, ""), ("short", SECRET), (TOKEN, "short")])
def test_insecure_config_rejected(token, secret):
    with pytest.raises(ValueError):
        InternalAuthSettings("owner-1", token, secret)
