from unittest.mock import MagicMock

from google.api_core.exceptions import ServiceUnavailable
import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.firestore import FirestoreDocumentStore, personal_repository_from_env
from investment_agent.repositories.personal import PersonalRepository, RepositoryUnavailable


def test_sdk_adapter_uses_transaction_for_all_reads_and_writes(monkeypatch):
    client, transaction = MagicMock(), MagicMock()
    client.transaction.return_value = transaction
    snapshots = {}

    def document(path):
        ref = MagicMock()
        ref.path = path
        snapshot = ref.get.return_value
        snapshot.exists = path in snapshots
        snapshot.to_dict.return_value = snapshots.get(path)
        return ref
    client.document.side_effect = document
    decorated = []

    def transactional(callback):
        decorated.append(callback)
        return callback
    monkeypatch.setattr("investment_agent.repositories.firestore.firestore.transactional", transactional)
    repo = PersonalRepository("owner", FirestoreDocumentStore(client))
    result = repo.write(OwnerContext("owner", "owner", "test"), "settings", "main", {"locale": "vi"}, expected_version=0, request_id="request-1")
    assert result.version == 1
    assert len(decorated) == 1
    client.transaction.assert_called_once_with(max_attempts=3)
    assert transaction.create.call_count == 2
    assert transaction.set.call_count == 1
    assert all(call.args[0].path.startswith("owners/owner/") for call in transaction.create.call_args_list)
    read_refs = [call.args[0] for call in client.document.call_args_list]
    assert any("/mutation_requests/" in path for path in read_refs)
    assert any("/record_heads/" in path for path in read_refs)


def test_firestore_failure_has_safe_message(monkeypatch):
    def transactional(callback):
        def failed(tx):
            raise ServiceUnavailable("SECRET private payload")
        return failed
    monkeypatch.setattr("investment_agent.repositories.firestore.firestore.transactional", transactional)
    with pytest.raises(RepositoryUnavailable, match="Personal repository unavailable") as error:
        FirestoreDocumentStore(MagicMock()).atomic(lambda tx: None)
    assert "SECRET" not in str(error.value)
    assert error.value.__suppress_context__ is True


def test_missing_production_credentials_do_not_fall_back_to_fake(monkeypatch):
    for name in ("FIREBASE_PROJECT_ID", "FIREBASE_CLIENT_EMAIL", "FIREBASE_PRIVATE_KEY", "FIREBASE_OWNER_UID", "FIRESTORE_EMULATOR_HOST", "FIREBASE_AUTH_EMULATOR_HOST"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RepositoryUnavailable, match="configuration incomplete"):
        personal_repository_from_env()


def test_production_factory_rejects_emulator_configuration(monkeypatch):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    with pytest.raises(RepositoryUnavailable, match="rejects emulator"):
        personal_repository_from_env()
