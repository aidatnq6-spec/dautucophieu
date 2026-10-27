from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository, prefetch, read_scope

OWNER = OwnerContext("owner-1", "owner", "test")


class CountingStore(MemoryDocumentStore):
    """Counts round trips: each atomic() is one Firestore transaction in production."""

    def __init__(self):
        super().__init__()
        self.trips = 0

    def atomic(self, operation):
        self.trips += 1
        return super().atomic(operation)


def repo_with(*records):
    store = CountingStore()
    repo = PersonalRepository("owner-1", store)
    for collection, record_id in records:
        repo.write(OWNER, collection, record_id, {"n": 1}, expected_version=0, request_id=f"seed-{collection}-{record_id}")
    store.trips = 0
    return repo, store


def test_outside_a_request_every_read_goes_to_the_store():
    repo, store = repo_with(("settings", "portfolio"))
    repo.read(OWNER, "settings", "portfolio")
    repo.read(OWNER, "settings", "portfolio")
    assert store.trips == 2


def test_within_a_request_a_record_is_read_once():
    repo, store = repo_with(("settings", "portfolio"), ("journal", "main"))
    with read_scope():
        first = repo.read(OWNER, "settings", "portfolio")
        again = repo.read(OWNER, "settings", "portfolio")
        repo.read(OWNER, "journal", "main")
        repo.read(OWNER, "settings", "missing")
        repo.read(OWNER, "settings", "missing")
    assert store.trips == 3 and again.payload == first.payload


def test_a_write_in_the_request_makes_the_next_read_fresh():
    repo, store = repo_with(("settings", "portfolio"))
    with read_scope():
        repo.read(OWNER, "settings", "portfolio")
        repo.write(OWNER, "settings", "portfolio", {"n": 2}, expected_version=1, request_id="w2")
        assert repo.read(OWNER, "settings", "portfolio").payload == {"n": 2}


def test_reads_do_not_leak_between_requests():
    repo, store = repo_with(("settings", "portfolio"))
    with read_scope():
        repo.read(OWNER, "settings", "portfolio")
    with read_scope():
        repo.read(OWNER, "settings", "portfolio")
    assert store.trips == 2


def test_prefetch_loads_several_records_together_for_the_rest_of_the_request():
    repo, store = repo_with(("settings", "portfolio"), ("journal", "main"), ("ledger_events", "main"))
    with read_scope():
        prefetch(repo, OWNER, [("settings", "portfolio"), ("journal", "main"), ("ledger_events", "main"), ("settings", "missing")])
        before = store.trips
        repo.read(OWNER, "journal", "main")
        repo.read(OWNER, "settings", "missing")
    assert before == 4 and store.trips == 4


def test_prefetch_outside_a_request_does_nothing():
    repo, store = repo_with(("settings", "portfolio"))
    prefetch(repo, OWNER, [("settings", "portfolio")])
    assert store.trips == 0
