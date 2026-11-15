from datetime import date

import pytest

from investment_agent.domain.macro_extras import EventError, events_view, rate_spread, validate_events


def test_the_spread_is_the_vnd_overnight_rate_less_the_usd_one_known_on_that_day():
    vn = [(date(2026, 11, 10), "4.10"), (date(2026, 11, 11), "3.80"), (date(2026, 11, 12), "4.00"), (date(2026, 11, 13), "4.20")]
    sofr = [(date(2026, 11, 10), "3.89"), (date(2026, 11, 12), "3.90")]  # no SOFR on 11/11: the 10/11 one still stands
    effr = [(date(2026, 11, 13), "3.85")]
    out = rate_spread(vn, sofr=sofr, effr=effr)
    assert [(p["date"], p["spread"], p["usd_source"]) for p in out["points"]] == [
        ("2026-11-10", "0.21", "SOFR"), ("2026-11-11", "-0.09", "SOFR"), ("2026-11-12", "0.1", "SOFR"), ("2026-11-13", "0.3", "SOFR")]
    assert out["latest"] == {"date": "2026-11-13", "vnd": "4.2", "usd": "3.9", "usd_source": "SOFR", "spread": "0.3"}
    assert out["negative_days"] == 1 and out["days"] == 4


def test_without_sofr_the_fed_rate_stands_in_and_old_usd_figures_are_not_used():
    out = rate_spread([(date(2026, 11, 13), "4.2")], sofr=[(date(2026, 10, 1), "4.0")], effr=[(date(2026, 11, 12), "3.85")])
    assert out["latest"]["usd_source"] == "EFFR" and out["latest"]["spread"] == "0.35"
    assert rate_spread([(date(2026, 11, 13), "4.2")], sofr=[(date(2026, 10, 1), "4.0")], effr=[])["points"] == []  # 6 weeks old: no figure


def test_events_need_a_day_and_a_title_and_are_split_into_coming_and_past():
    ev = validate_events([{"id": "a", "date": "2026-12-09", "title": "Fed họp", "kind": "fed", "note": "", "source": "federalreserve.gov", "remind": True},
                          {"id": "b", "date": "2026-11-09", "title": "NHNN hoán đổi 2 tỷ USD, 6 tháng", "kind": "sbv", "note": "24.399 / 24.704", "source": "NHNN"}])
    assert [e["id"] for e in ev] == ["b", "a"] and ev[0]["remind"] is False and ev[1]["kind"] == "fed"
    v = events_view(ev, today=date(2026, 12, 8))
    assert [e["id"] for e in v["coming"]] == ["a"] and v["coming"][0]["days"] == 1 and [e["id"] for e in v["past"]] == ["b"]
    for bad in ({"date": "09/12/2026"}, {"title": " "}, {"kind": "guess"}):
        with pytest.raises(EventError):
            validate_events([{"id": "x", "date": "2026-12-09", "title": "t", "kind": "fed", **bad}])
