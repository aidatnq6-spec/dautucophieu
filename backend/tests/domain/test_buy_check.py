from datetime import datetime

from investment_agent.domain.buy_check import buy_flags, three_month_change


def closes(*pairs):
    return [(datetime(2026, m, d), float(v)) for m, d, v in pairs]


def test_three_month_change_compares_the_last_close_with_the_close_about_three_months_earlier():
    series = closes((7, 1, 20), (7, 28, 22), (8, 3, 23), (10, 30, 28.6))
    assert three_month_change(series) == {"change": "0.3000", "from": "2026-07-28"}  # last close on or before 30/10 − 92 days
    assert three_month_change(closes((10, 1, 10), (10, 30, 11))) is None             # less than three months stored


def test_flags_name_each_concern_with_its_numbers():
    flags = buy_flags(ticker={"symbol": "KDH", "weight": "0.4100", "over": True}, sector={"sector": "Bất động sản", "weight": "0.4100", "over": True},
                      limit="0.25", pyramid_warnings=[{"short": "gold", "over": ["stocks"]}], stocks_over=True,
                      momentum={"change": "0.3500", "from": "2026-07-28"}, fomo="0.30")
    assert [f["kind"] for f in flags] == ["ticker", "sector", "stocks_layer", "bottom_up", "fomo"]
    assert flags[0] == {"kind": "ticker", "symbol": "KDH", "weight": "0.4100", "limit": "0.25"}
    assert flags[-1] == {"kind": "fomo", "change": "0.3500", "from": "2026-07-28", "threshold": "0.30"}


def test_nothing_to_flag():
    assert buy_flags(ticker={"symbol": "FPT", "weight": "0.0500", "over": False}, sector=None, limit="0.25", pyramid_warnings=[],
                     stocks_over=False, momentum={"change": "0.1000", "from": "2026-07-28"}, fomo="0.30") == []
