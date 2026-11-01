from datetime import datetime, timezone

import pytest

from investment_agent.api.auth import OwnerContext
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.chart_drawings import MAX_DRAWINGS, DrawingError, change_drawings, read_drawings

OWNER = OwnerContext("owner-1", "owner", "test")
NOW = datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)
ALLOWED = {"FPT", "HPG", "VNINDEX", "BTC"}


def _repo():
    return PersonalRepository("owner-1", MemoryDocumentStore())


def _change(repo, change, version, rid):
    return change_drawings(repo, OWNER, change, expected_version=version, request_id=rid, allowed=ALLOWED, now=NOW)


def test_a_level_and_a_trend_line_are_kept_per_ticker_and_removed():
    repo = _repo()
    drawings, version = _change(repo, {"action": "add", "symbol": "fpt", "kind": "hline", "price": "56.3"}, 0, "d1")
    assert version == 1 and drawings[0] | {"id": "x"} == {"id": "x", "symbol": "FPT", "kind": "hline", "interval": None, "price": "56.3",
                                                          "points": None, "created_at": NOW.isoformat()}
    trend = {"action": "add", "symbol": "HPG", "kind": "trend", "interval": "1D",
             "points": [{"t": "2026-09-01", "p": "26.5"}, {"t": "2026-10-30", "p": "28.15"}]}
    drawings, version = _change(repo, trend, 1, "d2")
    assert drawings[1]["interval"] == "1D" and drawings[1]["points"] == [{"t": "2026-09-01", "p": "26.5"}, {"t": "2026-10-30", "p": "28.15"}]
    hourly = {"action": "add", "symbol": "BTC", "kind": "trend", "interval": "1H", "points": [{"t": 1761900000, "p": "70000"}, {"t": 1761990000, "p": "71000.5"}]}
    drawings, version = _change(repo, hourly, 2, "d3")
    assert drawings[2]["points"][0] == {"t": 1761900000, "p": "70000"}
    weekly = {"action": "add", "symbol": "HPG", "kind": "trend", "interval": "1W", "points": [{"t": "2026-08-31", "p": "25"}, {"t": "2026-10-26", "p": "28"}]}
    drawings, version = _change(repo, weekly, 3, "d3w")
    assert drawings[3]["interval"] == "1W"
    drawings, version = _change(repo, {"action": "remove", "id": drawings[0]["id"]}, 4, "d4")
    assert [d["symbol"] for d in drawings] == ["HPG", "BTC", "HPG"] and read_drawings(repo, OWNER) == (drawings, 5)


def test_clearing_a_ticker_leaves_the_others():
    repo = _repo()
    _change(repo, {"action": "add", "symbol": "FPT", "kind": "hline", "price": "50"}, 0, "d1")
    _change(repo, {"action": "add", "symbol": "FPT", "kind": "hline", "price": "60"}, 1, "d2")
    _change(repo, {"action": "add", "symbol": "HPG", "kind": "hline", "price": "25"}, 2, "d3")
    drawings, version = _change(repo, {"action": "clear", "symbol": "fpt"}, 3, "d4")
    assert [d["symbol"] for d in drawings] == ["HPG"] and version == 4


@pytest.mark.parametrize("bad, code", [
    ({"action": "add", "symbol": "ZZZ", "kind": "hline", "price": "1"}, "symbol_not_watched"),
    ({"action": "add", "symbol": "FPT", "kind": "circle", "price": "1"}, "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "hline", "price": "-1"}, "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "hline", "price": "56,3"}, "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "hline", "price": "1.23456789012345678"}, "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1Y", "points": [{"t": "2026-09-01", "p": "1"}, {"t": "2026-09-02", "p": "2"}]},
     "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1D", "points": [{"t": "2026-09-01", "p": "1"}]}, "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1D", "points": [{"t": "2026-09-01", "p": "1"}, {"t": "2026-09-01", "p": "2"}]},
     "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1D", "points": [{"t": 1761900000, "p": "1"}, {"t": 1761990000, "p": "2"}]},
     "invalid_drawing"),  # daily bars are keyed by date
    ({"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1H", "points": [{"t": "2026-09-01", "p": "1"}, {"t": 1761990000, "p": "2"}]},
     "invalid_drawing"),
    ({"action": "add", "symbol": "FPT", "kind": "trend", "interval": "1D", "points": [{"t": "2026-02-30", "p": "1"}, {"t": "2026-03-02", "p": "2"}]},
     "invalid_drawing"),
    ({"action": "remove", "id": "nope"}, "drawing_not_found"),
    ({"action": "move"}, "invalid_drawing"),
])
def test_bad_drawings_are_refused(bad, code):
    with pytest.raises(DrawingError) as err:
        _change(_repo(), bad, 0, "bad")
    assert err.value.code == code


def test_at_most_two_hundred_drawings():
    repo = _repo()
    for i in range(MAX_DRAWINGS):
        _change(repo, {"action": "add", "symbol": "FPT", "kind": "hline", "price": str(i + 1)}, i, f"d{i}")
    with pytest.raises(DrawingError) as err:
        _change(repo, {"action": "add", "symbol": "FPT", "kind": "hline", "price": "1"}, MAX_DRAWINGS, "over")
    assert err.value.code == "too_many_drawings"
