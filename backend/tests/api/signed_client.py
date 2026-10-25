"""Signed loopback requests for personal API route tests."""

import hashlib
import hmac
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings

TOKEN = "test-internal-token-" + "a" * 32
SECRET = "test-hmac-secret-" + "b" * 32
NOW = 1_800_000_000  # 2027-01-15T08:00:00Z
DAY = 86_400


class Clock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now


def make_client(clock, repository=None):
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=repository)
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))


def call(client, clock, method, target, payload=None):
    body = b"" if payload is None else json.dumps(payload).encode()
    nonce = uuid4().hex
    canonical = "\n".join(["v1", str(clock.now), nonce, "owner-1", "owner", "corr-1", method, target, hashlib.sha256(body).hexdigest()])
    headers = {"authorization": f"Bearer {TOKEN}", "x-owner-uid": "owner-1", "x-owner-role": "owner",
               "x-correlation-id": "corr-1", "x-request-timestamp": str(clock.now), "x-request-nonce": nonce,
               "x-request-signature": hmac.new(SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest(),
               "content-type": "application/json"}
    return client.request(method, target, content=body, headers=headers)
