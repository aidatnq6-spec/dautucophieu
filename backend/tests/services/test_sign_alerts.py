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
    bank = {"symbol": "VCB", "sector": "Ngân hàng", "signs": {"provision_cut": True, "accrued_outpace": False}, "details": {}}
    assert check_signs(tmp_path, rows=[ROWS[1], bank], held={"VCB"}, titles=TITLES, send=send)["new"] == 0 and sent == []
    later = {**bank, "signs": {"provision_cut": True, "accrued_outpace": True}}
    assert check_signs(tmp_path, rows=[ROWS[1], later], held={"VCB"}, titles=TITLES, send=send)["new"] == 1 and len(sent) == 1


def test_only_the_banks_joining_the_board_are_silent_once_and_any_other_new_ticker_is_told(tmp_path):
    """Review 23/11/2026 (2): the silence is for the banks' one-time arrival, never for a ticker the owner adds to the watchlist later."""
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    check_signs(tmp_path, rows=[ROWS[1]], held={"VCG", "VCB", "ACB"}, titles=TITLES, send=send)
    vcg = {"symbol": "VCG", "sector": "Xây dựng", "signs": {"other_receivables": True}, "details": {}}
    vcb = {"symbol": "VCB", "sector": "Ngân hàng", "signs": {"provision_cut": True}, "details": {}}
    assert check_signs(tmp_path, rows=[ROWS[1], vcg, vcb], held={"VCG", "VCB", "ACB"}, titles=TITLES, send=send)["new"] == 1  # VCG, not VCB
    assert "VCG" in sent[0] and "VCB" not in sent[0]
    acb = {"symbol": "ACB", "sector": "Ngân hàng", "signs": {"provision_cut": True}, "details": {}}  # a bank added after the banks joined
    assert check_signs(tmp_path, rows=[ROWS[1], vcg, vcb, acb], held={"VCG", "VCB", "ACB"}, titles=TITLES, send=send)["new"] == 1
    assert "ACB" in sent[1]


def test_a_ticker_that_could_not_be_read_keeps_what_was_recorded_so_nothing_is_told_twice(tmp_path):
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    on = {"symbol": "VCG", "signs": {"paper_income": True, "other_receivables": None}, "details": {}}
    check_signs(tmp_path, rows=[{**on, "signs": {"paper_income": False}}], held={"VCG"}, titles=TITLES, send=send)
    assert check_signs(tmp_path, rows=[on], held={"VCG"}, titles=TITLES, send=send)["new"] == 1
    unread = {"symbol": "VCG", "signs": {"paper_income": None, "other_receivables": None}, "details": {}}  # its file cut short
    check_signs(tmp_path, rows=[unread], held={"VCG"}, titles=TITLES, send=send)
    assert json.loads((tmp_path / "alerts" / STATE).read_text(encoding="utf-8"))["symbols"]["VCG"] == ["paper_income"]
    assert check_signs(tmp_path, rows=[on], held={"VCG"}, titles=TITLES, send=send)["new"] == 0 and len(sent) == 1


def test_a_sign_that_could_not_be_read_keeps_what_was_recorded_even_when_the_others_read(tmp_path):
    """Review 23/11/2026 (3): the quarterly file missing turns `lending` to None while the yearly signs still read; it is not cleared."""
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    check_signs(tmp_path, rows=[{"symbol": "VCG", "signs": {"lending": False, "paper_income": False}, "details": {}}], held={"VCG"}, titles=TITLES, send=send)
    on = {"symbol": "VCG", "signs": {"lending": True, "paper_income": False}, "details": {}}
    assert check_signs(tmp_path, rows=[on], held={"VCG"}, titles=TITLES, send=send)["new"] == 1
    check_signs(tmp_path, rows=[{"symbol": "VCG", "signs": {"lending": None, "paper_income": False}, "details": {}}], held={"VCG"}, titles=TITLES, send=send)
    assert check_signs(tmp_path, rows=[on], held={"VCG"}, titles=TITLES, send=send)["new"] == 0 and len(sent) == 1


def test_a_bank_unread_on_its_arrival_keeps_its_one_silent_run_for_when_it_reads(tmp_path):
    """Review 23/11/2026 (3): an unread bank on the run the banks join is not recorded, so its signs already on are not news later."""
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    check_signs(tmp_path, rows=[ROWS[1]], held={"VCB", "ACB"}, titles=TITLES, send=send)
    acb = {"symbol": "ACB", "sector": "Ngân hàng", "signs": {"provision_cut": False}, "details": {}}
    unread = {"symbol": "VCB", "sector": "Ngân hàng", "signs": {"provision_cut": None, "accrued_outpace": None}, "details": {}}
    check_signs(tmp_path, rows=[ROWS[1], acb, unread], held={"VCB", "ACB"}, titles=TITLES, send=send)
    read = {**unread, "signs": {"provision_cut": True, "accrued_outpace": False}}
    assert check_signs(tmp_path, rows=[ROWS[1], acb, read], held={"VCB", "ACB"}, titles=TITLES, send=send)["new"] == 0 and sent == []
    later = {**read, "signs": {"provision_cut": True, "accrued_outpace": True}}
    assert check_signs(tmp_path, rows=[ROWS[1], acb, later], held={"VCB", "ACB"}, titles=TITLES, send=send)["new"] == 1


def test_signs_of_tickers_not_held_are_never_told_and_a_failed_send_is_tried_again(tmp_path):
    check_signs(tmp_path, rows=[{"symbol": "DXG", "signs": {}, "details": {}}, {"symbol": "VCG", "signs": {}, "details": {}}], held=set(), titles=TITLES,
                send=lambda text: True)
    assert check_signs(tmp_path, rows=ROWS, held=set(), titles=TITLES, send=lambda text: True)["new"] == 0  # nothing held: nothing told
    check_signs(tmp_path, rows=[{"symbol": "VCG", "signs": {}, "details": {}}], held={"VCG"}, titles=TITLES, send=lambda text: True)
    assert check_signs(tmp_path, rows=ROWS, held={"VCG"}, titles=TITLES, send=lambda text: False)["sent"] is False
    sent = []
    assert check_signs(tmp_path, rows=ROWS, held={"VCG"}, titles=TITLES, send=lambda text: sent.append(text) or True)["new"] == 2 and sent
    assert json.loads((tmp_path / "alerts" / STATE).read_text(encoding="utf-8"))["symbols"]["VCG"] == ["other_receivables", "paper_income"]
