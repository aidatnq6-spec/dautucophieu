"""Reads go to the store in batches: the heads in one round trip, the revisions not yet seen in another. Revisions never change once
written, so one seen before is not fetched again; the head is always fetched, so a newer version is never missed."""

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository, RepositoryUnavailable, prefetch, read_scope

OWNER = OwnerContext("owner-1", "owner", "test")


class CountingStore(MemoryDocumentStore):
    def __init__(self):
        super().__init__()
        self.transactions, self.batches, self.paths = 0, 0, 0

    def atomic(self, operation):
        self.transactions += 1
        return super().atomic(operation)

    def get_many(self, paths):
        self.batches += 1
        self.paths += len(paths)
        return super().get_many(paths)


def repo_with(*records):
    store = CountingStore()
    repo = PersonalRepository("owner-1", store)
    for collection, record_id in records:
        repo.write(OWNER, collection, record_id, {"id": record_id}, expected_version=0, request_id=f"seed-{collection}-{record_id}")
    store.transactions = store.batches = store.paths = 0
    return repo, store


def test_prefetch_reads_every_record_in_two_round_trips_and_no_transaction():
    repo, store = repo_with(*(("settings", f"plan_{i}") for i in range(30)))
    with read_scope():
        prefetch(repo, OWNER, [("settings", f"plan_{i}") for i in range(30)] + [("settings", "missing")])
        assert (store.batches, store.transactions) == (2, 0)
        assert repo.read(OWNER, "settings", "plan_7").payload == {"id": "plan_7"}
        assert repo.read(OWNER, "settings", "missing") is None
    assert store.batches == 2


def test_a_plain_read_needs_no_transaction_and_a_revision_seen_before_is_not_fetched_again():
    repo, store = repo_with(("settings", "portfolio"))
    assert repo.read(OWNER, "settings", "portfolio").payload == {"id": "portfolio"}
    assert (store.batches, store.transactions) == (2, 0)
    assert repo.read(OWNER, "settings", "portfolio").payload == {"id": "portfolio"}
    assert store.batches == 3  # only the head


def test_a_newer_version_written_elsewhere_is_read():
    repo, store = repo_with(("settings", "portfolio"))
    repo.read(OWNER, "settings", "portfolio")
    other = PersonalRepository("owner-1", store)  # another process writes
    other.write(OWNER, "settings", "portfolio", {"id": "new"}, expected_version=1, request_id="elsewhere")
    record = repo.read(OWNER, "settings", "portfolio")
    assert record.version == 2 and record.payload == {"id": "new"}


def test_an_old_version_is_read_by_number():
    repo, _ = repo_with(("settings", "portfolio"))
    repo.write(OWNER, "settings", "portfolio", {"id": "two"}, expected_version=1, request_id="w2")
    assert repo.read(OWNER, "settings", "portfolio", version=1).payload == {"id": "portfolio"}
    assert repo.read(OWNER, "settings", "portfolio", version=3) is None


def test_a_head_without_its_revision_is_unavailable_not_empty():
    repo, store = repo_with(("settings", "portfolio"))
    store.documents = {p: d for p, d in store.documents.items() if "/settings/" not in p}
    with pytest.raises(RepositoryUnavailable):
        repo.read(OWNER, "settings", "portfolio")


def test_an_unavailable_store_fails_the_read_and_prefetch_leaves_it_to_the_read():
    repo, store = repo_with(("settings", "portfolio"))
    store.available = False
    with read_scope():
        prefetch(repo, OWNER, [("settings", "portfolio")])
        with pytest.raises(RepositoryUnavailable):
            repo.read(OWNER, "settings", "portfolio")


def test_prefetch_skips_records_already_read_in_the_request():
    repo, store = repo_with(("settings", "a"), ("settings", "b"))
    with read_scope():
        repo.read(OWNER, "settings", "a")
        before = store.paths
        prefetch(repo, OWNER, [("settings", "a"), ("settings", "b")])
        assert store.paths - before == 2  # b's head and revision only
        prefetch(repo, OWNER, [("settings", "a"), ("settings", "b")])
        assert store.paths - before == 2
