from datetime import date

import pytest

from investment_agent.domain.idea_board import BoardError, board_view, merge_cards

TODAY = date(2026, 11, 14)


def test_a_card_moved_to_another_column_is_dated_today_and_an_unmoved_one_keeps_its_day():
    stored = [{"id": "a", "symbol": "FPT", "stage": "research", "note": "", "lesson": "", "moved_on": "2026-10-01"},
              {"id": "b", "symbol": "HPG", "stage": "idea", "note": "", "lesson": "", "moved_on": "2026-09-01"}]
    sent = [{"id": "a", "symbol": "FPT", "stage": "waiting", "note": "chờ 90", "lesson": ""},
            {"id": "b", "symbol": "HPG", "stage": "idea", "note": "thép", "lesson": ""},
            {"id": "c", "symbol": "mwg", "stage": "idea", "note": "", "lesson": ""}]
    out = {c["id"]: c for c in merge_cards(stored, sent, today=TODAY)}
    assert out["a"]["moved_on"] == "2026-11-14" and out["a"]["note"] == "chờ 90"
    assert out["b"]["moved_on"] == "2026-09-01" and out["c"]["symbol"] == "MWG" and out["c"]["moved_on"] == "2026-11-14"


def test_a_ticker_on_two_cards_or_an_unknown_column_is_refused():
    with pytest.raises(BoardError):
        merge_cards([], [{"id": "a", "symbol": "FPT", "stage": "idea"}, {"id": "b", "symbol": "FPT", "stage": "research"}], today=TODAY)
    with pytest.raises(BoardError):
        merge_cards([], [{"id": "a", "symbol": "FPT", "stage": "maybe"}], today=TODAY)


def test_the_board_checks_the_cards_against_the_ledger_and_the_theses():
    cards = [{"id": "a", "symbol": "FPT", "stage": "research", "note": "", "lesson": "", "moved_on": "2026-11-01"},
             {"id": "b", "symbol": "HPG", "stage": "holding", "note": "", "lesson": "", "moved_on": "2026-08-01"},
             {"id": "c", "symbol": "VCB", "stage": "holding", "note": "", "lesson": "", "moved_on": "2026-08-01"}]
    out = board_view(cards, held={"FPT", "VCB", "MWG"}, theses={"VCB"}, today=TODAY)
    cols = {c["stage"]: c for c in out["columns"]}
    assert [c["stage"] for c in out["columns"]] == ["idea", "research", "waiting", "holding", "sold"]
    fpt = cols["research"]["cards"][0]
    assert fpt["days"] == 13 and fpt["hints"] == ["Sổ lệnh đang có mã này: chuyển sang Đang nắm?"]
    hpg = next(c for c in cols["holding"]["cards"] if c["symbol"] == "HPG")
    assert hpg["hints"] == ["Sổ lệnh không còn mã này: chuyển sang Đã bán?", "Chưa có luận điểm đang mở"]
    assert next(c for c in cols["holding"]["cards"] if c["symbol"] == "VCB")["hints"] == []
    assert out["held_without_card"] == ["MWG"]
