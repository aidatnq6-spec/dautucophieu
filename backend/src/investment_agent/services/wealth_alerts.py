"""Việc tài chính hôm nay (owner, 21/11/2026): the personal reminders of one run go out as one Telegram note instead of one each.

Each part (Sổ tiết kiệm, khoản vay and bảo hiểm and cho thuê, Tháp tài sản, Góp vốn đều, Kế hoạch tích sản) keeps its own rule and marks
itself reminded as before; here it is handed a collector instead of Telegram. The collected texts are sent once. A note that could not
go out is queued at the head of the Telegram queue (PartSender.queue) and goes first next time, so a reminder already marked is
delivered later, never lost and never sent twice. One part failing never stops the others. Personal data; never sent to a model."""

from collections.abc import Callable
from datetime import date

Run = Callable[[Callable[[str], bool]], dict]


def wealth_alerts_run(runs: list[tuple[str, Run]], *, send, today: date) -> dict:
    """runs: (name, run) where run(send) calls one part with that send; send: a PartSender (it has queue())."""
    texts, out = [], {}

    def collect(text: str) -> bool:
        texts.append(text.strip())
        return True
    for name, run in runs:
        try:
            out[name] = run(collect)
        except Exception as exc:  # one part's book unreadable: the others still go out
            out[name] = {"error": type(exc).__name__}
    if not texts:
        return {"parts": 0, "sent": False, "queued": False, "runs": out}
    note = "\n\n".join([f"Việc tài chính hôm nay {today:%d/%m/%Y}", *texts])
    sent = bool(send(note))
    if not sent:
        send.queue(note)
    return {"parts": len(texts), "sent": sent, "queued": not sent, "runs": out}
