from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner


def client(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nHPG\n", encoding="utf-8")
    end = date(2027, 1, 14)
    for symbol in ("FPT", "HPG"):
        SeriesStore(tmp_path / "trend-sources").upsert(f"{symbol}-1d", [(datetime.combine(end - timedelta(days=399 - i), datetime.min.time()),
                                                                         str(50 + i * 0.01)) for i in range(400)])
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_dong_tien_lists_the_watched_tickers_with_the_held_ones_first(tmp_path):
    c, clock = client(tmp_path)
    out = call(c, clock, "GET", "/internal/watchlist/flow").json()
    assert [r["symbol"] for r in out["rows"]] == ["FPT", "HPG"] and out["rows"][0]["held"] is True
    assert out["date"] == "2027-01-14" and out["basis"] == "closes" and "new_high" in out["counts"]


def test_dinh_gia_chuoi_gives_one_row_per_chain_with_its_pe_and_pb_sides(tmp_path):
    c, clock = client(tmp_path)
    out = call(c, clock, "GET", "/internal/market/value-chains/valuation").json()
    assert out["chains"] and {"id", "name", "members", "priced", "pe", "pb", "since"} <= set(out["chains"][0])
    assert {"now", "median_5y", "position", "n"} <= set(out["chains"][0]["pe"])


def test_hieu_suat_theo_ky_gives_one_row_per_chain(tmp_path):
    c, clock = client(tmp_path)
    out = call(c, clock, "GET", "/internal/market/value-chains/returns").json()
    assert out["chains"] and {"id", "name", "periods", "breadth", "leader", "position_52w"} <= set(out["chains"][0])
    it = next((r for r in out["chains"] if "FPT" in r["no_data"] + r["stale"] or r["priced"]), None)
    assert it is not None
