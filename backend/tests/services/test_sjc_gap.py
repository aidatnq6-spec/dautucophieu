from datetime import date
from decimal import Decimal

from investment_agent.market.leading import MacroStore
from investment_agent.services.sjc_gap import check_sjc_gap


def test_crossing_the_owners_threshold_is_told_once_each_way(tmp_path):
    store, sent = MacroStore(tmp_path), []
    send = lambda t: sent.append(t) or True  # noqa: E731
    store.upsert("sjc_gap_pct", [(date(2026, 11, 16), "11.80")], entry="auto")
    assert check_sjc_gap(tmp_path, threshold=Decimal("12"), send=send) == {"status": "ok", "sent": 0, "above": False}
    store.upsert("sjc_gap_pct", [(date(2026, 11, 17), "13.35")], entry="auto")
    assert check_sjc_gap(tmp_path, threshold=Decimal("12"), send=send)["sent"] == 1
    assert sent[-1] == ("Chênh lệch vàng miếng SJC so với giá thế giới quy đổi lên 13,35% (17/11/2026), vượt ngưỡng 12% bạn đặt. "
                        "Xem trang Vĩ mô.")
    assert check_sjc_gap(tmp_path, threshold=Decimal("12"), send=send)["sent"] == 0  # still above: told once
    store.upsert("sjc_gap_pct", [(date(2026, 11, 18), "11.90")], entry="auto")
    assert check_sjc_gap(tmp_path, threshold=Decimal("12"), send=lambda t: False)["sent"] == 0  # not sent: tried again next run
    assert check_sjc_gap(tmp_path, threshold=Decimal("12"), send=send)["sent"] == 1
    assert sent[-1].startswith("Chênh lệch vàng miếng SJC so với giá thế giới quy đổi đã xuống 11,9% (18/11/2026), dưới ngưỡng 12%")


def test_without_a_threshold_or_a_figure_nothing_is_sent(tmp_path):
    assert check_sjc_gap(tmp_path, threshold=None, send=lambda t: True) == {"status": "skipped", "reason": "no_threshold", "sent": 0}
    assert check_sjc_gap(tmp_path, threshold=Decimal("12"), send=lambda t: True) == {"status": "skipped", "reason": "no_figure", "sent": 0}
