import json

from investment_agent.services.sign_alerts import STATE, check_signs

ROWS = [{"symbol": "VCG", "signs": {"paper_income": True, "other_receivables": True, "other_high": None}, "details": {"paper_income": "Năm 2025: 9,2%"}},
        {"symbol": "DXG", "signs": {"paper_income": False, "other_receivables": True}, "details": {}}]
TITLES = {"paper_income": "Thu nhập tài chính chưa thu tiền", "other_receivables": "Phải thu khác lớn", "other_high": "Cao hơn ngành"}


def test_the_first_run_only_records_and_a_new_sign_on_a_held_ticker_is_told_once(tmp_path):
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    first = [{"symbol": "VCG", "signs": {"paper_income": False, "other_receivables": True}, "details": {}}, ROWS[1]]
    assert check_signs(tmp_path, rows=first, held={"VCG"}, titles=TITLES, send=send) == {"status": "baseline", "new": 0, "sent": False}
    assert sent == []
    out = check_signs(tmp_path, rows=ROWS, held={"VCG"}, titles=TITLES, send=send)
    assert out == {"status": "ok", "new": 1, "sent": True}
    assert sent == ["🔎 Dấu hiệu báo cáo mới ở mã đang nắm\n• VCG: Thu nhập tài chính chưa thu tiền — Năm 2025: 9,2%\n"
                    "Xem Phân tích ngành → Ngành theo quý → Dấu hiệu phải thu, và thuyết minh của mã."]
    assert check_signs(tmp_path, rows=ROWS, held={"VCG"}, titles=TITLES, send=send)["new"] == 0 and len(sent) == 1  # told once


def test_a_ticker_new_to_the_board_is_only_recorded_on_its_first_run_and_told_from_then_on(tmp_path):
    """Banks joined the board on 23/11/2026 (owner review): a held bank's signs already on are not news; only what turns on after."""
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    check_signs(tmp_path, rows=[ROWS[1]], held={"VCB"}, titles=TITLES, send=send)  # the board before banks
    bank = {"symbol": "VCB", "signs": {"provision_cut": True, "accrued_outpace": False}, "details": {}}
    assert check_signs(tmp_path, rows=[ROWS[1], bank], held={"VCB"}, titles=TITLES, send=send)["new"] == 0 and sent == []
    later = {**bank, "signs": {"provision_cut": True, "accrued_outpace": True}}
    assert check_signs(tmp_path, rows=[ROWS[1], later], held={"VCB"}, titles=TITLES, send=send)["new"] == 1 and len(sent) == 1


def test_signs_of_tickers_not_held_are_never_told_and_a_failed_send_is_tried_again(tmp_path):
    check_signs(tmp_path, rows=[{"symbol": "DXG", "signs": {}, "details": {}}, {"symbol": "VCG", "signs": {}, "details": {}}], held=set(), titles=TITLES,
                send=lambda text: True)
    assert check_signs(tmp_path, rows=ROWS, held=set(), titles=TITLES, send=lambda text: True)["new"] == 0  # nothing held: nothing told
    check_signs(tmp_path, rows=[{"symbol": "VCG", "signs": {}, "details": {}}], held={"VCG"}, titles=TITLES, send=lambda text: True)
    assert check_signs(tmp_path, rows=ROWS, held={"VCG"}, titles=TITLES, send=lambda text: False)["sent"] is False
    sent = []
    assert check_signs(tmp_path, rows=ROWS, held={"VCG"}, titles=TITLES, send=lambda text: sent.append(text) or True)["new"] == 2 and sent
    assert json.loads((tmp_path / "alerts" / STATE).read_text(encoding="utf-8"))["symbols"]["VCG"] == ["other_receivables", "paper_income"]
