import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from investment_agent.cli import brief_snapshot_cli
from investment_agent.market.series import SeriesStore

VN = ZoneInfo("Asia/Ho_Chi_Minh")
CAL = {"version": "t", "source": "https://www.hsx.vn/x", "holidays": [], "first": "2026-01-01", "last": "2026-12-31"}
BOARD = [{"symbol": "FPT", "trading_date": "2026-10-26", "ref_price": 57000, "match_price": 56000, "accumulated_value": 1000.0,
          "accumulated_volume": 10, "foreign_buy_volume": 0, "foreign_sell_volume": 0, "foreign_buy_value": 0, "foreign_sell_value": 0,
          "icb_code2": "9500"}]


def test_cli_writes_the_session_snapshot_and_caches_the_listing(tmp_path, capsys):
    (tmp_path / "cal.json").write_text(json.dumps(CAL), encoding="utf-8")
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(datetime(2026, 10, 23), "1658.52"), (datetime(2026, 10, 26), "1650.12")])
    calls = []
    listing = lambda: calls.append(1) or {"symbols": ["FPT"], "icb_names": {"9500": "Công nghệ Thông tin"}, "icb_codes": {"FPT": "9500"}}
    run = lambda: brief_snapshot_cli(tmp_path, tmp_path / "cal.json", listing=listing, board=lambda s: BOARD,
                                     http_get=lambda url: json.dumps({"data": []}) if "hsx" in url else "<rss></rss>",
                                     now=datetime(2026, 10, 26, 15, 40, tzinfo=VN))
    assert run() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["session"] == "2026-10-26" and out["sections"]["board"] == "ok" and out["sections"]["indices"] == "ok"
    assert (tmp_path / "brief" / "2026-10-26.json").is_file()
    run()
    assert len(calls) == 1  # HOSE listing cached for a week


def test_cli_reads_the_vn_index_bars_from_the_price_store_for_the_session_shape(tmp_path, capsys):
    from investment_agent.market.prices import PriceBar, PriceStore
    (tmp_path / "cal.json").write_text(json.dumps(CAL), encoding="utf-8")
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(datetime(2026, 10, 23), "1658.52"), (datetime(2026, 10, 26), "1650.12")])
    at = datetime(2026, 10, 26, 16, 0, tzinfo=VN)
    mk = lambda d, h, l, c: PriceBar(entity_id="VNINDEX", session_date=d, open=c, high=h, low=l, close=c, volume=100, currency="POINT",
                                     source_id="vnstock:kbs", observed_at=at, provenance_mode="historical_as_reported")
    PriceStore(tmp_path).write_revision("VNINDEX", "r1", [mk(date(2026, 10, 23), "1660", "1650", "1658.52"), mk(date(2026, 10, 26), "1660", "1640", "1650.12")])
    assert brief_snapshot_cli(tmp_path, tmp_path / "cal.json", listing=lambda: {"symbols": ["FPT"], "icb_names": {}, "icb_codes": {}},
                              board=lambda s: BOARD, http_get=lambda url: json.dumps({"data": []}) if "hsx" in url else "<rss></rss>",
                              now=datetime(2026, 10, 26, 15, 40, tzinfo=VN)) == 0
    snap = json.loads((tmp_path / "brief" / "2026-10-26.json").read_text(encoding="utf-8"))
    assert snap["index_session"]["range"] == {"high": "1660.00", "low": "1640.00", "close": "1650.12", "from_high": "9.88", "from_low": "10.12"}
    assert snap["index_session"]["streak"]["direction"] == "down"
