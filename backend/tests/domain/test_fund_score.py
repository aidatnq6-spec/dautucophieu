from datetime import date, timedelta

from investment_agent.domain.fund_score import RISK_MIN_DAYS, fund_scores, history_risk, score_trend


def prof(kind, m12, m36, fee):
    return {"kind": kind, "manager": None, "fee": fee, "returns": {"ytd": None, "m1": None, "m3": None, "m6": None, "m12": m12, "m36": m36, "m60": None,
                                                                  "annual36": None}}


PROFILES = {"A": prof("STOCK", "20", "50", "1"), "B": prof("STOCK", "10", "30", "2"), "C": prof("STOCK", "0", None, "1.5"), "D": prof("BOND", "6", None, None)}


def test_each_measure_is_a_percentile_within_the_kind_and_the_score_their_mean():
    out = fund_scores(PROFILES, {})
    a, b, c = out["A"], out["B"], out["C"]
    assert a["parts"] == {"returns": "100", "fee": "100", "risk": None} and a["score"] == "100"
    assert b["parts"] == {"returns": "25", "fee": "0", "risk": None} and b["score"] == "12.5"  # 1 year 50, 3 years 0
    assert c["parts"]["returns"] == "0" and c["parts"]["fee"] == "50" and c["score"] == "25"  # no 3-year figure: only its 1 year counts
    assert a["risk_days"] == 0 and a["counted"] == ["returns", "fee"]
    assert out["D"] == {"score": None, "parts": {"returns": None, "fee": None, "risk": None}, "counted": [], "risk_days": 0, "peers": 1}  # alone


def test_risk_counts_once_the_nav_history_is_long_enough():
    start = date(2026, 1, 1)
    steady = {(start + timedelta(days=i)).isoformat(): str(100 + i * 0.1) for i in range(RISK_MIN_DAYS)}
    bumpy = {(start + timedelta(days=i)).isoformat(): str(100 + (10 if i % 2 else -10)) for i in range(RISK_MIN_DAYS)}
    assert history_risk(steady)["drawdown"] == "0" and history_risk({"2026-01-01": "1"}) is None
    out = fund_scores({"A": PROFILES["A"], "B": PROFILES["B"]}, {"A": bumpy, "B": steady})
    assert out["A"]["parts"]["risk"] == "0" and out["B"]["parts"]["risk"] == "100" and "risk" in out["B"]["counted"]


def test_the_trend_compares_with_the_month_before():
    snaps = {"2026-10": {"A": "60", "B": "40"}, "2026-11": {"A": "70", "B": "40", "C": "10"}}
    assert score_trend(snaps, "2026-11") == {"A": {"previous": "60", "change": "10"}, "B": {"previous": "40", "change": "0"}, "C": None}


def test_the_month_s_scores_are_kept_and_read_back(tmp_path):
    from investment_agent.domain.fund_score import read_snapshots, record_scores
    record_scores(tmp_path, "2026-10", {"A": {"score": "60"}, "B": {"score": None}})
    record_scores(tmp_path, "2026-11", {"A": {"score": "70"}})
    record_scores(tmp_path, "2026-11", {"A": {"score": "72"}})  # later the same month: replaces it
    assert read_snapshots(tmp_path) == {"2026-10": {"A": "60"}, "2026-11": {"A": "72"}}
