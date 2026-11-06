import json
from datetime import date

from investment_agent.domain.deposit_book import DepositBook
from investment_agent.services.deposit_alerts import deposit_alerts_run


def sổ(id, matures, principal="50000000", interest="2000000", payout="end", locked=True, bank=None):
    return {"id": id, "bank": bank or f"Ngân hàng {id.upper()}", "matures": matures, "principal": principal, "rate": "6",
            "interest": interest, "payout": payout, "locked": locked}


def book(*deposits):
    return DepositBook.model_validate({"deposits": list(deposits)})


def run(tmp_path, b, today, ok=True):
    texts = []
    out = deposit_alerts_run(tmp_path, book=b, today=today, send=lambda t: texts.append(t) or ok)
    return out, texts


def test_a_deposit_is_reminded_once_from_the_day_before_it_matures(tmp_path):
    b = book(sổ("a", "2026-12-05"), sổ("b", "2027-03-06"))
    assert run(tmp_path, b, date(2026, 12, 3)) == ({"alerts": 0, "sent": False}, [])  # two days before: not yet
    out, texts = run(tmp_path, b, date(2026, 12, 4))
    assert out == {"alerts": 1, "sent": True}
    assert texts == ["Sổ tiết kiệm đến hạn\n"
                     "• Ngân hàng A · đến hạn ngày mai 05/12/2026 · gốc 50.000.000 đ · lãi khi đáo hạn 2.000.000 đ · phong tỏa\n"
                     "Phần mềm không tự tái tục hay tất toán. Xử lý xong, sửa ngày đáo hạn hoặc xóa sổ ở Sổ tài sản. Không phải khuyến nghị."]
    assert run(tmp_path, b, date(2026, 12, 4)) == ({"alerts": 0, "sent": False}, [])  # once only, also on the day itself
    assert run(tmp_path, b, date(2026, 12, 5)) == ({"alerts": 0, "sent": False}, [])
    state = json.loads((tmp_path / "alerts" / "deposits.json").read_text(encoding="utf-8"))
    assert state == {"a": "2026-12-05"}  # ids and dates only, no amounts


def test_a_missed_day_is_caught_up_within_seven_days_and_never_later(tmp_path):
    b = book(sổ("a", "2026-12-05", interest=None), sổ("b", "2026-12-06", payout="upfront", interest=None, locked=False),
             sổ("c", "2026-11-28"), sổ("d", "2026-11-29"))
    out, texts = run(tmp_path, b, date(2026, 12, 6))
    assert out == {"alerts": 3, "sent": True}
    lines = texts[0].split("\n")[1:-1]
    assert lines == ["• Ngân hàng D · đã đến hạn 29/11/2026 (7 ngày trước) · gốc 50.000.000 đ · lãi khi đáo hạn 2.000.000 đ · phong tỏa",
                     "• Ngân hàng A · đã đến hạn 05/12/2026 (1 ngày trước) · gốc 50.000.000 đ · lãi chưa nhập · phong tỏa",
                     "• Ngân hàng B · đến hạn hôm nay 06/12/2026 · gốc 50.000.000 đ · lãi đầu kỳ, đã nhận"]  # c is 8 days past: left to the page


def test_a_failed_send_is_retried_and_a_new_date_is_reminded_again(tmp_path):
    b = book(sổ("a", "2026-12-05"))
    assert run(tmp_path, b, date(2026, 12, 4), ok=False)[0] == {"alerts": 1, "sent": False}
    assert run(tmp_path, b, date(2026, 12, 4))[0] == {"alerts": 1, "sent": True}
    rolled = book(sổ("a", "2027-03-05"))  # tái tục: the owner moved the date
    assert run(tmp_path, rolled, date(2027, 3, 4))[0] == {"alerts": 1, "sent": True}
    assert json.loads((tmp_path / "alerts" / "deposits.json").read_text(encoding="utf-8")) == {"a": "2027-03-05"}


def test_no_book_or_a_deleted_row_sends_nothing_and_drops_its_mark(tmp_path):
    assert run(tmp_path, None, date(2026, 12, 4)) == ({"alerts": 0, "sent": False}, [])
    run(tmp_path, book(sổ("a", "2026-12-05")), date(2026, 12, 4))
    assert run(tmp_path, book(), date(2026, 12, 5)) == ({"alerts": 0, "sent": False}, [])
    assert json.loads((tmp_path / "alerts" / "deposits.json").read_text(encoding="utf-8")) == {}
