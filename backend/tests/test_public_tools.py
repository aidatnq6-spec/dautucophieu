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
    write(tmp_path / "fund-nav.json", {"fetched_at": "t", "source": "Fmarket", "url": "u",
                                       "funds": {"QA": {"date": "2026-11-25", "name": "Quỹ A", "nav": "10"}, "QB": {"date": "2026-11-24", "name": "Quỹ B", "nav": "20"}},
                                       "profiles": {"QA": {"fee": "1", "kind": "STOCK", "manager": "M", "returns": {"m1": "2"}}}})
    write(tmp_path / "fund-nav-history.json", {"QA": {f"2026-11-1{i}": str(9 + i) for i in range(4)}})
    write(tmp_path / "fund-holdings.json", {"fetched_at": "t", "source": "Fmarket", "funds": {"QA": {"as_of": "2026-10", "stocks": [{"symbol": "AAA", "percent": "6"}]}}})
    write(tmp_path / "fund-scores.json", {"2026-11": {"QA": {"score": "9"}}})
    write(tmp_path / "gold-price-history.json", {"Vàng miếng SJC": {f"2026-11-1{i}": str(100 + i) for i in range(5)}, "Nhẫn": {"2026-11-14": "90"}})
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


def test_open_funds_list_and_one_fund_without_the_apps_own_scores(data):
    listing = data.quy_mo()
    assert listing["nguon"] == "Fmarket" and listing["lay_luc"] == "t"
    assert listing["quy"] == [{"ma": "QA", "ten": "Quỹ A", "loai": "STOCK", "nav": "10", "ngay": "2026-11-25"},
                              {"ma": "QB", "ten": "Quỹ B", "loai": None, "nav": "20", "ngay": "2026-11-24"}]
    one = data.quy_mo("qa", so_ngay=2)
    assert one["nav"] == {"date": "2026-11-25", "name": "Quỹ A", "nav": "10"} and one["ho_so"]["manager"] == "M"
    assert one["lich_su_nav"] == {"2026-11-12": "11", "2026-11-13": "12"}
    assert one["danh_muc_cong_bo"] == {"as_of": "2026-10", "stocks": [{"symbol": "AAA", "percent": "6"}]}
    assert "score" not in json.dumps(one) and "score" not in json.dumps(listing)
    assert data.quy_mo("QB")["danh_muc_cong_bo"] is None and data.quy_mo("QB")["lich_su_nav"] == {}
    assert data.quy_mo("ZZ")["thieu"] is True and data.quy_mo("../x")["thieu"] is True


def test_gold_history_lists_kinds_then_reads_buy_prices(data):
    assert data.gia_vang_lich_su()["loai"] == ["Nhẫn", "Vàng miếng SJC"]
    out = data.gia_vang_lich_su("Vàng miếng SJC", so_ngay=2)
    assert {k: v for k, v in out.items() if k != "tep_cap_nhat_luc"} == {"loai": "Vàng miếng SJC", "gia": "mua", "don_vi": "đồng/chỉ", "nguon": "Phú Quý",
                   "diem": [["2026-11-13", "103"], ["2026-11-14", "104"]]}
    assert data.gia_vang_lich_su("Bạc")["thieu"] is True


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
        "co_dong_ban_lanh_dao", "giao_dich_noi_bo", "danh_sach_vi_mo", "chi_bao_vi_mo", "chi_so_chau_a", "gia_vang", "omo",
        "quy_mo", "gia_vang_lich_su", "dinh_gia_ma", "lich_su_gia"])
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


def test_files_without_a_fetch_time_report_when_the_file_was_last_written(data):
    # P/E-P/B series, gold history and OMO keep no fetch time inside the file; the file's own write time is the only honest stamp.
    import os
    stamp = datetime(2026, 11, 25, 13, 0, tzinfo=timezone.utc)
    for name in ("index-valuation/VNINDEX-pe-1d.json", "gold-price-history.json", "omo.json"):
        os.utime(data.root / name, (stamp.timestamp(), stamp.timestamp()))
    assert data.dinh_gia_chi_so("VNINDEX", "pe")["tep_cap_nhat_luc"] == "2026-11-25T13:00:00+00:00"
    assert data.gia_vang_lich_su("Nhẫn")["tep_cap_nhat_luc"] == "2026-11-25T13:00:00+00:00"
    assert data.gia_vang_lich_su()["tep_cap_nhat_luc"] == "2026-11-25T13:00:00+00:00"
    assert data.omo()["tep_cap_nhat_luc"] == "2026-11-25T13:00:00+00:00"


def test_statements_name_each_line_as_vndirect_does_and_say_what_equity_covers(data):
    write(data.root / "statements" / "CCC.json", {"symbol": "CCC", "fetched_at": "x", "source": "vndirect:finfo",
                                                  "quarters": {"2026-Q3": {"npat": "10", "npat_parent": "9", "equity": "100", "minority_equity": "7"}}, "years": {}})
    out = data.bao_cao_tai_chinh("CCC")
    assert out["ten_dong"] == {"npat": "Lợi nhuận sau thuế thu nhập doanh nghiệp", "npat_parent": "Lợi nhuận sau thuế của Công ty mẹ",
                               "equity": "Vốn chủ sở hữu", "minority_equity": "Lợi ích cổ đông không kiểm soát"}
    assert "không kiểm soát" in out["pham_vi"]["equity"] and "công ty mẹ" in out["pham_vi"]["npat_parent"]
    bank = data.bao_cao_tai_chinh("AAA")  # the financial layout names its own lines
    assert bank["ten_dong"] == {} and bank["loai"] == "bank"  # "loans" is not a stored bank line; nothing is named by guess


def test_fundamentals_say_profit_is_the_parents_and_equity_includes_minorities(data):
    write(data.root / "statements" / "BBB.json", {"symbol": "BBB", "fetched_at": "x", "source": "vndirect:finfo",
                                                  "quarters": {"2026-Q3": {"minority_equity": "5"}}, "years": {"2025": {"minority_equity": "4"}}})
    out = data.eps_co_tuc("BBB", so_ky=1)
    assert "công ty mẹ" in out["chu_thich"]["npat"] and "không kiểm soát" in out["chu_thich"]["equity"]
    assert out["loi_ich_thieu_so"] == {"years": {"2025": "4"}, "quarters": {"2026-Q3": "5"}}


def test_published_valuation_of_one_ticker(data):
    write(data.root / "valuation-check" / "BBB.json", {"fetched_at": "2026-11-25T13:04:50+00:00", "date": "2026-11-23", "market_cap": "191",
                                                        "pe": "11.26", "pb": "1.02", "shares": "1245", "profit_quarter": "2026-Q3", "ours": "never shown"})
    assert data.dinh_gia_ma("bbb") == {"ma": "BBB", "nguon": "VNDirect", "ngay": "2026-11-23", "lay_luc": "2026-11-25T13:04:50+00:00",
                                       "von_hoa": "191", "pe": "11.26", "pb": "1.02", "so_co_phieu": "1245", "quy_loi_nhuan": "2026-Q3"}
    assert data.dinh_gia_ma("ZZZ") == {"thieu": True, "ly_do": "Chưa có định giá VNDirect công bố của ZZZ trong kho."}


def test_long_price_history_is_unadjusted_closes_with_the_share_events_that_break_it(data):
    write(data.root / "index-history" / "BBB.json", {"symbol": "BBB", "fetched_at": "2026-11-07T08:11:50+00:00", "source": "vndirect:finfo",
                                                     "closes": [["2016-12-30", "20.5"], ["2017-01-03", "21"], ["2024-09-30", "30"],
                                                                ["2024-10-31", "28"], ["2026-11-06", "15.1"]]})
    write(data.root / "fundamentals" / "BBB.json", {"symbol": "BBB", "share_issues": [{"date": "2016-07-01", "kind": "bonus", "ratio": "0.1"},
                                                                                       {"date": "2024-10-17", "kind": "bonus", "ratio": "0.1"},
                                                                                       {"date": "2025-01-05", "kind": "raise", "ratio": "0.2"}]})
    out = data.lich_su_gia("bbb", tu_ngay="2017-01-01")
    assert out["diem"] == [["2017-01-03", "21"], ["2024-09-30", "30"], ["2024-10-31", "28"], ["2026-11-06", "15.1"]]
    assert out["don_vi"] == "nghìn đồng" and out["dieu_chinh"] is False and out["nguon"] == "vndirect:finfo"
    assert out["ngay_cuoi"] == "2026-11-06" and out["lay_luc"] == "2026-11-07T08:11:50+00:00"
    assert "cuối tháng" in out["mat_do"] and "chưa điều chỉnh" in out["luu_y"]
    assert out["su_kien_co_phieu"] == [{"date": "2024-10-17", "kind": "bonus", "ratio": "0.1"}, {"date": "2025-01-05", "kind": "raise", "ratio": "0.2"}]
    assert data.lich_su_gia("BBB", tu_ngay="ngày mai")["thieu"] is True
    assert data.lich_su_gia("ZZZ") == {"thieu": True, "ly_do": "Chưa có lịch sử giá dài hạn của ZZZ trong kho."}
