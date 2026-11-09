from datetime import date

from investment_agent.market.leading import MacroStore

from signed_client import call
from test_deposit_book_route import client, save_layers

MIX = {"deposit": "40", "bond": "10", "gold": "10", "stocks": "35", "crypto": "5"}


def falling(tmp_path):
    MacroStore(tmp_path).upsert("deposit_12m", [(date(2026, 6, 1), "6.5"), (date(2027, 1, 14), "5")], entry="auto")


def save(c, clock, version=0, rid="ct1", **targets):
    return call(c, clock, "PUT", "/internal/cycle-targets", {"up": None, "down": None, "flat": None, **targets, "expected_version": version, "request_id": rid})


def test_the_current_phases_targets_are_compared_with_the_tower(tmp_path):
    c, clock = client(tmp_path)
    falling(tmp_path)
    save_layers(c, clock)  # reserve 120, cash 95, deposits 300, gold 100, stocks 5 at cost: base 500 tr
    r = save(c, clock, down=MIX)
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "down" and body["basis"] == "vietnam" and body["reason"] is None and body["version"] == 1
    rows = {x["id"]: x for x in body["rows"]}
    assert rows["deposit"]["held"] == "395000000" and rows["deposit"]["gap"] == "-195000000"  # 40% of 500 tr less deposits and cash
    assert rows["stocks"]["gap"] == "170000000"
    assert body["targets"]["down"]["stocks"] == "35" and body["targets"]["up"] is None


def test_a_phase_without_targets_says_so_and_shows_no_rows(tmp_path):
    c, clock = client(tmp_path)
    falling(tmp_path)
    save_layers(c, clock)
    body = save(c, clock, up=MIX).json()
    assert body["phase"] == "down" and body["reason"] == "no_target" and body["rows"] == []


def test_no_tower_or_no_phase_is_said_rather_than_guessed(tmp_path):
    c, clock = client(tmp_path)
    assert call(c, clock, "GET", "/internal/cycle-targets").json()["phase"] is None
    assert call(c, clock, "GET", "/internal/cycle-targets").json()["reason"] == "no_phase"
    falling(tmp_path)
    body = call(c, clock, "GET", "/internal/cycle-targets").json()
    assert body["reason"] == "no_total" and body["version"] == 0


def test_saving_targets_leaves_the_tower_as_it_was(tmp_path):
    c, clock = client(tmp_path)
    falling(tmp_path)
    save_layers(c, clock)
    before = call(c, clock, "GET", "/internal/equity-budget").json()
    save(c, clock, down=MIX)
    assert call(c, clock, "GET", "/internal/equity-budget").json() == before


def test_a_stale_version_and_a_mix_not_at_100_are_refused(tmp_path):
    c, clock = client(tmp_path)
    assert save(c, clock, down=MIX).status_code == 200
    assert save(c, clock, version=0, rid="ct2", down=MIX).status_code == 409
    assert save(c, clock, version=1, rid="ct3", down={**MIX, "stocks": "30"}).status_code == 422
