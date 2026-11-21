"""Việc tài chính hôm nay (owner, 21/11/2026): the personal reminders of one run (deposits, loans and insurance, Tháp tài sản,
contributions, accumulation) go out as one Telegram note. Each part keeps its own rule and marks itself reminded as before; a note that
could not go out waits at the head of the queue and goes first next time, so nothing is lost or sent twice."""

import json
from datetime import date

from investment_agent.notifications.part_sender import PartSender
from investment_agent.notifications.render import split_message
from investment_agent.services.wealth_alerts import wealth_alerts_run

TODAY = date(2026, 11, 21)


def part(name, text):
    def run(send):
        return {"sent": send(text)} if text else {"sent": False}
    return name, run


def sender(tmp_path, ok=True, log=None):
    log = [] if log is None else log
    return PartSender(lambda p: log.append(p) or ok, tmp_path / "alerts" / "telegram_pending.json"), log


def test_the_parts_of_one_run_go_out_as_one_note(tmp_path):
    send, log = sender(tmp_path)
    out = wealth_alerts_run([part("deposits", "Sổ tiết kiệm đến hạn\n• A"), part("tower", None), part("loans", "Khoản vay\n• B")],
                            send=send, today=TODAY)
    assert out == {"parts": 2, "sent": True, "queued": False, "runs": {"deposits": {"sent": True}, "tower": {"sent": False}, "loans": {"sent": True}}}
    assert log == split_message("Việc tài chính hôm nay 21/11/2026\n\nSổ tiết kiệm đến hạn\n• A\n\nKhoản vay\n• B")


def test_nothing_to_say_sends_nothing(tmp_path):
    send, log = sender(tmp_path)
    out = wealth_alerts_run([part("deposits", None)], send=send, today=TODAY)
    assert out["parts"] == 0 and out["sent"] is False and log == []


def test_a_note_that_could_not_go_out_waits_and_goes_first_next_time(tmp_path):
    send, log = sender(tmp_path, ok=False)
    out = wealth_alerts_run([part("deposits", "Sổ tiết kiệm đến hạn\n• A")], send=send, today=TODAY)
    assert out["sent"] is False and out["queued"] is True
    note = "Việc tài chính hôm nay 21/11/2026\n\nSổ tiết kiệm đến hạn\n• A"
    assert json.loads((tmp_path / "alerts" / "telegram_pending.json").read_text(encoding="utf-8")) == split_message(note)
    later, log2 = sender(tmp_path)
    assert later("Tin khác")
    assert log2 == [*split_message(note), *split_message("Tin khác")]


def test_one_part_failing_never_stops_the_others(tmp_path):
    send, log = sender(tmp_path)

    def broken(send):
        raise RuntimeError("book unreadable")
    out = wealth_alerts_run([("deposits", broken), part("loans", "Khoản vay\n• B")], send=send, today=TODAY)
    assert out["runs"]["deposits"] == {"error": "RuntimeError"} and out["sent"] is True and "Khoản vay" in log[0]
