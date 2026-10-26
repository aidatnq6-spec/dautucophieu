"""Vnstock adapter against a fake client shaped like the documented v5 API (no network, library not required)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.prices import PriceStore, ingest, session_series
from investment_agent.market.providers.vnstock_adapter import ProviderUnavailable, VnstockProvider, audit_symbol
from investment_agent.market.view import StoreMarket

VN = ZoneInfo("Asia/Ho_Chi_Minh")
NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
CAL = TradingCalendar(version="t", source="test", holidays=frozenset(), first=date(2016, 1, 1), last=date(2026, 12, 31))


class FakeEquity:
    def __init__(self, symbol, calls):
        self.symbol, self.calls = symbol, calls

    def ohlcv(self, start=None, end=None, interval="1D", *, source=None, floating=2, **kw):
        self.calls.append({"symbol": self.symbol, "start": start, "end": end, "interval": interval, "source": source, "floating": floating})
        days = pd.bdate_range(start, end)
        return pd.DataFrame({"time": [pd.Timestamp(d).tz_localize(VN) + pd.Timedelta(hours=7) for d in days],
                             "open": [57.9] * len(days), "high": [58.35] * len(days), "low": [57.1] * len(days),
                             "close": [57.95] * len(days), "volume": [1_200_000] * len(days)})


class FakeMarket:
    def __init__(self):
        self.calls = []

    def equity(self, symbol):
        return FakeEquity(symbol, self.calls)


class FakeStatements:
    def income_statement(self, period=None, format="long", **kw):
        rows = [{"period": p, "id": "IS_NET_REVENUE", "name": "Doanh thu thuần", "unit": "VNĐ", "value": 1_000.0}
                for p in ("2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")]
        df = pd.DataFrame(rows)
        df.attrs["symbol"] = "FPT"
        return df


class FakeFundamental:
    def equity(self, symbol):
        return FakeStatements()


def provider(market=None):
    return VnstockProvider(market=market or FakeMarket(), fundamental=FakeFundamental(), clock=lambda: NOW)


def test_prices_are_converted_from_thousand_dong_and_labelled_adjusted():
    bars = provider().fetch_prices("FPT", date(2026, 10, 19), date(2026, 10, 23))
    assert len(bars) == 5
    b = bars[0]
    assert (b.close, b.high, b.entity_id, b.session_date) == (Decimal("57950"), Decimal("58350"), "FPT", date(2026, 10, 19))
    assert b.provenance_mode == "latest_restated" and b.price_basis == "adjusted" and b.source_id == "vnstock:kbs"


def test_request_keeps_source_precision_and_uses_daily_kbs():
    market = FakeMarket()
    provider(market).fetch_prices("fpt", date(2026, 10, 19), date(2026, 10, 23))
    call = market.calls[0]
    assert (call["symbol"], call["interval"], call["source"], call["floating"]) == ("FPT", "1D", "kbs", None)
    assert (call["start"], call["end"]) == ("2026-10-19", "2026-10-23")


def test_bad_rows_are_dropped_not_zero_filled():
    class Broken(FakeEquity):
        def ohlcv(self, *a, **kw):
            df = super().ohlcv(*a, **kw)
            df.loc[1, "close"] = float("nan")
            df.loc[2, "high"] = 1.0  # high below close
            return df

    class M(FakeMarket):
        def equity(self, symbol):
            return Broken(symbol, self.calls)
    bars = provider(M()).fetch_prices("FPT", date(2026, 10, 19), date(2026, 10, 23))
    assert [b.session_date.day for b in bars] == [19, 22, 23]


def test_missing_library_is_reported_cleanly(monkeypatch):
    import builtins
    real = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "vnstock":
            raise ImportError("no vnstock")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ProviderUnavailable) as e:
        VnstockProvider(clock=lambda: NOW).fetch_prices("FPT", date(2026, 10, 19), date(2026, 10, 23))
    assert "vnstock" in str(e.value)


def test_audit_reports_depth_against_the_ten_year_requirement():
    report = audit_symbol(provider(), "FPT", today=date(2026, 10, 23), years=10)
    assert report["price_rows"] > 0 and report["first_price_date"] == "2016-10-24"
    assert report["meets_10y_prices"] is True and report["price_basis"] == "adjusted"
    assert report["financial_periods"] == 8 and report["meets_40_quarters"] is False
    assert report["line_items"] == ["IS_NET_REVENUE"] and report["publication_dates"] is False


def test_store_market_serves_latest_stored_close_with_its_date(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, provider().fetch_prices("FPT", date(2026, 10, 19), date(2026, 10, 23)), revision_id="vnstock-20261023")
    market = StoreMarket(store, CAL, today=lambda: date(2026, 10, 25))
    point = market.price("FPT")
    assert (point.price, point.session_date) == (Decimal("57950"), date(2026, 10, 23))
    assert market.provenance == "vnstock_adjusted" and market.price("VNM") is None and market.evidence("FPT") == []


def test_store_market_treats_old_prices_as_missing(tmp_path):
    store = PriceStore(tmp_path)
    ingest(store, CAL, provider().fetch_prices("FPT", date(2026, 10, 19), date(2026, 10, 23)), revision_id="r1")
    assert StoreMarket(store, CAL, today=lambda: date(2026, 11, 20), max_age_days=10).price("FPT") is None


def test_cli_market_sync_loads_only_calendar_sessions(tmp_path):
    import json as _json
    from investment_agent.cli import market_sync
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(_json.dumps({"version": "x", "source": "HOSE notice", "holidays": ["2026-10-21"], "first": "2026-01-01",
                                     "last": "2026-12-31"}), encoding="utf-8")
    assert market_sync(["fpt"], tmp_path, cal_path, 7, provider=provider(), today=date(2026, 10, 23)) == 0
    days = [r.session_date.day for r in session_series(PriceStore(tmp_path), CAL, "FPT", date(2026, 10, 16), date(2026, 10, 23)) if r.status == "traded"]
    assert days == [16, 19, 20, 22, 23]  # holiday 21/10 dropped


def test_cli_audit_writes_report(tmp_path):
    import json as _json
    from investment_agent.cli import vnstock_audit
    assert vnstock_audit(["FPT", "VCB"], tmp_path, provider=provider(), today=date(2026, 10, 23)) == 0
    rows = _json.loads((tmp_path / "vnstock-audit.json").read_text(encoding="utf-8"))
    assert [r["symbol"] for r in rows] == ["FPT", "VCB"] and rows[0]["meets_40_quarters"] is False


class RestatedEquity(FakeEquity):
    def ohlcv(self, *a, **kw):
        df = super().ohlcv(*a, **kw)
        df.loc[df.index[-1], "close"] = 58.3
        return df


class RestatedMarket(FakeMarket):
    def equity(self, symbol):
        return RestatedEquity(symbol, self.calls)


def _sync_twice(tmp_path, second_market):
    import json as _json
    from investment_agent.cli import market_sync
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(_json.dumps({"version": "x", "source": "test", "holidays": [], "first": "2026-01-01", "last": "2026-12-31"}),
                        encoding="utf-8")
    first = market_sync(["FPT"], tmp_path, cal_path, 7, provider=provider(), today=date(2026, 10, 23))
    later = VnstockProvider(market=second_market, fundamental=FakeFundamental(), clock=lambda: NOW + timedelta(hours=2))
    return first, market_sync(["FPT"], tmp_path, cal_path, 7, provider=later, today=date(2026, 10, 23))


def test_same_day_rerun_with_unchanged_prices_is_a_no_op(tmp_path):
    assert _sync_twice(tmp_path, FakeMarket()) == (0, 0)
    assert len(PriceStore(tmp_path).revisions("FPT")) == 1


def test_same_day_rerun_with_restated_prices_adds_a_revision(tmp_path):
    assert _sync_twice(tmp_path, RestatedMarket()) == (0, 0)
    store = PriceStore(tmp_path)
    assert len(store.revisions("FPT")) == 2
    assert store.latest("FPT")[date(2026, 10, 23)][0].close == Decimal("58300")


class FakeListing:
    def symbols_by_group(self, group):
        return pd.Series({"VN30": ["FPT", "VCB"], "VN100": ["FPT", "VCB", "KDH"]}[group])


def test_cli_index_groups_writes_members_with_date_and_source(tmp_path):
    import json as _json
    from investment_agent.cli import index_groups
    p = VnstockProvider(market=FakeMarket(), fundamental=FakeFundamental(), listing=FakeListing(), clock=lambda: NOW)
    assert index_groups(["VN30", "VN100"], tmp_path / "index-groups.json", provider=p, today=date(2026, 10, 25)) == 0
    saved = _json.loads((tmp_path / "index-groups.json").read_text(encoding="utf-8"))
    assert saved == {"as_of": "2026-10-25", "source": "vnstock:kbs", "groups": {"VN30": ["FPT", "VCB"], "VN100": ["FPT", "KDH", "VCB"]}}


class FakeIndex:
    def __init__(self, calls):
        self.calls = calls

    def ohlcv(self, start=None, end=None, interval="1D", **kw):
        self.calls.append({"start": start, "end": end})
        return pd.DataFrame({"time": [pd.Timestamp("2026-10-23").tz_localize(VN) + pd.Timedelta(hours=7)], "open": [1761.38],
                             "high": [1775.19], "low": [1750.83], "close": [1774.15], "volume": [777_197_613]})


class IndexMarket(FakeMarket):
    def index(self, symbol):
        return FakeIndex(self.calls)


class IndustryListing(FakeListing):
    def symbols_by_industries(self, source=None):
        assert source == "vci"
        return pd.DataFrame([{"symbol": "MBB", "icb_level": 1, "icb_name": "Ngân hàng"}, {"symbol": "MBB", "icb_level": 2, "icb_name": "Ngân hàng"},
                             {"symbol": "SSI", "icb_level": 2, "icb_name": "Dịch vụ tài chính"}, {"symbol": "", "icb_level": 2, "icb_name": "Quỹ"}])


def test_index_prices_stay_in_points():
    p = VnstockProvider(market=IndexMarket(), fundamental=FakeFundamental(), clock=lambda: NOW)
    [bar] = p.fetch_index("vnindex", date(2026, 10, 23), date(2026, 10, 23))
    assert (bar.entity_id, bar.close, bar.currency, bar.price_basis) == ("VNINDEX", Decimal("1774.15"), "POINT", "raw")


def test_cli_market_sync_loads_an_index(tmp_path):
    import json as _json
    from investment_agent.cli import market_sync
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(_json.dumps({"version": "x", "source": "t", "holidays": [], "first": "2026-01-01", "last": "2026-12-31"}), encoding="utf-8")
    p = VnstockProvider(market=IndexMarket(), fundamental=FakeFundamental(), clock=lambda: NOW)
    assert market_sync(["VNINDEX"], tmp_path, cal_path, 7, provider=p, today=date(2026, 10, 23), index=True) == 0
    assert PriceStore(tmp_path).latest("VNINDEX")[date(2026, 10, 23)][0].close == Decimal("1774.15")


def test_cli_industries_saves_level_two_sectors_for_watched_tickers(tmp_path):
    import json as _json
    from investment_agent.cli import industries
    p = VnstockProvider(market=FakeMarket(), fundamental=FakeFundamental(), listing=IndustryListing(), clock=lambda: NOW)
    assert industries(["MBB", "SSI", "XYZ"], tmp_path / "industries.json", provider=p, today=date(2026, 10, 25)) == 0
    saved = _json.loads((tmp_path / "industries.json").read_text(encoding="utf-8"))
    assert saved == {"as_of": "2026-10-25", "source": "vnstock:vci", "level": 2, "sectors": {"MBB": "Ngân hàng", "SSI": "Dịch vụ tài chính"}}


class PreOpenIndex:
    """Vnstock's daily index rows on 26/10/2026 before the open: a zero-volume placeholder for today,
    and (as on the 07:11 run) the same session twice."""
    def __init__(self, calls):
        self.calls = calls

    def ohlcv(self, start=None, end=None, interval="1D", **kw):
        t = lambda d: pd.Timestamp(d).tz_localize(VN) + pd.Timedelta(hours=7)  # noqa: E731
        return pd.DataFrame({"time": [t("2026-10-23"), t("2026-10-23"), t("2026-10-26")],
                             "open": [1761.38, 1757.6, 1774.15], "high": [1775.19, 1775.19, 1774.15], "low": [1750.83, 1750.83, 1774.15],
                             "close": [1774.15, 1774.15, 1774.15], "volume": [777197613, 640986900, 0]})


class PreOpenMarket(FakeMarket):
    def index(self, symbol):
        return PreOpenIndex(self.calls)

    def equity(self, symbol):
        return PreOpenIndex(self.calls)


def test_preopen_placeholders_are_dropped_and_a_repeated_session_keeps_the_last_row():
    p = VnstockProvider(market=PreOpenMarket(), fundamental=FakeFundamental(), clock=lambda: NOW)
    bars = p.fetch_index("VNINDEX", date(2026, 10, 23), date(2026, 10, 26))
    assert [(b.session_date, b.volume) for b in bars] == [(date(2026, 10, 23), 640986900)]
    closes = p.fetch_closes("VNINDEX", date(2026, 10, 23), date(2026, 10, 26), interval="1D", index=True)
    assert [t.date() for t, _ in closes] == [date(2026, 10, 23)]


def test_market_sync_survives_a_repeated_session_from_the_source(tmp_path):
    import json as _json
    from investment_agent.cli import market_sync
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(_json.dumps({"version": "x", "source": "t", "holidays": [], "first": "2026-01-01", "last": "2026-12-31"}), encoding="utf-8")
    p = VnstockProvider(market=PreOpenMarket(), fundamental=FakeFundamental(), clock=lambda: NOW)
    assert market_sync(["VNINDEX"], tmp_path, cal_path, 7, provider=p, today=date(2026, 10, 26), index=True) == 0
    assert sorted(PriceStore(tmp_path).latest("VNINDEX")) == [date(2026, 10, 23)]
