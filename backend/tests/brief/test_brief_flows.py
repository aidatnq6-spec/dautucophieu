import json
from datetime import date, timedelta

from investment_agent.brief.flows import net_flows


def write(root, folder, day, record):
    (root / folder).mkdir(parents=True, exist_ok=True)
    (root / folder / f"{day}.json").write_text(json.dumps({"date": day, **record}), encoding="utf-8")


def foreign(root, day, *nets):
    write(root, "foreign", day, {"stocks": {f"M{i}": {"buy_volume": "1", "sell_volume": "1", "buy_value": str(max(n, 0)), "sell_value": str(max(-n, 0))}
                                            for i, n in enumerate(nets)}})


def proprietary(root, day, buy, sell):
    write(root, "proprietary", day, {"index": {"buy_volume": "1", "sell_volume": "1", "buy_value": str(buy), "sell_value": str(sell)}, "stocks": {}})


def weekdays(last: date, n: int) -> list[date]:
    out, d = [], last
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return sorted(out)


B = 10**9
SESSIONS = weekdays(date(2026, 11, 26), 25)


def test_foreign_net_is_the_sum_of_the_stocks_over_twenty_sessions_ending_at_the_brief_session(tmp_path):
    for d in SESSIONS:
        foreign(tmp_path, d.isoformat(), 3 * B, -1 * B)  # +2 tỷ a session
    foreign(tmp_path, "2026-11-26", -237 * B)
    f = net_flows(tmp_path, date(2026, 11, 26), SESSIONS)["foreign"]
    assert f["status"] == "ok" and f["date"] == "2026-11-26" and f["lag_sessions"] == 0 and f["net_bn"] == "-237.00"
    assert len(f["bars"]) == 20 and f["bars"][0]["date"] == SESSIONS[-20].isoformat() and f["bars"][-1] == {"date": "2026-11-26", "net_bn": "-237.00"}
    assert f["sum_bn"] == "-199.00" and f["missing"] == 0  # 19 × 2 − 237


def test_proprietary_ends_at_vndirects_newest_session_with_its_lag_and_missing_sessions_left_blank(tmp_path):
    for d in SESSIONS[:-3]:
        proprietary(tmp_path, d.isoformat(), 5 * B, 4 * B)
    write(tmp_path, "proprietary", SESSIONS[-5].isoformat(), {"thieu": True})
    p = net_flows(tmp_path, date(2026, 11, 26), SESSIONS)["proprietary"]
    assert p["date"] == SESSIONS[-4].isoformat() and p["lag_sessions"] == 3 and p["net_bn"] == "1.00"
    assert p["bars"][-1]["date"] == SESSIONS[-4].isoformat() and p["bars"][-2]["net_bn"] is None and p["missing"] == 1
    assert p["sum_bn"] == "19.00"


def test_an_empty_store_says_so_and_the_other_flow_still_shows(tmp_path):
    foreign(tmp_path, "2026-11-26", 1 * B)
    out = net_flows(tmp_path, date(2026, 11, 26), SESSIONS)
    assert out["foreign"]["status"] == "ok" and out["proprietary"]["status"] == "missing" and out["proprietary"]["reason"]


def test_a_session_after_the_brief_is_never_used(tmp_path):
    foreign(tmp_path, "2026-11-26", 1 * B)
    foreign(tmp_path, "2026-11-27", 9 * B)
    assert net_flows(tmp_path, date(2026, 11, 26), SESSIONS)["foreign"]["net_bn"] == "1.00"


def test_the_brief_view_carries_both_rows_and_a_broken_store_only_blanks_them(tmp_path, monkeypatch):
    from investment_agent.brief.view import market_for_session
    (tmp_path / "brief").mkdir()
    (tmp_path / "brief" / "2026-11-26.json").write_text(json.dumps({"session_date": "2026-11-26", "board": {"status": "ok"}}), encoding="utf-8")
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    foreign(tmp_path, "2026-11-26", -237 * B)
    view = market_for_session(tmp_path, set())("2026-11-26")
    assert view["flows"]["foreign"]["net_bn"] == "-237.00" and len(view["flows"]["foreign"]["bars"]) == 20
    import investment_agent.brief.flows as flows
    monkeypatch.setattr(flows, "net_flows", lambda *a, **k: 1 / 0)
    broken = market_for_session(tmp_path, set())("2026-11-26")
    assert broken is not None and broken["flows"]["foreign"]["status"] == "missing"


def test_the_lag_counts_the_brief_session_even_when_the_calendar_has_not_got_it(tmp_path):
    foreign(tmp_path, "2026-11-25", 1 * B)
    f = net_flows(tmp_path, date(2026, 11, 26), [d for d in SESSIONS if d != date(2026, 11, 26)])["foreign"]
    assert f["date"] == "2026-11-25" and f["lag_sessions"] == 1


def test_one_damaged_file_blanks_its_own_session_only(tmp_path):
    foreign(tmp_path, "2026-11-25", 1 * B)
    write(tmp_path, "foreign", "2026-11-26", {"stocks": {"FPT": {"buy_value": None, "sell_value": "1"}}})
    proprietary(tmp_path, "2026-11-26", 2 * B, 1 * B)
    out = net_flows(tmp_path, date(2026, 11, 26), SESSIONS)
    assert out["foreign"]["date"] == "2026-11-25" and out["foreign"]["bars"][-1]["net_bn"] == "1.00"
    assert out["proprietary"]["net_bn"] == "1.00"
