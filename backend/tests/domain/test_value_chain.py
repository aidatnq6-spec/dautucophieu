from datetime import date, timedelta
from decimal import Decimal

import pytest

from investment_agent.domain.value_chain import factor_status, label, read_indicator, score, weight_for_share

TODAY = date(2026, 10, 30)


def series(*pairs):
    return [(date.fromisoformat(d), Decimal(v)) for d, v in pairs]


@pytest.mark.parametrize("share, weight", [("0.0999", "small"), ("0.10", "minor"), ("0.2499", "minor"), ("0.25", "major"), ("0.35-0.40", "major"),
                                           ("0.05-0.15", "minor")])
def test_weight_follows_the_reported_share(share, weight):
    assert weight_for_share(share) == weight


def test_relative_move_over_a_month():
    r = read_indicator("wti", series(("2026-09-25", "60"), ("2026-10-28", "63.6")), today=TODAY, max_age_days=7)
    assert (r["direction"], r["change"], r["kind"], r["from"], r["date"], r["stale"]) == ("up", "0.06", "ratio", "2026-09-25", "2026-10-28", False)
    flat = read_indicator("wti", series(("2026-09-25", "60"), ("2026-10-28", "62")), today=TODAY, max_age_days=7)
    assert flat["direction"] == "flat"


def test_rates_move_in_percentage_points():
    r = read_indicator("vn_interbank_on", series(("2026-09-28", "4.5"), ("2026-10-29", "4.6")), today=TODAY, max_age_days=7)
    assert (r["direction"], r["change"], r["kind"]) == ("flat", "0.10", "points")
    r = read_indicator("vn_interbank_on", series(("2026-09-28", "4.5"), ("2026-10-29", "4.8")), today=TODAY, max_age_days=7)
    assert r["direction"] == "up"


def test_foreign_flows_read_the_sign_of_twenty_sessions():
    days = [(TODAY - timedelta(days=i)).isoformat() for i in range(25, 0, -1)]
    r = read_indicator("foreign_net", series(*[(d, "500" if i < 5 else "-100") for i, d in enumerate(days)]), today=TODAY, max_age_days=4)
    assert (r["direction"], r["change"], r["kind"]) == ("down", "-2000", "net")  # the five early buying days are outside the 20 sessions


def test_pmi_reads_its_level_against_fifty():
    assert read_indicator("vn_pmi", series(("2026-08-31", "50.5"), ("2026-09-30", "51.2")), today=TODAY, max_age_days=35)["direction"] == "up"
    assert read_indicator("vn_pmi", series(("2026-08-31", "49.5"), ("2026-09-30", "48.1")), today=TODAY, max_age_days=35)["direction"] == "down"
    assert read_indicator("vn_pmi", series(("2026-08-31", "52"), ("2026-09-30", "50.4")), today=TODAY, max_age_days=35)["direction"] == "flat"


def test_old_or_missing_series():
    assert read_indicator("wti", [], today=TODAY, max_age_days=7) is None
    assert read_indicator("wti", series(("2026-09-01", "60"), ("2026-10-10", "70")), today=TODAY, max_age_days=7)["stale"] is True
    assert read_indicator("com_coal", series(("2026-08-01", "150"), ("2026-09-01", "160")), today=TODAY, max_age_days=75)["direction"] == "up"


def test_factor_status_turns_a_direction_into_good_or_bad():
    up = {"direction": "up", "stale": False}
    assert factor_status("bad", up) == "bad" and factor_status("good", up) == "good"
    assert factor_status("bad", {"direction": "down", "stale": False}) == "good"
    assert factor_status("bad", {"direction": "flat", "stale": False}) == "neutral"
    assert factor_status("bad", None) == "unknown" and factor_status("bad", {**up, "stale": True}) == "unknown"
    assert factor_status("bad", {"direction": None, "stale": False}) == "unknown"


def test_score_weights_major_minor_small():
    s = score([("major", "good"), ("minor", "bad"), ("small", "unknown")])
    assert s == {"good": "0.5000", "bad": "0.3333", "neutral": "0.0000", "unknown": "0.1667"}


@pytest.mark.parametrize("shares, approved, expected", [
    ({"good": "0.5", "bad": "0.3", "neutral": "0", "unknown": "0.2"}, True, "tailwind"),
    ({"good": "0.2", "bad": "0.4", "neutral": "0", "unknown": "0.4"}, True, "headwind"),
    ({"good": "0.4", "bad": "0.3", "neutral": "0.3", "unknown": "0"}, True, "neutral"),
    ({"good": "0.45", "bad": "0", "neutral": "0", "unknown": "0.55"}, True, "insufficient"),
    ({"good": "0.9", "bad": "0", "neutral": "0", "unknown": "0.1"}, False, None),
])
def test_label(shares, approved, expected):
    assert label(shares, approved=approved) == expected


def test_trading_value_compares_twenty_session_averages_not_one_session():
    """One block-deal day must not flip the securities card: vnindex_value reads 20-session averages a month apart."""
    days = [TODAY - timedelta(days=i) for i in range(70, 0, -1)]
    values = ["20000"] * len(days)
    values[-1] = "40000"  # a single block-deal session doubles turnover
    r = read_indicator("vnindex_value", [(d, Decimal(v)) for d, v in zip(days, values)], today=TODAY, max_age_days=4)
    assert r["direction"] == "flat" and r["change"] == "0.05"  # (19×20,000 + 40,000)/20 = 21,000 against 20,000
