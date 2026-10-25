"""Opt-in, isolated emulator integration; never reads the user's .env files."""

import os
from urllib.parse import urlparse
from uuid import uuid4

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.firestore import FirestoreDocumentStore
from investment_agent.repositories.personal import PersonalRepository, VersionConflict, COLLECTIONS


def test_real_sdk_transactions_in_isolated_emulator(monkeypatch):
    host = os.environ.get("INVESTMENT_AGENT_TEST_FIRESTORE_EMULATOR")
    if not host:
        pytest.skip("Set INVESTMENT_AGENT_TEST_FIRESTORE_EMULATOR to an isolated loopback emulator")
    parsed = urlparse("http://" + host)
    if parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path or parsed.username or parsed.password or parsed.query or parsed.fragment:
        pytest.fail("Emulator tests require 127.0.0.1:port, never a production endpoint")
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", host)
    client = firestore.Client(project="demo-investment-agent-tests", credentials=AnonymousCredentials())
    uid = "test-" + uuid4().hex
    owner = OwnerContext(uid, "owner", "emulator-test")
    repo = PersonalRepository(uid, FirestoreDocumentStore(client))
    try:
        first = repo.write(owner, "profile_versions", "main", {"capital": "100"}, expected_version=0, request_id="request-1")
        assert repo.write(owner, "profile_versions", "main", {"capital": "100"}, expected_version=0, request_id="request-1") == first
        with pytest.raises(VersionConflict):
            repo.write(owner, "profile_versions", "main", {"capital": "200"}, expected_version=0, request_id="request-2")
        assert repo.read(owner, "profile_versions", "main").version == 1
    finally:
        # Delete only this generated namespace in the fixed demo emulator project.
        for collection in (*COLLECTIONS, "record_heads", "mutation_requests"):
            for document in client.collection("owners").document(uid).collection(collection).stream(timeout=10):
                document.reference.delete(timeout=10)
        client.close()
