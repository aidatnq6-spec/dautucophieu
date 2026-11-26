"""MCP dữ liệu công khai: synthetic files only; the server reads data/ and nothing personal."""

import ast
import json
from datetime import date, datetime, timezone
from pathlib import Path

import anyio
import pytest

from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.prices import PriceBar, PriceStore, ingest
from investment_agent.public_tools import PublicData

SRC = Path(__file__).resolve().parents[1] / "src" / "investment_agent"
CAL = TradingCalendar(version="cal-test", source="synthetic", holidays=frozenset(), first=date(2026, 8, 3), last=date(2026, 12, 31))
OBSERVED = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def bar(entity, day, price):
    return PriceBar.model_validate({"entity_id": entity, "session_date": day, "open": str(price), "high": str(price + 100),
                                    "low": str(price - 100), "close": str(price), "volume": 1000, "currency": "POINT" if entity == "VNINDEX" else "VND",
                                    "source_id": "fixture", "observed_at": OBSERVED.isoformat(), "provenance_mode": "synthetic"})


@pytest.fixture
def data(tmp_path):
    write(tmp_path / "hose-listing.json", {"at": "2026-11-24T13:00:00+00:00", "listing": {"symbols": ["AAA", "BBB"]}})
    write(tmp_path / "industries.json", {"as_of": "2026-11-25", "source": "vndirect:finfo", "sectors": {"AAA": "Ngân hàng"}})
    write(tmp_path / "index-groups.json", {"as_of": "2026-11-23", "source": "vndirect:finfo", "groups": {"VN30": ["AAA"], "VN100": ["AAA", "BBB"]}})
    write(tmp_path / "statements" / "BBB.json", {"symbol": "BBB", "fetched_at": "2026-11-20T00:00:00+00:00", "source": "vndirect:finfo",
                                                 "quarters": {f"2026-Q{i}": {"cash": str(i)} for i in (1, 2, 3)},
                                                 "years": {"2024": {"cash": "7"}, "2025": {"cash": "8"}}})
    write(tmp_path / "statements-financial" / "AAA.json", {"symbol": "AAA", "fetched_at": "x", "source": "vndirect:finfo", "kind": "bank",
                                                           "quarters": {"2026-Q3": {"loans": "9"}}, "years": {}})
    write(tmp_path / "financial-ratios" / "AAA.json", {"symbol": "AAA", "kind": "bank", "fetched_at": "x", "source": "vndirect:finfo",
                                                       "quarters": {"2026-03-31": {"NIM": "1"}, "2026-06-30": {"NIM": "2"}}})
    write(tmp_path / "fundamentals" / "BBB.json", {"symbol": "BBB", "fetched_at": "x", "source": "vndirect", "years": {"2024": {"eps": "1"}, "2025": {"eps": "2"}},
                                                   "quarters": {"2026-Q3": {"npat": "3"}}, "annual": {}, "dividends": [{"year": "2025"}],
                                                   "shares_outstanding": "100", "shares_check": None})
    write(tmp_path / "events" / "BBB.json", {"symbol": "BBB", "fetched_at": "x", "events": [{"title": "Trả cổ tức"}]})
    write(tmp_path / "company" / "BBB.json", {"symbol": "BBB", "shareholders": [{"name": "Công ty X"}], "officers": [], "fetched_at": "x", "source": "vndirect"})
    write(tmp_path / "insider" / "BBB.json", {"symbol": "BBB", "deals": [], "fetched_at": "x", "source": "vndirect"})
    write(tmp_path / "macro" / "vn_cpi_yoy.json", {"indicator": "vn_cpi_yoy", "observations": [
        {"date": f"2026-0{m}-28", "value": str(m), "entry": "auto", "source_url": None, "recorded_at": "x"} for m in (6, 7, 8)]})
    write(tmp_path / "macro" / "_status.json", {"vn_cpi_yoy": {"status": "ok", "at": "x"}})
    write(tmp_path / "macro" / "asia-indices.json", {"status": "ok", "read_at": "x", "rows": [{"code": "KOSPI", "price": "1"}]})
    (tmp_path / "macro" / "vn_pmi.json.bak-2026-11-16").write_text("{}", encoding="utf-8")
    write(tmp_path / "index-valuation" / "VNINDEX-pe-1d.json", {"key": "VNINDEX-pe-1d", "points": [["2026-11-2" + str(i), str(10 + i)] for i in range(5)]})
    write(tmp_path / "gold-price.json", {"source": "Phú Quý", "unit": "chỉ", "as_of": "x", "kinds": {"SJC": {"buy": "1", "sell": "2"}}})
    write(tmp_path / "omo.json", {"sessions": [{"date": f"2026-11-1{i}", "rows": [], "total": str(i)} for i in range(4)]})
    store = PriceStore(tmp_path)
    ingest(store, CAL, [bar("VNINDEX", d, 1000 + i) for i, d in enumerate(("2026-11-02", "2026-11-03", "2026-11-04"))], revision_id="r1")
    return PublicData(tmp_path)


def test_symbol_profile_reads_listing_sector_and_groups(data):
    assert data.thong_tin_ma("aaa") == {"ma": "AAA", "niem_yet_hose": True, "nganh_icb": "Ngân hàng", "nhom_chi_so": ["VN30", "VN100"],
                                        "nguon": {"niem_yet": "2026-11-24T13:00:00+00:00", "nganh": "2026-11-25", "nhom": "2026-11-23"}}
    assert data.thong_tin_ma("BBB")["nganh_icb"] is None


def test_bad_symbols_are_refused_before_any_file_is_read(data):
    for bad in ("../x", "A", "AB/CD", "", "TOOLONGSYMBOL1"):
        assert data.bao_cao_tai_chinh(bad) == {"thieu": True, "ly_do": "Mã không hợp lệ."}


def test_missing_file_says_so_instead_of_guessing(data):
    assert data.eps_co_tuc("ZZZ") == {"thieu": True, "ly_do": "Chưa có dữ liệu cơ bản của ZZZ trong kho."}
    assert data.gia_ngay("ZZZ") == {"thieu": True, "ly_do": "Chưa có giá ngày của ZZZ trong kho."}


def test_statements_keep_the_newest_periods_and_pick_the_financial_layout(data):
    out = data.bao_cao_tai_chinh("BBB", ky="quy", so_ky=2)
    assert out["ky"] == {"2026-Q2": {"cash": "2"}, "2026-Q3": {"cash": "3"}} and out["don_vi"] == "đồng" and out["nguon"] == "vndirect:finfo"
    assert data.bao_cao_tai_chinh("BBB", ky="nam")["ky"] == {"2024": {"cash": "7"}, "2025": {"cash": "8"}}
    assert data.bao_cao_tai_chinh("AAA")["ky"] == {"2026-Q3": {"loans": "9"}}
    assert data.bao_cao_tai_chinh("BBB", ky="thang")["thieu"] is True


def test_ratios_fundamentals_and_company_files(data):
    assert data.chi_so_tai_chinh("AAA", so_ky=1)["ky"] == {"2026-06-30": {"NIM": "2"}}
    f = data.eps_co_tuc("BBB", so_ky=1)
    assert f["years"] == {"2025": {"eps": "2"}} and f["dividends"] == [{"year": "2025"}] and f["shares_outstanding"] == "100"
    assert data.su_kien_doanh_nghiep("BBB")["events"] == [{"title": "Trả cổ tức"}]
    assert data.co_dong_ban_lanh_dao("BBB")["shareholders"] == [{"name": "Công ty X"}]
    assert data.giao_dich_noi_bo("BBB")["deals"] == []


def test_daily_prices_in_order_with_a_session_limit(data):
    out = data.gia_ngay("VNINDEX", so_phien=2)
    assert [r["ngay"] for r in out["phien"]] == ["2026-11-03", "2026-11-04"]
    assert out["phien"][-1] == {"ngay": "2026-11-04", "mo": "1002", "cao": "1102", "thap": "902", "dong": "1002", "khoi_luong": 1000}
    assert out["co_so_gia"] == "raw" and out["nguon"] == "fixture"
    assert [r["ngay"] for r in data.gia_ngay("VNINDEX", tu_ngay="2026-11-03", den_ngay="2026-11-03")["phien"]] == ["2026-11-03"]
    assert data.gia_ngay("VNINDEX", tu_ngay="hôm qua")["thieu"] is True


def test_macro_lists_series_only_and_reads_the_newest_points(data):
    assert data.danh_sach_vi_mo() == {"chi_bao": [{"ma": "vn_cpi_yoy", "trang_thai": "ok", "cap_nhat": "x"}]}
    assert [o["value"] for o in data.chi_bao_vi_mo("vn_cpi_yoy", so_diem=2)["quan_sat"]] == ["7", "8"]
    assert data.chi_bao_vi_mo("_status")["thieu"] is True and data.chi_bao_vi_mo("../omo")["thieu"] is True
    assert data.chi_so_chau_a()["rows"] == [{"code": "KOSPI", "price": "1"}]
    assert data.gia_vang()["kinds"] == {"SJC": {"buy": "1", "sell": "2"}}
    assert [s["date"] for s in data.omo(so_phien=2)["sessions"]] == ["2026-11-12", "2026-11-13"]


def test_index_valuation(data):
    assert data.dinh_gia_chi_so("VNINDEX", "pe", so_diem=2)["diem"] == [["2026-11-23", "13"], ["2026-11-24", "14"]]
    assert data.dinh_gia_chi_so("VN30", "pb")["thieu"] is True
    assert data.dinh_gia_chi_so("HNX", "pe")["thieu"] is True


def test_server_exposes_exactly_the_approved_read_only_tools(data):
    from mcp import Client
    from investment_agent.mcp_server import build_server

    async def run():
        async with Client(build_server(data.root)) as client:
            tools = (await client.list_tools()).tools
            result = await client.call_tool("thong_tin_ma", {"ma": "AAA"})
            return tools, result

    tools, result = anyio.run(run)
    assert sorted(t.name for t in tools) == sorted([
        "thong_tin_ma", "gia_ngay", "dinh_gia_chi_so", "bao_cao_tai_chinh", "chi_so_tai_chinh", "eps_co_tuc", "su_kien_doanh_nghiep",
        "co_dong_ban_lanh_dao", "giao_dich_noi_bo", "danh_sach_vi_mo", "chi_bao_vi_mo", "chi_so_chau_a", "gia_vang", "omo"])
    assert all(t.annotations and t.annotations.read_only_hint for t in tools)
    assert "Ngân hàng" in result.content[0].text


@pytest.mark.parametrize("module", ["public_tools.py", "mcp_server.py"])
def test_server_code_never_imports_personal_data(module):
    tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    project = [m for m in names if m.startswith("investment_agent")]
    assert project and all(m.startswith(("investment_agent.market", "investment_agent.public_tools")) for m in project), project
    assert not any(m.startswith(("investment_agent.market.watchlist", "firebase", "google")) for m in names)
