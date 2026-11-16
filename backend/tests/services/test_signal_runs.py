from datetime import date, timedelta

from investment_agent.brief.snapshot import BriefStore
from investment_agent.services.signal_runs import RUNS, check_runs


def write(tmp_path, days, *, low=True, gap="green_over_red", asia_against=False):
    store = BriefStore(tmp_path)
    for d in days:
        store.write({"session_date": d.isoformat(), "signals": {
            "status": "ok", "breadth_gap": {"kind": gap, "up": 100, "down": 220} if gap else None,
            "liquidity": {"ratio20": "0.69", "change_pct": None, "low": low, "below_avg_sessions": 1}, "pull": {"status": "missing"},
            "asia": {"index": "up", "up": 0, "down": 3, "counted": 3, "left_out": []} if asia_against else None}})


SESSIONS = [date(2026, 11, 16) + timedelta(days=i) for i in range(5)]  # Mon–Fri


def test_a_run_reaching_its_length_is_told_once(tmp_path):
    assert RUNS == {"low_liquidity": 5, "green_over_red": 3, "red_over_green": 3, "asia_against": 3}
    sent = []
    write(tmp_path, SESSIONS[:2])
    assert check_runs(tmp_path, send=lambda t: sent.append(t) or True)["sent"] == 0  # two sessions: not yet
    write(tmp_path, SESSIONS[2:3])
    assert check_runs(tmp_path, send=lambda t: sent.append(t) or True)["sent"] == 1
    assert sent[-1] == ("Tín hiệu phiên kéo dài: xanh vỏ đỏ lòng 3 phiên liền (16/11–18/11): VN-Index tăng nhưng số mã giảm áp đảo số mã tăng. "
                        "Xem Bản tin sau phiên.")
    assert check_runs(tmp_path, send=lambda t: sent.append(t) or True)["sent"] == 0  # told once
    write(tmp_path, SESSIONS[3:5])
    check_runs(tmp_path, send=lambda t: sent.append(t) or True)
    assert sent[-1].startswith("Tín hiệu phiên kéo dài: thanh khoản thấp 5 phiên liền (16/11–20/11)")
    assert sum("xanh vỏ đỏ lòng" in t for t in sent) == 1  # the same run, longer, is not told again


def test_a_note_not_sent_waits_and_a_new_run_is_told_again(tmp_path):
    write(tmp_path, SESSIONS[:3], low=False)
    assert check_runs(tmp_path, send=lambda t: False)["sent"] == 0
    sent = []
    assert check_runs(tmp_path, send=lambda t: sent.append(t) or True)["sent"] == 1
    write(tmp_path, [date(2026, 11, 23)], low=False, gap=None)  # the run ends
    write(tmp_path, [date(2026, 11, 24) + timedelta(days=i) for i in range(3)], low=False)  # a new run of three
    assert check_runs(tmp_path, send=lambda t: sent.append(t) or True)["sent"] == 1 and "(24/11–26/11)" in sent[-1]
