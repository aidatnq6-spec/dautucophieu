from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import (
    PersonalRepository, MemoryDocumentStore, VersionConflict, IdempotencyConflict,
    OwnerDenied, RepositoryUnavailable, InvalidRecord,
)
from investment_agent.repositories.personal_cache import PersonalCache, CachedPersonalRepository

OWNER = OwnerContext("owner-1", "owner", "test-1")
NOW = datetime(2026, 10, 25, 10, tzinfo=timezone.utc)


@pytest.fixture
def store():
    return MemoryDocumentStore()


@pytest.fixture
def repo(store):
    return PersonalRepository("owner-1", store, clock=lambda: NOW)


def write(repo, request_id="request-1", version=0, payload=None, context=OWNER):
    return repo.write(context, "profile_versions", "main", payload or {"capital": "100.25"}, expected_version=version, request_id=request_id)


def test_cas_and_immutable_history(repo):
    first = write(repo)
    second = write(repo, "request-2", 1, {"capital": "200"})
    assert (first.version, second.version) == (1, 2)
    assert repo.read(OWNER, "profile_versions", "main", version=1).payload == {"capital": "100.25"}
    assert repo.read(OWNER, "profile_versions", "main").payload == {"capital": "200"}
    with pytest.raises(VersionConflict):
        write(repo, "request-3", 1)


def test_retry_returns_original_revision_after_later_update(repo):
    first = write(repo)
    write(repo, "request-2", 1, {"capital": "200"})
    assert write(repo) == first
    assert repo.read(OWNER, "profile_versions", "main").version == 2


def test_request_id_cannot_be_reused_for_different_payload_or_target(repo):
    write(repo)
    with pytest.raises(IdempotencyConflict):
        write(repo, payload={"capital": "999"})
    with pytest.raises(IdempotencyConflict):
        repo.write(OWNER, "risk_versions", "main", {"answers": "AAAA"}, expected_version=0, request_id="request-1")


@pytest.mark.parametrize("context", [OwnerContext("intruder", "owner", "test"), OwnerContext("owner-1", "viewer", "test"), None])
def test_owner_rejected_before_storage_access(store, context):
    store.available = False
    repo = PersonalRepository("owner-1", store)
    with pytest.raises(OwnerDenied):
        write(repo, context=context)
    with pytest.raises(OwnerDenied):
        repo.read(context, "profile_versions", "main")


def test_owner_namespaces_are_separate(store):
    first = PersonalRepository("owner-1", store)
    second = PersonalRepository("owner-2", store)
    write(first)
    assert second.read(OwnerContext("owner-2", "owner", "test"), "profile_versions", "main") is None
    assert all(path.startswith("owners/owner-1/") for path in store.documents)


def test_concurrent_cas_has_one_winner(repo):
    def attempt(i):
        try:
            return write(repo, f"request-{i}").version
        except VersionConflict:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, (1, 2)), key=str) == [1, "conflict"]


def test_concurrent_identical_requests_create_one_version(repo):
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: write(repo), range(4)))
    assert all(record == records[0] for record in records)
    assert repo.read(OWNER, "profile_versions", "main").version == 1


def test_transaction_failure_does_not_publish_partial_state(repo, store):
    store.fail_commit = True
    with pytest.raises(RepositoryUnavailable):
        write(repo)
    assert not store.documents
    store.fail_commit = False
    assert write(repo).version == 1


@pytest.mark.parametrize("collection,record_id,payload", [
    ("unknown", "main", {}), ("profile_versions", "../other", {}),
    ("settings", "main", {"nested": {"bot_token": "SECRET"}}),
    ("profile_versions", "main", {"amount": 0.1}),
])
def test_invalid_records_rejected(repo, collection, record_id, payload):
    with pytest.raises(InvalidRecord):
        repo.write(OWNER, collection, record_id, payload, expected_version=0, request_id="request-1")


def test_payload_is_not_aliased(repo):
    payload = {"goals": [{"amount": "100"}]}
    record = write(repo, payload=payload)
    payload["goals"][0]["amount"] = "999"
    record.payload["goals"][0]["amount"] = "888"
    assert repo.read(OWNER, "profile_versions", "main").payload == {"goals": [{"amount": "100"}]}


def test_cached_read_is_stale_offline_and_cannot_authorize_publish(repo, store, tmp_path):
    with PersonalCache(tmp_path / "cache.sqlite") as cache:
        service = CachedPersonalRepository(repo, cache)
        write(repo)
        fresh = service.read(OWNER, "profile_versions", "main")
        assert fresh.stale is False and fresh.verified_at == NOW
        store.available = False
        stale = service.read(OWNER, "profile_versions", "main")
        assert stale.stale is True and stale.record.version == 1
        with pytest.raises(RepositoryUnavailable):
            service.require_current(OWNER, {("profile_versions", "main"): 1})
        with pytest.raises(RepositoryUnavailable):
            service.write(OWNER, "profile_versions", "main", {"capital": "999"}, expected_version=1, request_id="request-2")
        assert service.read(OWNER, "profile_versions", "main").record.payload == {"capital": "100.25"}


def test_uncached_offline_and_nonowner_cache_access_fail(repo, store, tmp_path):
    with PersonalCache(tmp_path / "cache.sqlite") as cache:
        service = CachedPersonalRepository(repo, cache)
        write(repo)
        service.read(OWNER, "profile_versions", "main")
        store.available = False
        with pytest.raises(RepositoryUnavailable):
            service.read(OWNER, "risk_versions", "main")
        with pytest.raises(OwnerDenied):
            service.read(OwnerContext("intruder", "owner", "test"), "profile_versions", "main")


def test_current_versions_are_checked_together(repo, tmp_path):
    with PersonalCache(tmp_path / "cache.sqlite") as cache:
        service = CachedPersonalRepository(repo, cache)
        write(repo)
        assert service.require_current(OWNER, {("profile_versions", "main"): 1}) is None
        write(repo, "request-2", 1, {"capital": "200"})
        with pytest.raises(VersionConflict):
            service.require_current(OWNER, {("profile_versions", "main"): 1})


def test_ambiguous_commit_retry_does_not_duplicate_business_revision(repo, store):
    original = store.atomic
    def lost_response(operation):
        original(operation)
        raise RepositoryUnavailable("Response lost after remote commit")
    store.atomic = lost_response
    with pytest.raises(RepositoryUnavailable):
        write(repo)
    store.atomic = original
    assert write(repo).version == 1
    assert repo.read(OWNER, "profile_versions", "main").version == 1


def test_cache_reopens_and_never_regresses_on_older_retry(repo, store, tmp_path):
    path = tmp_path / "cache.sqlite"
    with PersonalCache(path) as cache:
        service = CachedPersonalRepository(repo, cache)
        service.write(OWNER, "profile_versions", "main", {"capital": "100.25"}, expected_version=0, request_id="request-1")
        service.write(OWNER, "profile_versions", "main", {"capital": "200"}, expected_version=1, request_id="request-2")
        service.write(OWNER, "profile_versions", "main", {"capital": "100.25"}, expected_version=0, request_id="request-1")
    store.available = False
    with PersonalCache(path) as cache:
        view = CachedPersonalRepository(repo, cache).read(OWNER, "profile_versions", "main")
        assert view.stale and view.record.version == 2
        assert view.record.payload == {"capital": "200"}


def test_remote_missing_record_invalidates_old_cached_copy(repo, store, tmp_path):
    with PersonalCache(tmp_path / "cache.sqlite") as cache:
        service = CachedPersonalRepository(repo, cache)
        write(repo)
        service.read(OWNER, "profile_versions", "main")
        store.documents.clear()  # Simulate a remote reset/restore, not an API deletion.
        assert service.read(OWNER, "profile_versions", "main").record is None
        store.available = False
        with pytest.raises(RepositoryUnavailable):
            service.read(OWNER, "profile_versions", "main")


def test_write_can_require_input_versions_in_the_same_transaction(repo, store):
    write(repo)  # profile_versions/main v1
    ok = repo.write(OWNER, "reports", "r1", {"status": "published"}, expected_version=0, request_id="rep-1",
                    inputs={("profile_versions", "main"): 1})
    assert ok.version == 1
    write(repo, request_id="request-2", version=1)  # profile moves to v2
    before = dict(store.documents)
    with pytest.raises(VersionConflict):
        repo.write(OWNER, "reports", "r2", {"status": "published"}, expected_version=0, request_id="rep-2",
                   inputs={("profile_versions", "main"): 1})
    assert store.documents == before
