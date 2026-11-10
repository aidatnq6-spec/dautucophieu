"""After a restart the first page view paid for the Firestore connection and the market files: the app now opens its main pages itself
once it is up, and keeps the connection open with one small read every 20 minutes."""

from investment_agent.api.auth import InternalAuthSettings, OwnerContext
from investment_agent.api.warmup import WARM_PATHS, keep_alive, warm_once
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import NOW, SECRET, TOKEN
from test_passive_income_route import client as passive_client

SETTINGS = InternalAuthSettings("owner-1", TOKEN, SECRET)


def test_the_main_pages_are_opened_once_with_signed_requests_the_app_accepts(tmp_path):
    c, clock = passive_client(tmp_path)  # an owner with data and a data folder
    assert warm_once(SETTINGS, get=lambda url, headers: c.get(url, headers=headers), clock=clock) == len(WARM_PATHS)
    assert "/internal/glance" in WARM_PATHS and "/internal/overview" in WARM_PATHS


def test_a_page_that_fails_does_not_stop_the_others_or_the_app():
    calls = []

    def get(url, headers):
        calls.append(url)
        raise OSError("not up yet")
    assert warm_once(SETTINGS, get=get, clock=lambda: NOW) == 0
    assert len(calls) == len(WARM_PATHS)


def test_keep_alive_reads_one_small_record_and_never_raises():
    store = MemoryDocumentStore()
    repo = PersonalRepository("owner-1", store)
    reads = []
    store_get = store.get_many
    store.get_many = lambda paths: reads.append(len(paths)) or store_get(paths)
    assert keep_alive(repo, "owner-1") is True and reads == [1]
    store.available = False
    assert keep_alive(repo, "owner-1") is False
    assert keep_alive(None, "owner-1") is False
    assert isinstance(OwnerContext("owner-1", "owner", "warmup"), OwnerContext)
