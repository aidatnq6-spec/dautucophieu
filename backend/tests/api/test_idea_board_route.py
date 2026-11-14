from signed_client import call
from test_deposit_book_route import client  # ledger holds FPT


def test_cards_are_saved_dated_and_checked_against_the_ledger(tmp_path):
    c, clock = client(tmp_path)
    empty = call(c, clock, "GET", "/internal/journal/board").json()
    assert empty["version"] == 0 and empty["held_without_card"] == ["FPT"]
    body = call(c, clock, "PUT", "/internal/journal/board", {"cards": [{"id": "a", "symbol": "fpt", "stage": "research", "note": "đọc BCTC"}],
                                                             "expected_version": 0, "request_id": "ib1"}).json()
    card = next(col for col in body["columns"] if col["stage"] == "research")["cards"][0]
    assert body["version"] == 1 and card["symbol"] == "FPT" and card["moved_on"] == "2027-01-15" and card["days"] == 0
    assert card["hints"] == ["Sổ lệnh đang có mã này: chuyển sang Đang nắm?"] and body["held_without_card"] == []
    bad = call(c, clock, "PUT", "/internal/journal/board", {"cards": [{"id": "a", "symbol": "FPT", "stage": "x"}], "expected_version": 1, "request_id": "ib2"})
    assert bad.status_code == 422
