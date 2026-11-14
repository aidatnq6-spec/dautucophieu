from datetime import date

from investment_agent.domain.book_bridge import book_bridge
from investment_agent.domain.deposit_book import DepositBook


def book(units="50", chi="1", principal="200000000", extra_account=None):
    accounts = [{"id": "a", "name": "TK", "amount": "5000000", "liquid": True}] + ([extra_account] if extra_account else [])
    return DepositBook.model_validate({
        "accounts": accounts,
        "deposits": [{"id": "d", "bank": "NH", "matures": "2027-02-05", "principal": principal, "rate": "6", "interest": None, "payout": "end", "locked": False}],
        "bonds": [{"id": "f", "name": "Quỹ", "amount": "900000", "fund": "VFF", "units": units}, {"id": "x", "name": "Trái phiếu riêng", "amount": "300000"}],
        "gold": [{"id": "g", "name": "Nhẫn", "amount": "8000000", "kind": "Nhẫn tròn", "chi": chi}], "crypto": []})


NAV = {"VFF": {"2026-10-30": "20000", "2026-11-28": "21000"}}
GOLD = {"Nhẫn tròn": {"2026-10-31": "9000000", "2026-11-30": "9500000"}}
S, E = date(2026, 10, 31), date(2026, 11, 30)


def test_price_moves_on_what_was_held_at_the_start_are_split_from_what_was_entered():
    out = book_bridge(book(), book(units="60", principal="210000000", extra_account={"id": "b", "name": "TK2", "amount": "1000000", "liquid": True}),
                      navs=NAV, gold=GOLD, start_day=S, end_day=E)
    assert out["status"] == "ok"
    assert out["start"] == str(5000000 + 200000000 + 50 * 20000 + 300000 + 9000000)
    assert out["end"] == str(6000000 + 210000000 + 60 * 21000 + 300000 + 9500000)
    steps = {s["id"]: s["amount"] for s in out["steps"]}
    assert steps == {"book:fund_price": "50000", "book:gold_price": "500000", "book:entries": str(1000000 + 10000000 + 10 * 21000)}


def test_a_fund_with_a_nav_history_that_starts_after_the_first_day_cannot_be_valued_then():
    out = book_bridge(book(), book(), navs={"VFF": {"2026-11-14": "20500"}}, gold=GOLD, start_day=S, end_day=E)
    assert out == {"status": "missing_prices", "missing": ["VFF"], "start_day": "2026-10-31", "end_day": "2026-11-30"}


def test_no_book_at_the_start_means_every_row_is_an_entry():
    out = book_bridge(None, book(), navs=NAV, gold=GOLD, start_day=S, end_day=E)
    assert out["start"] == "0" and [s["id"] for s in out["steps"]] == ["book:entries"]
