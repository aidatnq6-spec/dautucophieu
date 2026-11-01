from investment_agent.notifications.part_sender import PartSender


def _long(n=3):
    return "\n".join(f"dòng {i} " + "x" * 3000 for i in range(n))  # three parts


class Chat:
    def __init__(self, fail_at=()):
        self.got, self.fail_at, self.calls = [], set(fail_at), 0

    def __call__(self, part: str) -> bool:
        self.calls += 1
        if self.calls in self.fail_at:
            return False
        self.got.append(part)
        return True


def test_a_failure_after_the_first_part_keeps_the_rest_and_never_resends_what_arrived(tmp_path):
    chat = Chat(fail_at={2})
    send = PartSender(chat, tmp_path / "pending.json")
    assert send(_long()) is True  # part 1 is out: the note counts as delivered, the rest follows
    assert [p[:5] for p in chat.got] == ["(1/3)"]
    assert send("tin mới") is True
    assert [p[:5] for p in chat.got] == ["(1/3)", "(2/3)", "(3/3)", "(1/1)"]  # the rest first, in order, then the new note
    assert not (tmp_path / "pending.json").exists()


def test_a_failed_first_part_sends_nothing_and_reports_failure(tmp_path):
    chat = Chat(fail_at={1})
    send = PartSender(chat, tmp_path / "pending.json")
    assert send(_long()) is False and chat.got == []
    assert not (tmp_path / "pending.json").exists()  # the caller retries the whole note


def test_while_earlier_parts_cannot_go_out_a_new_note_waits(tmp_path):
    chat = Chat(fail_at={2, 3})
    send = PartSender(chat, tmp_path / "pending.json")
    send(_long())
    assert send("tin mới") is False  # the pending part failed again: the new note is not sent out of order
    assert [p[:5] for p in chat.got] == ["(1/3)"]
    assert PartSender(chat, tmp_path / "pending.json")("tin mới") is True  # a later run delivers both
    assert [p[:5] for p in chat.got] == ["(1/3)", "(2/3)", "(3/3)", "(1/1)"]


def test_an_unreadable_pending_file_is_set_aside(tmp_path):
    (tmp_path / "pending.json").write_text("{oops", encoding="utf-8")
    chat = Chat()
    assert PartSender(chat, tmp_path / "pending.json")("tin") is True and len(chat.got) == 1
