from signed_client import call
from test_deposit_book_route import client, save_book


def test_a_page_read_again_takes_its_records_in_one_batch_and_answers_the_same(tmp_path):
    c, clock = client(tmp_path)
    save_book(c, clock)
    store = c.app.state.personal_repository.store
    calls = []
    for name in ("get_many", "atomic"):
        if hasattr(store, name):
            original = getattr(store, name)
            setattr(store, name, lambda *a, _o=original, _n=name, **k: calls.append(_n) or _o(*a, **k))
    first = call(c, clock, "GET", "/internal/passive-income").json()
    first_calls = len(calls)
    calls.clear()
    second = call(c, clock, "GET", "/internal/passive-income").json()
    assert second == first
    assert len(calls) < first_calls and len(calls) <= 2  # one batch for the heads, one for revisions not yet in memory


def test_a_write_is_seen_by_the_next_read_of_the_page(tmp_path):
    c, clock = client(tmp_path)
    save_book(c, clock)
    before = call(c, clock, "GET", "/internal/deposit-book").json()
    save_book(c, clock, version=before["version"], rid="again", reserve="777000000")
    after = call(c, clock, "GET", "/internal/deposit-book").json()
    assert after["version"] == before["version"] + 1 and after["book"]["reserve"] == "777000000"  # read fresh, only batched



def test_an_older_revision_read_before_is_answered_from_memory(tmp_path):
    from investment_agent.api.auth import OwnerContext
    c, clock = client(tmp_path)
    save_book(c, clock)
    save_book(c, clock, version=1, rid="again", reserve="1000000")
    repo, owner = c.app.state.personal_repository, OwnerContext(uid="owner-1", role="owner", correlation_id="t")
    first = repo.read(owner, "settings", "deposit_book", version=1)
    calls = []
    original = repo.store.get_many
    repo.store.get_many = lambda paths: calls.append(paths) or original(paths)
    again = repo.read(owner, "settings", "deposit_book", version=1)
    assert again.payload == first.payload and again.version == 1 and calls == []
