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
        "quy_mo", "gia_vang_lich_su", "dinh_gia_ma", "lich_su_gia", "so_sanh_nganh", "thuyet_minh", "dinh_gia_lich_su", "tu_doanh", "khoi_ngoai", "cung_chieu"])
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
    published = data.dinh_gia_ma("bbb")
    assert {k: published[k] for k in ("ma", "nguon", "ngay", "lay_luc", "von_hoa", "pe", "pb", "so_co_phieu", "quy_loi_nhuan")} == {"ma": "BBB", "nguon": "VNDirect", "ngay": "2026-11-23", "lay_luc": "2026-11-25T13:04:50+00:00",
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


def test_long_prices_prefer_vndirects_adjusted_series_month_end_by_default(data):
    write(data.root / "price-history" / "BBB.json", {"symbol": "BBB", "fetched_at": "2026-11-26T13:00:00+00:00", "source": "vndirect:finfo",
                                                     "adjusted": True, "unit": "nghìn đồng",
                                                     "closes": [["2024-09-27", "27.1"], ["2024-09-30", "27.3"], ["2024-10-16", "27.349"],
                                                                ["2024-10-17", "27.563"], ["2024-10-31", "26.9"], ["2024-11-05", "26.5"]]})
    out = data.lich_su_gia("BBB", tu_ngay="2024-09-28")
    assert out["dieu_chinh"] is True and out["nguon"] == "vndirect:finfo" and out["lay_luc"] == "2026-11-26T13:00:00+00:00"
    assert out["diem"] == [["2024-09-30", "27.3"], ["2024-10-31", "26.9"], ["2024-11-05", "26.5"]]  # each month's last close in range
    assert out["ngay_cuoi"] == "2024-11-05" and "điều chỉnh" in out["luu_y"]
    daily = data.lich_su_gia("BBB", tu_ngay="2024-10-16", den_ngay="2024-10-17", mat_do="ngay")
    assert daily["diem"] == [["2024-10-16", "27.349"], ["2024-10-17", "27.563"]] and daily["mat_do"].startswith("Từng phiên")
    assert data.lich_su_gia("BBB", mat_do="tuan")["thieu"] is True


def test_dividends_paid_in_the_cash_flow_is_told_apart_from_the_dividends_shareholders_received(data):
    note = data.bao_cao_tai_chinh("BBB")["pham_vi"]["dividends_paid"]
    assert "cổ đông không kiểm soát" in note and "eps_co_tuc" in note


def test_ratios_missing_for_a_ticker_say_so(data):
    assert data.chi_so_tai_chinh("ZZZ") == {"thieu": True, "ly_do": "Chưa có chỉ số tài chính của ZZZ trong kho."}


def test_a_quarter_whose_profit_comes_mostly_from_outside_sales_is_flagged_above_thirty_percent(data):
    quarters = {"2025-Q4": {"pbt": "100", "fin_income": "5", "other_profit": "0"}, "2026-Q1": {"pbt": "100", "fin_income": "5", "other_profit": "5"},
                "2026-Q2": {"pbt": "1000", "fin_income": "900", "other_profit": "0"}, "2026-Q3": {"pbt": "100", "fin_income": "20", "other_profit": "5"}}
    write(data.root / "statements" / "KKK.json", {"symbol": "KKK", "fetched_at": "x", "source": "vndirect:finfo", "quarters": quarters, "years": {}})
    flag = data.bao_cao_tai_chinh("KKK", so_ky=1)["canh_bao_loi_nhuan_ngoai_ban_hang"]
    assert flag["nguong"] == "0.3" and flag["cong_thuc"] == "(fin_income + other_profit) / pbt"
    assert flag["quy_gan_nhat"] == {"ky": "2026-Q3", "ty_le": "0.25", "vuot_nguong": False}
    assert flag["bon_quy"] == {"ky": ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"], "ty_le": "0.7231", "vuot_nguong": True}  # (5+10+900+25) / 1300
    write(data.root / "statements" / "LLL.json", {"symbol": "LLL", "fetched_at": "x", "source": "vndirect:finfo",
                                                  "quarters": {"2026-Q3": {"pbt": "-5", "fin_income": "3", "other_profit": "0"}}, "years": {}})
    loss = data.bao_cao_tai_chinh("LLL")["canh_bao_loi_nhuan_ngoai_ban_hang"]
    assert loss["quy_gan_nhat"] == {"ky": "2026-Q3", "ty_le": None, "vuot_nguong": None, "ly_do": "LNTT không dương"}
    assert loss["bon_quy"] == {"ky": ["2026-Q3"], "ty_le": None, "vuot_nguong": None, "ly_do": "Chưa đủ 4 quý"}
    assert "canh_bao_loi_nhuan_ngoai_ban_hang" not in data.bao_cao_tai_chinh("KKK", ky="nam")
    assert "canh_bao_loi_nhuan_ngoai_ban_hang" not in data.bao_cao_tai_chinh("AAA")  # banks: their income is financial by nature


def test_ratios_of_a_general_company_come_from_vndirects_own_set(data):
    write(data.root / "financial-ratios-general" / "BBB.json", {"symbol": "BBB", "kind": "general", "fetched_at": "t", "source": "vndirect:finfo",
                                                               "names": {"ROAE_TR_AVG4Q": "ROAE"},
                                                               "quarters": {"2026-06-30": {"ROAE_TR_AVG4Q": "0.09"}, "2026-09-30": {"ROAE_TR_AVG4Q": "0.08"}}})
    out = data.chi_so_tai_chinh("BBB", so_ky=1)
    assert out["loai"] == "general" and out["ten_chi_so"] == {"ROAE_TR_AVG4Q": "ROAE"} and out["ky"] == {"2026-09-30": {"ROAE_TR_AVG4Q": "0.08"}}
    assert "0,08 là 8%" in out["luu_y"] and out["lay_luc"] == "t"


def test_an_insider_notice_without_volume_points_to_its_document(data):
    write(data.root / "insider" / "BBB.json", {"symbol": "BBB", "fetched_at": "t", "source": "vndirect:finfo", "deals": [
        {"date": "2026-11-11", "kind": None, "shares": None, "source": "HOSE", "title": "Báo cáo thay đổi sở hữu", "url": "https://dstock.vndirect.com.vn/x",
         "doc_url": "https://www.hsx.vn/vi/tin-tuc/x/1"},
        {"date": "2026-10-14", "kind": "Mua", "shares": 10000, "source": "HOSE", "title": "Báo cáo kết quả", "url": "https://dstock.vndirect.com.vn/y"},
        {"date": "2026-10-01", "kind": None, "shares": None, "source": "HOSE", "title": "Cũ", "url": "https://dstock.vndirect.com.vn/z"}]})
    deals = data.giao_dich_noi_bo("BBB")["deals"]
    assert deals[0]["van_ban"] == "https://www.hsx.vn/vi/tin-tuc/x/1" and deals[0]["thieu_so_luong"] is True
    assert "van_ban" not in deals[1] and deals[2]["van_ban"] == "https://dstock.vndirect.com.vn/z"
    assert "không có chiều mua bán và số lượng" in data.giao_dich_noi_bo("BBB")["luu_y"]


def test_an_insider_notice_read_from_its_hose_document_carries_the_figures(data):
    write(data.root / "insider" / "BBB.json", {"symbol": "BBB", "fetched_at": "t", "source": "vndirect:finfo", "deals": [
        {"date": "2026-11-11", "kind": None, "shares": None, "source": "HOSE", "title": "Báo cáo kết quả ESOP", "url": None,
         "doc_url": "https://www.hsx.vn/vi/tin-tuc/x/77"}]})
    write(data.root / "insider-docs" / "77.json", {"news_id": "77", "read_at": "r", "reason": None,
                                                   "result": {"kind": "ESOP", "shares": 650000, "files": 1, "rong": False, "before": 1, "after": 650001}})
    out = data.giao_dich_noi_bo("BBB")
    deal = out["deals"][0]
    assert (deal["kind"], deal["shares"]) == ("ESOP", 650000) and "thieu_so_luong" not in deal
    assert deal["tu_van_ban"] == {"truoc": 1, "sau": 650001, "so_tep": 1, "rong": False, "doc_luc": "r"}
    assert "tu_van_ban" in out["luu_y"] and "ESOP" in out["luu_y"]


def test_an_eps_that_moved_far_more_than_profit_is_flagged_above_three_times(data):
    write(data.root / "fundamentals" / "EEE.json", {"symbol": "EEE", "years": {
        "2022": {"npat": "1100", "eps": "1440"}, "2023": {"npat": "715", "eps": "840"}, "2024": {"npat": "810", "eps": "80"},
        "2025": {"npat": "1045", "eps": "870"}, "2021": {"npat": "-5", "eps": "-10"}}})
    flag = data.eps_co_tuc("EEE")["canh_bao_eps"]
    assert flag["nguong"] == "3" and [r["nam"] for r in flag["nam"]] == ["2024", "2025"]  # 2024 fell tenfold; 2025 rose back
    first = flag["nam"][0]
    assert first == {"nam": "2024", "eps": "80", "eps_nam_truoc": "840", "npat": "810", "npat_nam_truoc": "715", "lech": "0.084"}
    assert "giữ nguyên" in flag["y_nghia"]


def test_daily_prices_name_the_hose_sessions_the_store_lacks(data, tmp_path):
    out = data.gia_ngay("VNINDEX", tu_ngay="2026-11-02", den_ngay="2026-11-06")
    assert out["phien_thieu"] == ["2026-11-05", "2026-11-06"]  # the fixture stops on 04/11; 05 and 06/11 are HOSE sessions
    assert out["lich_kiem"].startswith("config/trading-calendar-hose-2026.json")


def test_sessions_before_the_official_calendar_are_checked_against_vnindex_days(data):
    from datetime import date as d
    from investment_agent.market.prices import PriceStore, ingest
    from investment_agent.market.calendar import TradingCalendar
    cal = TradingCalendar(version="t", source="synthetic", holidays=frozenset(), first=d(2025, 12, 1), last=d(2025, 12, 31))
    ingest(PriceStore(data.root), cal, [bar("BBB", day, 1000) for day in ("2025-12-29", "2025-12-31")], revision_id="r1")
    write(data.root / "index-sessions" / "VNINDEX.json", {"source": "vndirect:finfo", "fetched_at": "t", "dates": ["2025-12-29", "2025-12-30", "2025-12-31"]})
    out = data.gia_ngay("BBB", tu_ngay="2025-12-29", den_ngay="2025-12-31")
    assert out["phien_thieu"] == ["2025-12-30"]
    assert "phiên VN-Index của VNDirect" in out["lich_kiem"] and "không phải lịch chính thức" in out["lich_kiem"]


def test_daily_long_prices_name_the_vnindex_days_the_ticker_lacks(data):
    write(data.root / "price-history" / "BBB.json", {"symbol": "BBB", "fetched_at": "t", "source": "vndirect:finfo", "adjusted": True,
                                                     "closes": [["2015-03-02", "10"], ["2015-03-05", "11"]]})
    write(data.root / "index-sessions" / "VNINDEX.json", {"source": "vndirect:finfo", "fetched_at": "t",
                                                          "dates": ["2015-03-02", "2015-03-03", "2015-03-04", "2015-03-05"]})
    out = data.lich_su_gia("BBB", mat_do="ngay")
    assert out["phien_thieu"] == ["2015-03-03", "2015-03-04"] and "phiên VN-Index" in out["lich_kiem"]
    assert "phien_thieu" not in data.lich_su_gia("BBB")  # month-ends are a choice of days, not sessions


def test_a_ticker_set_against_its_icb_sector_on_the_same_quarter(data):
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": ["KKK", "PPA", "PPB", "PPC", "PPD", "BNK"],
                                                                  "icb_codes": {"KKK": "8600", "PPA": "8600", "PPB": "8600", "PPC": "8600", "PPD": "8600", "BNK": "8300"},
                                                                  "icb_names": {"8600": "Bất động sản", "8300": "Ngân hàng"}}})
    for sym, roe, q in (("KKK", "0.08", "2026-09-30"), ("PPA", "0.05", "2026-09-30"), ("PPB", "0.10", "2026-09-30"), ("PPC", "0.20", "2026-09-30"),
                        ("PPD", "0.30", "2026-06-30")):  # PPD has not reported Q3 yet: counted apart, its Q2 is not used
        write(data.root / "financial-ratios-general" / f"{sym}.json", {"symbol": sym, "kind": "general", "fetched_at": "t", "source": "vndirect:finfo",
                                                                      "names": {"ROAE_TR_AVG4Q": "ROAE"},
                                                                      "quarters": {q: {"ROAE_TR_AVG4Q": roe, **({"DSO_TR_AVG5Q": "40"} if sym == "KKK" else {})}}})
    out = data.so_sanh_nganh("kkk")
    assert out["nganh"] == "Bất động sản" and out["quy"] == "2026-09-30" and out["so_doanh_nghiep_nganh"] == 4
    assert out["chua_co_quy_nay"] == 1 and out["nguon"] == "vndirect:finfo"
    roe = next(c for c in out["chi_so"] if c["ma_chi_so"] == "ROAE_TR_AVG4Q")
    assert roe == {"ma_chi_so": "ROAE_TR_AVG4Q", "ten": "ROAE", "gia_tri": "0.08", "trung_vi": "0.1", "phan_vi_25": "0.075", "phan_vi_75": "0.15",
                   "so_doanh_nghiep": 3, "thu_hang": "3/4 (cao xuống thấp)"}
    dso = next(c for c in out["chi_so"] if c["ma_chi_so"] == "DSO_TR_AVG5Q")
    assert dso["gia_tri"] == "40" and dso["trung_vi"] is None and dso["ly_do"] == "Dưới 3 doanh nghiệp cùng ngành có số quý này"
    assert len(out["chi_so"]) == 16 and "không gắn nhãn tốt hay xấu" in out["luu_y"].lower()
    assert data.so_sanh_nganh("BNK")["thieu"] is True and "Chưa có chỉ số" in data.so_sanh_nganh("BNK")["ly_do"]  # a bank: its own ratios
    assert data.so_sanh_nganh("ZZZ")["thieu"] is True


def test_a_bank_set_against_the_other_hose_banks_on_the_same_quarter(data):
    from investment_agent.market.financial_ratios import DISPLAY
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": ["BNK", "BAA", "BBB", "BCC", "BDD", "SEC"],
        "icb_codes": {"BNK": "8300", "BAA": "8300", "BBB": "8300", "BCC": "8300", "BDD": "8300", "SEC": "8700"},
        "icb_names": {"8300": "Ngân hàng", "8700": "Dịch vụ tài chính"}}})
    for sym, npl, q in (("BNK", "0.02", "2026-09-30"), ("BAA", "0.01", "2026-09-30"), ("BBB", "0.03", "2026-09-30"), ("BCC", "0.05", "2026-09-30"),
                        ("BDD", "0.09", "2026-06-30")):  # BDD has not reported Q3 yet: counted apart, its Q2 is not used
        write(data.root / "financial-ratios" / f"{sym}.json", {"symbol": sym, "kind": "bank", "fetched_at": "2026-11-27T01:00:00+00:00",
                                                              "source": "vndirect:finfo", "quarters": {q: {"BAD_LOANS_RATIO_AQ": npl}}})
    out = data.so_sanh_nganh("bnk")
    assert out["nganh"] == "Ngân hàng" and out["quy"] == "2026-09-30" and out["so_doanh_nghiep_nganh"] == 4 and out["chua_co_quy_nay"] == 1
    assert out["nguon"] == "vndirect:finfo"
    npl = next(c for c in out["chi_so"] if c["ma_chi_so"] == "BAD_LOANS_RATIO_AQ")
    assert npl == {"ma_chi_so": "BAD_LOANS_RATIO_AQ", "ten": "Tỷ lệ nợ xấu (NPL)", "gia_tri": "0.02", "trung_vi": "0.03",
                   "phan_vi_25": "0.02", "phan_vi_75": "0.04", "so_doanh_nghiep": 3, "thu_hang": "3/4 (cao xuống thấp)"}
    assert [c["ma_chi_so"] for c in out["chi_so"]] == [code for code, _, _ in DISPLAY["bank"]]
    sec = data.so_sanh_nganh("SEC")
    assert sec["thieu"] is True and "ICB cấp 4" in sec["ly_do"]  # securities firms compare on level 4 (27/11/2026)


def test_general_ratios_warn_that_per_share_figures_use_vndirects_quarter_end_share_count(data):
    write(data.root / "financial-ratios-general" / "BBB.json", {"symbol": "BBB", "kind": "general", "fetched_at": "t", "source": "vndirect:finfo",
                                                               "names": {}, "quarters": {"2026-09-30": {"BVPS_AQ": "16737"}}})
    note = data.chi_so_tai_chinh("BBB")["luu_y"]
    assert "số cổ phiếu cuối quý" in note and "đợt thưởng" in note


def test_notes_split_financial_income_borrowings_and_inventory_with_the_pages_own_labels(data):
    write(data.root / "company-notes" / "BBB.json", {"symbol": "BBB", "fetched_at": "2026-11-25T14:06:24+00:00", "source": "vietcap:iq", "fields_version": 2,
        "quarters": {"2026-Q1": {"fin_interest": "7100000000"},
                     "2026-Q2": {"fin_interest": "9800000000", "fin_other": "896300000000", "fin_disposals": "0", "exp_interest": "19300000000",
                                 "bonds": "1000", "inv_property": "5000", "ppe_dep_add": "1"}},
        "years": {"2025": {"lt_bank": "3000"}}})
    out = data.thuyet_minh("bbb", so_ky=1)
    assert out["nguon"] == "vietcap:iq" and out["lay_luc"] == "2026-11-25T14:06:24+00:00" and out["don_vi"] == "đồng"
    q2 = out["ky"]["2026-Q2"]
    assert q2["doanh_thu_tai_chinh"] == {"fin_interest": "9800000000", "fin_disposals": "0", "fin_other": "896300000000"}
    assert q2["chi_phi_tai_chinh"] == {"exp_interest": "19300000000"} and q2["no_vay"] == {"bonds": "1000"} and q2["ton_kho"] == {"inv_property": "5000"}
    assert out["ten_dong"]["fin_other"] == "Doanh thu tài chính khác" and out["ten_dong"]["fin_disposals"] == "Lãi thanh lý đầu tư"
    assert "ppe_dep_add" not in json.dumps(out["ky"])  # only the named lines
    assert list(data.thuyet_minh("BBB", ky="nam")["ky"]) == ["2025"]
    assert data.thuyet_minh("ZZZ") == {"thieu": True, "ly_do": "Chưa có thuyết minh BCTC của ZZZ trong kho."}


def test_a_published_valuation_says_which_price_it_rests_on_and_how_far_the_latest_close_has_moved(data):
    write(data.root / "valuation-check" / "VNINDEX.json", {"fetched_at": "t", "date": "2026-11-02", "market_cap": "2000000", "pe": "10", "pb": "1",
                                                            "shares": "1000", "profit_quarter": "2026-Q3"})
    out = data.dinh_gia_ma("VNINDEX")
    assert out["gia_ngay_dinh_gia"] == "2000" and out["gia_moi_nhat"] == {"ngay": "2026-11-04", "gia": "1002"}
    assert out["lech_gia"] == "-0.499" and "5%" in out["luu_y"]  # (1002 − 2000) ÷ 2000


def test_a_tickers_own_pe_and_pb_history_by_month_end_with_medians_robust_to_tiny_profits(data):
    # 4 quarters' parent profit 100, parent equity 1000, 10 shares: P/E = 100 × close, P/B = 10 × close (close in thousand đồng)
    q = {k: {"npat_parent": "25", "equity_parent": "1000", "shares": "10"} for k in ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1")}
    q["2026-Q2"] = {"npat_parent": "-200", "equity_parent": "1000", "shares": "10"}  # four quarters to Q2/2026 lose money
    write(data.root / "index-history" / "BBB.json", {"symbol": "BBB", "fetched_at": "2026-11-07T08:11:50+00:00", "source": "vndirect:finfo", "quarters": q,
                                                     "closes": [["2025-05-30", "0.5"],   # Q1/2025 is out (15/05) but Q2–Q4/2024 are missing
                                                                ["2026-06-30", "0.1"], ["2026-07-31", "0.2"], ["2026-08-31", "0.3"]]})
    # a 10% bonus issue on 15/07/2026, after both quarters those months rest on: the close has fallen with it, so the shares must rise with it
    write(data.root / "fundamentals" / "BBB.json", {"symbol": "BBB", "share_issues": [{"date": "2026-07-15", "kind": "bonus", "ratio": "0.1"},
                                                                                      {"date": "2026-07-20", "kind": "raise", "ratio": "0.2"}]})
    out = data.dinh_gia_lich_su("bbb")
    pe, pb = out["cua_so"]["3_nam"]["pe"], out["cua_so"]["3_nam"]["pb"]
    assert pe["so_thang"] == 2 and pe["trung_vi"] == "16" and pe["bo_qua_lo"] == 1 and pe["bo_qua_thieu"] == 1  # 10 and 0.2 × 1000 × 11 ÷ 100 = 22
    assert (pe["thap_nhat"], pe["cao_nhat"]) == ("10", "22")
    assert pb["so_thang"] == 3 and pb["trung_vi"] == "2.2" and pb["bo_qua_thieu"] == 1
    assert out["hien_tai"] == {"ngay": "2026-08-31", "pe": None, "pb": "3.3"} and pb["thang_thap_hon_hien_tai"] == "2/3"
    assert "thưởng" in out["cong_thuc"]
    assert out["ngay_cuoi"] == "2026-08-31" and "45 ngày" in out["cong_thuc"] and "tự tính" in out["nguon"]
    assert data.dinh_gia_lich_su("ZZZ")["thieu"] is True


def test_every_time_the_tools_give_is_in_vietnam_time():
    from investment_agent.public_tools import vn_times
    out = vn_times({"lay_luc": "2026-11-26T08:30:05.123456+00:00", "fetched_at": "2026-11-25T13:04:50+00:00", "ngay": "2026-11-23",
                    "x": {"tep_cap_nhat_luc": "2026-11-26T01:31:00+00:00", "nested": [{"recorded_at": "2026-11-26T00:52:02+00:00"}]},
                    "fetched_at_bad": "not a time", "as_of": "2026-11-25T18:27:00+07:00", "lay_luc2": None})
    assert out["lay_luc"] == "2026-11-26T15:30:05+07:00" and out["fetched_at"] == "2026-11-25T20:04:50+07:00"
    assert out["x"]["tep_cap_nhat_luc"] == "2026-11-26T08:31:00+07:00" and out["x"]["nested"][0]["recorded_at"] == "2026-11-26T07:52:02+07:00"
    assert out["ngay"] == "2026-11-23" and out["fetched_at_bad"] == "not a time" and out["as_of"] == "2026-11-25T18:27:00+07:00"


def test_the_server_answers_in_vietnam_time(data):
    from mcp import Client
    from investment_agent.mcp_server import build_server

    async def run():
        async with Client(build_server(data.root)) as client:
            return await client.call_tool("gia_ngay", {"ma": "VNINDEX"})
    text = anyio.run(run).content[0].text
    assert '"lay_luc": "2026-10-24T17:00:00+07:00"' in text  # OBSERVED is 10:00 UTC


def test_fewer_daily_sessions_than_asked_point_to_the_long_daily_series(data):
    out = data.gia_ngay("VNINDEX", so_phien=60)
    assert len(out["phien"]) == 3 and "2026-11-02" in out["luu_y"] and "lich_su_gia" in out["luu_y"]
    assert "luu_y" not in data.gia_ngay("VNINDEX", so_phien=2)


def test_every_tool_answer_goes_through_vietnam_time():
    import re as _re
    source = (SRC / "mcp_server.py").read_text(encoding="utf-8")
    assert not _re.findall(r"^\s+return data\.", source, flags=_re.M)  # a new tool must wrap its answer in vn_times too


def test_a_securities_firm_set_against_the_other_hose_investment_services_firms(data):
    from investment_agent.market.financial_ratios import DISPLAY
    syms = ["SSA", "SSB", "SSC", "SSD", "SSE", "EVX"]
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": syms, "icb_codes": {s: "8700" for s in syms},
        "icb_names": {"8700": "Dịch vụ tài chính"}, "icb4_codes": {**{s: "8777" for s in syms[:5]}, "EVX": "8773"}}})
    for sym, roe, q in (("SSA", "0.12", "2026-09-30"), ("SSB", "0.08", "2026-09-30"), ("SSC", "0.10", "2026-09-30"), ("SSD", "0.20", "2026-09-30"),
                        ("SSE", "0.30", "2026-06-30"), ("EVX", "0.50", "2026-09-30")):  # SSE not out for Q3; EVX consumer finance, never a peer
        write(data.root / "financial-ratios" / f"{sym}.json", {"symbol": sym, "kind": "securities", "fetched_at": "2026-11-27T01:00:00+00:00",
                                                              "source": "vndirect:finfo", "quarters": {q: {"ROAE_TR_AVG4Q": roe}}})
    out = data.so_sanh_nganh("SSA")
    assert out["nganh"] == "Dịch vụ đầu tư (chứng khoán)" and out["ma_nganh"] == "8777" and out["quy"] == "2026-09-30"
    assert out["so_doanh_nghiep_nganh"] == 4 and out["chua_co_quy_nay"] == 1
    roe = next(c for c in out["chi_so"] if c["ma_chi_so"] == "ROAE_TR_AVG4Q")
    assert roe["ten"] == "ROAE" and roe["trung_vi"] == "0.1" and roe["so_doanh_nghiep"] == 3 and roe["thu_hang"] == "2/4 (cao xuống thấp)"
    assert [c["ma_chi_so"] for c in out["chi_so"]] == [code for code, _, _ in DISPLAY["securities"]]
    assert "ICB cấp 4" in out["luu_y"] and "cấp 2" not in out["luu_y"]
    evx = data.so_sanh_nganh("EVX")
    assert evx["thieu"] is True and "Dịch vụ đầu tư" in evx["ly_do"]


def test_a_securities_firm_without_level_four_codes_in_the_listing_says_so(data):
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": ["SSA"], "icb_codes": {"SSA": "8700"},
                                                                  "icb_names": {"8700": "Dịch vụ tài chính"}}})
    out = data.so_sanh_nganh("SSA")
    assert out["thieu"] is True and "ICB cấp 4" in out["ly_do"]


def _prop(data, day, stocks):
    rec = {"date": day, "source": "vndirect:finfo", "fetched_at": f"{day}T13:00:00+00:00", "khop": True,
           "index": {"buy_volume": "0", "sell_volume": "0", "buy_value": str(sum(b for _, b, _ in stocks)), "sell_value": str(sum(s for _, _, s in stocks))},
           "stocks": {c: {"buy_volume": "10", "sell_volume": "4", "buy_value": str(b), "sell_value": str(s)} for c, b, s in stocks}}
    write(data.root / "proprietary" / f"{day}.json", rec)


TU_DOANH_NOW = datetime(2026, 11, 27, 13, 30, tzinfo=timezone.utc)  # Friday 20:30 in Vietnam


def test_tu_doanh_sums_the_sessions_up_to_the_newest_stored_and_names_the_strongest_net_buys_and_sells(data):
    _prop(data, "2026-11-19", [("FPT", 5, 1), ("SSI", 1, 4)])
    write(data.root / "proprietary" / "2026-11-20.json", {"date": "2026-11-20", "thieu": True, "hoi_luc": "x"})
    _prop(data, "2026-11-23", [("FPT", 3, 0), ("HPG", 0, 2), ("VNM", 2, 2)])
    out = data.tu_doanh(so_phien=3, now=TU_DOANH_NOW)
    assert out["khoang"] == {"so_phien": 3, "so_phien_hoi": 3, "tu": "2026-11-19", "den": "2026-11-23", "phien_co_so": 2,
                             "phien_thieu": ["2026-11-20"], "chua_hoi": [], "phien_hong": [], "cham_phien": 3}  # 25, 26, 27/11 closed with no figures yet (24/11: holiday)
    assert out["toan_san"]["mua_gt"] == "11" and out["toan_san"]["ban_gt"] == "9" and out["toan_san"]["rong_gt"] == "2"
    assert [x["ma"] for x in out["mua_rong_manh"]] == ["FPT"] and out["mua_rong_manh"][0] == {
        "ma": "FPT", "mua_gt": "8", "ban_gt": "1", "rong_gt": "7", "mua_kl": "20", "ban_kl": "8", "rong_kl": "12", "so_phien": 2}
    assert [x["ma"] for x in out["ban_rong_manh"]] == ["SSI", "HPG"]  # VNM nets to zero: in neither list
    assert out["don_vi"].startswith("đồng") and out["nguon"].startswith("VNDirect") and out["phien_khong_khop"] == []


def test_tu_doanh_of_one_ticker_tells_a_session_without_its_trades_from_a_session_without_figures(data):
    _prop(data, "2026-11-19", [("FPT", 5, 1)])
    write(data.root / "proprietary" / "2026-11-20.json", {"date": "2026-11-20", "thieu": True, "hoi_luc": "x"})
    _prop(data, "2026-11-23", [("HPG", 1, 0)])
    out = data.tu_doanh(so_phien=3, ma="fpt", now=TU_DOANH_NOW)
    assert out["ma"] == "FPT" and out["phien"] == [
        {"ngay": "2026-11-19", "mua_gt": "5", "ban_gt": "1", "rong_gt": "4", "mua_kl": "10", "ban_kl": "4", "rong_kl": "6"},
        {"ngay": "2026-11-20", "thieu": True},
        {"ngay": "2026-11-23", "khong_giao_dich": True}]
    assert out["tong"]["rong_gt"] == "4" and out["tong"]["so_phien"] == 1


def test_tu_doanh_clamps_the_window_and_says_when_nothing_is_stored(data):
    assert data.tu_doanh(now=TU_DOANH_NOW)["thieu"] is True
    _prop(data, "2026-11-23", [("FPT", 1, 0)])
    assert data.tu_doanh(so_phien="x", now=TU_DOANH_NOW)["khoang"]["so_phien_hoi"] == 60
    assert data.tu_doanh(so_phien=9999, now=TU_DOANH_NOW)["khoang"]["so_phien_hoi"] == 250
    assert data.tu_doanh(so_phien=0, now=TU_DOANH_NOW)["khoang"]["so_phien_hoi"] == 1
    assert data.tu_doanh(ma="??", now=TU_DOANH_NOW)["thieu"] is True


def test_tu_doanh_tells_sessions_never_asked_from_sessions_vndirect_left_empty_and_gives_the_window_it_has(data):
    _prop(data, "2026-11-23", [("FPT", 1, 0)])
    write(data.root / "proprietary" / "2026-11-20.json", {"date": "2026-11-20", "thieu": True, "hoi_luc": "x"})  # 2026-11-19: no file
    out = data.tu_doanh(so_phien=3, now=TU_DOANH_NOW)
    assert out["khoang"]["phien_thieu"] == ["2026-11-20"] and out["khoang"]["chua_hoi"] == ["2026-11-19"]
    assert out["khoang"]["so_phien"] == 3 and out["khoang"]["so_phien_hoi"] == 3
    wide = data.tu_doanh(so_phien=250, now=TU_DOANH_NOW)  # only 2026 has a calendar here: the window says what it holds
    assert wide["khoang"]["so_phien_hoi"] == 250 and wide["khoang"]["so_phien"] < 250 and wide["khoang"]["tu"] >= "2026-01-01"
    assert "không khớp" in out["luu_y"]


def _foreign(data, day, stocks):
    write(data.root / "foreign" / f"{day}.json", {"date": day, "source": "vndirect:finfo", "fetched_at": f"{day}T13:00:00+00:00",
        "index": {"buy_volume": "0", "sell_volume": "0", "buy_value": "999", "sell_value": "0"},  # VNDirect's VNINDEX row: not the total
        "stocks": {c: {"buy_volume": "10", "sell_volume": "4", "buy_value": str(b), "sell_value": str(s)} for c, b, s in stocks}})


def test_khoi_ngoai_totals_are_the_sum_of_the_stocks_with_the_same_window_as_tu_doanh(data):
    _foreign(data, "2026-11-19", [("FPT", 5, 1), ("SSI", 1, 4)])
    write(data.root / "foreign" / "2026-11-20.json", {"date": "2026-11-20", "thieu": True, "ly_do": "VNDirect trả mọi mã bằng 0 cho phiên này"})
    _foreign(data, "2026-11-23", [("FPT", 3, 0), ("HPG", 0, 2)])
    out = data.khoi_ngoai(so_phien=3, now=TU_DOANH_NOW)
    assert out["khoang"]["phien_thieu"] == ["2026-11-20"] and out["khoang"]["cham_phien"] == 3 and out["khoang"]["so_phien"] == 3
    assert out["toan_san"] == {"mua_gt": "9", "ban_gt": "7", "rong_gt": "2", "mua_kl": "40", "ban_kl": "16", "rong_kl": "24"}
    assert [x["ma"] for x in out["mua_rong_manh"]] == ["FPT"] and [x["ma"] for x in out["ban_rong_manh"]] == ["SSI", "HPG"]
    assert "phien_khong_khop" not in out and out["nguon"].startswith("VNDirect (foreigns")
    one = data.khoi_ngoai(so_phien=3, ma="HPG", now=TU_DOANH_NOW)
    assert [r.get("khong_giao_dich") or r.get("thieu") or r["rong_gt"] for r in one["phien"]] == [True, True, "-2"]


def test_khoi_ngoai_with_an_empty_store_says_so(data):
    assert data.khoi_ngoai(now=TU_DOANH_NOW)["thieu"] is True


def test_a_ticker_vndirect_left_empty_is_named_and_never_read_as_no_trading(data):
    _foreign(data, "2026-11-19", [("FPT", 5, 1)])
    rec = json.loads((data.root / "foreign" / "2026-11-19.json").read_text(encoding="utf-8"))
    rec["bo_qua"] = ["HPG"]  # VNDirect served HPG with an empty figure that session
    write(data.root / "foreign" / "2026-11-19.json", rec)
    out = data.khoi_ngoai(so_phien=1, now=TU_DOANH_NOW)
    assert out["phien_bo_qua"] == [{"ngay": "2026-11-19", "ma": ["HPG"]}]
    one = data.khoi_ngoai(so_phien=1, ma="HPG", now=TU_DOANH_NOW)
    assert one["phien"] == [{"ngay": "2026-11-19", "thieu": True}]


def test_a_damaged_session_file_is_named_and_left_out_not_the_whole_answer(data):
    _foreign(data, "2026-11-19", [("FPT", 5, 1)])
    (data.root / "foreign" / "2026-11-20.json").write_text("{not json", encoding="utf-8")
    write(data.root / "foreign" / "2026-11-23.json", {"date": "2026-11-23", "stocks": {"FPT": {"buy_value": "1"}}})  # fields missing
    out = data.khoi_ngoai(so_phien=3, now=TU_DOANH_NOW)
    assert out["khoang"]["phien_hong"] == ["2026-11-20", "2026-11-23"] and out["khoang"]["den"] == "2026-11-19"
    assert out["toan_san"]["mua_gt"] == "5"
    _prop(data, "2026-11-19", [("FPT", 5, 1)])
    write(data.root / "proprietary" / "2026-11-23.json", {"date": "2026-11-23", "stocks": {}, "index": None})
    assert data.tu_doanh(so_phien=3, now=TU_DOANH_NOW)["khoang"]["phien_hong"] == ["2026-11-23"]


def test_an_insurer_set_against_the_other_hose_insurers(data):
    from investment_agent.market.financial_ratios import DISPLAY
    syms = ["BMI", "BVH", "MIG", "PGI", "BIC"]
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": syms, "icb_codes": {s: "8500" for s in syms},
                                                                  "icb_names": {"8500": "Bảo hiểm"}}})
    for sym, cr, q in (("BMI", "0.95", "2026-09-30"), ("BVH", "1.02", "2026-09-30"), ("MIG", "0.98", "2026-09-30"), ("PGI", "0.90", "2026-09-30"),
                       ("BIC", "0.80", "2026-06-30")):  # BIC not out for Q3
        write(data.root / "financial-ratios" / f"{sym}.json", {"symbol": sym, "kind": "insurance", "fetched_at": "t", "source": "vndirect:finfo",
                                                              "quarters": {q: {"COMBINED_RATIO_TR": cr}}})
    out = data.so_sanh_nganh("BMI")
    assert out["nganh"] == "Bảo hiểm" and out["chua_co_quy_nay"] == 1 and out["so_doanh_nghiep_nganh"] == 4
    cr = next(c for c in out["chi_so"] if c["ma_chi_so"] == "COMBINED_RATIO_TR")
    assert cr["ten"] == "Tỷ lệ kết hợp" and cr["trung_vi"] == "0.98" and cr["thu_hang"] == "3/4 (cao xuống thấp)"
    assert [c["ma_chi_so"] for c in out["chi_so"]] == [code for code, _, _ in DISPLAY["insurance"]]


def test_sector_history_gives_each_quarters_median_of_the_peers_reporting_it(data):
    from investment_agent.market.sector_compare import sector_history
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": ["KKK", "PPA", "PPB", "PPC"],
        "icb_codes": {s: "8600" for s in ("KKK", "PPA", "PPB", "PPC")}, "icb_names": {"8600": "Bất động sản"}}})
    q = {"KKK": {"2026-06-30": "0.1", "2026-09-30": "0.2"}, "PPA": {"2026-06-30": "0.05", "2026-09-30": "0.06"},
         "PPB": {"2026-06-30": "0.07", "2026-09-30": "0.08"}, "PPC": {"2026-09-30": "0.10"}}  # PPC has no Q2: two peers then
    for sym, by_q in q.items():
        write(data.root / "financial-ratios-general" / f"{sym}.json", {"symbol": sym, "kind": "general", "fetched_at": "t", "source": "vndirect:finfo",
                                                                      "quarters": {d: {"ROAE_TR_AVG4Q": v} for d, v in by_q.items()}})
    out = sector_history(data.root, "KKK", ["2026-06-30", "2026-09-30"], ("ROAE_TR_AVG4Q",))
    assert out == {"ROAE_TR_AVG4Q": [None, "0.08"]}  # Q2: under 3 peers, no point; never another quarter
    assert sector_history(data.root, "ZZZ", ["2026-09-30"]) == {}


def test_so_sanh_nganh_adds_the_tickers_own_quarters_beside_the_sector_median_of_each(data):
    write(data.root / "hose-listing.json", {"at": "t", "listing": {"symbols": ["KKK", "PPA", "PPB", "PPC"],
        "icb_codes": {s: "8600" for s in ("KKK", "PPA", "PPB", "PPC")}, "icb_names": {"8600": "Bất động sản"}}})
    q = {"KKK": {"2026-03-31": "0.09", "2026-06-30": "0.1", "2026-09-30": "0.2"}, "PPA": {"2026-06-30": "0.05", "2026-09-30": "0.06"},
         "PPB": {"2026-06-30": "0.07", "2026-09-30": "0.08"}, "PPC": {"2026-06-30": "0.09", "2026-09-30": "0.10"}}
    for sym, by_q in q.items():
        write(data.root / "financial-ratios-general" / f"{sym}.json", {"symbol": sym, "kind": "general", "fetched_at": "t", "source": "vndirect:finfo",
                                                                      "names": {"ROAE_TR_AVG4Q": "ROAE"},
                                                                      "quarters": {d: {"ROAE_TR_AVG4Q": v} for d, v in by_q.items()}})
    out = data.so_sanh_nganh("KKK", so_quy=2)
    assert out["quy"] == "2026-09-30" and out["theo_quy"]["quy"] == ["2026-06-30", "2026-09-30"]
    assert out["theo_quy"]["chi_so"]["ROAE_TR_AVG4Q"] == {"gia_tri": ["0.1", "0.2"], "trung_vi": ["0.07", "0.08"]}
    assert data.so_sanh_nganh("KKK")["theo_quy"]["quy"] == ["2026-03-31", "2026-06-30", "2026-09-30"]  # default 4, only 3 exist
    assert data.so_sanh_nganh("KKK", so_quy=99)["theo_quy"]["chi_so"]["ROAE_TR_AVG4Q"]["trung_vi"][0] is None  # Q1: no peer, clamped to 8


def test_cung_chieu_gives_the_tickers_both_bought_or_both_sold_over_the_sessions_both_stores_have(data):
    _foreign(data, "2026-11-19", [("VPB", 5, 0), ("MCH", 0, 4), ("FPT", 3, 0)])
    _foreign(data, "2026-11-20", [("VPB", 5, 0), ("MCH", 0, 4), ("FPT", 3, 0)])
    _prop(data, "2026-11-19", [("VPB", 2, 0), ("MCH", 0, 1), ("FPT", 0, 1)])
    out = data.cung_chieu(so_phien=2, now=TU_DOANH_NOW)
    assert out["khoang"]["tu"] == "2026-11-18" and out["khoang"]["den"] == "2026-11-19" and out["khoang"]["phien_bo"] == 1
    assert out["khoang"]["cham_phien"] == 5  # 20, 23, 25–27/11 closed after the newest session both stores have (24/11: holiday)
    assert out["cung_mua_rong"] == [{"ma": "VPB", "ngoai_rong_gt": "5", "tu_doanh_rong_gt": "2"}]
    assert out["cung_ban_rong"] == [{"ma": "MCH", "ngoai_rong_gt": "-4", "tu_doanh_rong_gt": "-1"}]
    assert out["don_vi"].startswith("đồng") and "watched" not in str(out)


def test_cung_chieu_without_a_common_session_says_so(data):
    _foreign(data, "2026-11-19", [("VPB", 5, 0)])
    assert data.cung_chieu(now=TU_DOANH_NOW)["thieu"] is True
