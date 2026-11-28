"""Chuỗi giá trị cho Claude (docs/superpowers/specs/2026-11-28-chuoi-gia-tri-mcp-design.md): chains by the ticker's ICB sector, never a member."""

import json
from datetime import date, timedelta

import pytest

from investment_agent.market.leading import MacroStore
from investment_agent.public_tools import PublicData
from investment_agent.services import value_chain_approvals as approvals
from investment_agent.market.value_chain_public import chains_for_sector, sector_valuation

TODAY = date(2027, 1, 15)
SOURCE = {"title": "Cập nhật HSG – MUA", "publisher": "ACBS", "date": "2026-10-28", "url": "https://acbs.com.vn/HSG_x.pdf"}
REF = [{"source": "acbs-ht1", "page": 3}]
ITEM = {"name": "Quặng sắt (HPG)", "note": "HSG lấy HRC nhập khẩu", "share": None, "basis": None, "refs": REF}


def factor(fid, indicator, when_up="bad", weight="major"):
    return {"id": fid, "label": f"Yếu tố {fid} theo VND", "stage": "input", "indicator": indicator, "when_up": when_up, "weight": weight, "share": None,
            "why": "lý do", "refs": REF}


def chain(cid, symbols, status, factors):
    return {"id": cid, "name": cid.title(), "icb": "Tài nguyên Cơ bản", "status": status, "symbols": symbols,
            "stages": {"input": [ITEM], "middle": [ITEM], "output": [ITEM]}, "factors": factors}


@pytest.fixture
def env(tmp_path):
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "t", "listing": {
        "symbols": ["HPG", "HSG", "NKG", "HRC", "VND", "DHG"], "icb_codes": {"HPG": "1700", "HSG": "1700", "NKG": "1700", "HRC": "1300", "VND": "8700", "DHG": "4500"},
        "icb_names": {"1700": "Tài nguyên Cơ bản", "4500": "Y tế"}}}, ensure_ascii=False), encoding="utf-8")
    MacroStore(tmp_path).upsert("wti", [(TODAY - timedelta(days=35), "60"), (TODAY - timedelta(days=1), "66")], entry="auto")
    doc = {"version": "t", "sources": {"acbs-ht1": SOURCE}, "chains": [
        chain("steel", ["HPG"], "approved", [factor("oil", "wti")]),
        chain("coated", ["HSG"], "draft", [factor("oil", "wti"), factor("coke", None, weight="minor")])]}
    path = tmp_path / "value-chains.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return tmp_path, path


def test_a_ticker_gets_every_chain_of_its_sector_and_never_a_member_name(env):
    root, path = env
    out = chains_for_sector(root, "HPG", today=TODAY, config_path=path)
    assert [c["id"] for c in out["chuoi"]] == ["steel", "coated"] and out["nganh"] == "Tài nguyên Cơ bản" and out["ma"] == "HPG"
    assert "HPG" not in json.dumps(out["chuoi"]) and "HSG" not in json.dumps(out)
    assert out["chuoi"][0]["yeu_to"][0]["ten"] == "Yếu tố oil theo VND"  # VND: the currency, also a HOSE ticker, kept
    assert chains_for_sector(root, "HSG", today=TODAY, config_path=path)["chuoi"] == out["chuoi"]
    stage = out["chuoi"][0]["cac_khau"]["dau_vao"][0]
    assert stage == {"ten": "Quặng sắt ([mã])", "ghi_chu": "[mã] lấy HRC nhập khẩu", "ty_trong": None,  # HRC: hot-rolled coil, kept
                     "nguon": [{"tieu_de": "Cập nhật [mã] – MUA", "don_vi": "ACBS", "ngay": None, "trang": 3}]}  # no URL, no date: they find the report
    assert out["ngay"] == "2027-01-15" and "không theo vốn hóa" in out["luu_y"]


def test_a_draft_has_factor_readings_but_no_label(env):
    root, path = env
    steel, coated = chains_for_sector(root, "HPG", today=TODAY, config_path=path)["chuoi"]
    assert coated["da_duyet"] is False and coated["nhan"] is None and "chưa được chủ sở hữu duyệt" in coated["ghi_chu_duyet"]
    assert steel["da_duyet"] is True and steel["nhan"] == "bat_loi" and steel["ghi_chu_duyet"] is None
    oil = steel["yeu_to"][0]
    assert (oil["chieu"], oil["tac_dong"], oil["trong_so"], oil["so_moi_nhat"]["gia_tri"], oil["thieu"]) == ("tang", "xau", "chinh", "66", None)
    assert steel["ty_trong"] == {"tot": "0.0000", "xau": "1.0000", "trung_tinh": "0.0000", "chua_danh_gia": "0.0000"}


def test_a_factor_without_a_series_says_why(env):
    root, path = env
    coke = chains_for_sector(root, "HPG", today=TODAY, config_path=path)["chuoi"][1]["yeu_to"][1]
    assert coke["tac_dong"] == "chua_danh_gia" and coke["thieu"] == "ứng dụng chưa có chuỗi số cho chỉ báo này" and coke["so_moi_nhat"] is None


def _closes(root, symbol, pairs):
    path = root / "price-history" / f"{symbol}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"symbol": symbol, "adjusted": True, "unit": "nghìn đồng", "closes": pairs}), encoding="utf-8")


def test_sector_returns_cover_every_hose_ticker_of_the_sector_not_the_chain_members(env):
    root, path = env
    month = (TODAY - timedelta(days=31)).isoformat()
    for symbol, now in (("HPG", "11"), ("NKG", "13"), ("DHG", "50")):  # NKG is in no chain; DHG is another sector
        _closes(root, symbol, [[month, "10"], [(TODAY - timedelta(days=1)).isoformat(), now]])
    out = chains_for_sector(root, "HPG", today=TODAY, config_path=path)
    stats = out["thong_ke_nganh"]
    assert stats["so_ma_nganh"] == 3 and stats["hieu_suat"]["so_ma_co_gia"] == 2
    assert stats["hieu_suat"]["ky"]["thang"] == {"thay_doi": "0.2000", "so_ma": 2}  # (0.1 + 0.3) / 2, 4 places as chain_returns gives it
    assert all(k not in out["chuoi"][0] for k in ("so_ma", "hieu_suat", "dinh_gia"))


def test_a_sector_without_prices_or_valuations_gives_empty_stats(env):
    root, path = env
    stats = chains_for_sector(root, "HPG", today=TODAY, config_path=path)["thong_ke_nganh"]
    assert stats["hieu_suat"]["so_ma_co_gia"] == 0 and stats["hieu_suat"]["ky"]["thang"] == {"thay_doi": None, "so_ma": 0}
    assert stats["dinh_gia"]["pe"] == {"hien_tai_trung_vi": None, "trung_vi_5_nam_trung_vi": None, "so_ma": 0, "so_ma_thap_hon_5_nam": 0,
                                       "so_ma_duoi_60_thang": 0}
    assert stats["dinh_gia"]["ngay_cuoi_cu_nhat"] is None


def test_sector_valuation_is_the_median_of_each_tickers_own_figures():
    def own(pe, pe5, pb, pb5, day="2027-01-14", months=60):
        return {"ngay_cuoi": day, "hien_tai": {"pe": pe, "pb": pb},
                "cua_so": {"5_nam": {"pe": {"trung_vi": pe5, "so_thang": months}, "pb": {"trung_vi": pb5, "so_thang": months}}}}
    out = sector_valuation({"A": own("8", "10", "1", "1.2", months=30), "B": own("12", "11", "2", "1.5", day="2026-12-20"),
                            "C": own(None, "9", "1.5", None), "D": {"thieu": True, "ly_do": "x"}})
    assert out["pe"] == {"hien_tai_trung_vi": "10", "trung_vi_5_nam_trung_vi": "10.5", "so_ma": 2, "so_ma_thap_hon_5_nam": 1, "so_ma_duoi_60_thang": 1}
    assert out["pb"] == {"hien_tai_trung_vi": "1.5", "trung_vi_5_nam_trung_vi": "1.35", "so_ma": 2, "so_ma_thap_hon_5_nam": 1, "so_ma_duoi_60_thang": 1}
    assert out["so_ma_co_dinh_gia"] == 3 and out["ngay_cuoi_moi_nhat"] == "2027-01-14" and out["ngay_cuoi_cu_nhat"] == "2026-12-20"


def test_a_sector_without_a_chain_says_so(env):
    root, path = env
    assert chains_for_sector(root, "DHG", today=TODAY, config_path=path) == {
        "thieu": True, "ly_do": "Chưa có chuỗi giá trị cho ngành Y tế.", "ma": "DHG", "nganh": "Y tế"}


def test_a_ticker_without_a_sector_or_invalid_is_missing(env):
    root, path = env
    zzz = chains_for_sector(root, "ZZZ", today=TODAY, config_path=path)
    assert zzz["thieu"] is True and "Chưa có ngành ICB của ZZZ" in zzz["ly_do"]
    data = PublicData(root)
    assert data.chuoi_gia_tri("!!", today=TODAY, config_path=path)["thieu"] is True
    assert data.chuoi_gia_tri(" hpg ", today=TODAY, config_path=path)["ma"] == "HPG"


def test_an_app_approval_of_older_content_is_not_approved(env):
    root, path = env
    approvals.approve(root, "coated", fingerprint="old", note=None, on=TODAY)
    coated = chains_for_sector(root, "HPG", today=TODAY, config_path=path)["chuoi"][1]
    assert coated["da_duyet"] is False and coated["nhan"] is None


def test_the_kept_words_never_stand_for_a_member_of_the_same_chain_in_the_committed_chains():
    # HRC and VND stay as words (hot-rolled coil, the currency); a chain listing one of them as a member must not write it in its text
    import re
    from investment_agent.market.value_chain_public import NOT_TICKERS
    from investment_agent.market.value_chains import VALUE_CHAINS_PATH, load_value_chains
    config = load_value_chains(VALUE_CHAINS_PATH)
    for c in config.chains:
        kept = NOT_TICKERS & set(c.symbols)
        if not kept:
            continue
        dump = c.model_dump(mode="json")
        text = json.dumps([dump["name"], dump["stages"], [(f["label"], f["why"]) for f in dump["factors"]],
                           [config.sources[r["source"]].title for f in dump["factors"] for r in f["refs"]]], ensure_ascii=False)
        assert not any(re.search(rf"(?<![A-Za-z]){w}(?![A-Za-z])", text) for w in kept), (c.id, kept)


def test_a_chain_name_with_a_ticker_reads_ma(env):
    root, path = env
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["chains"][0]["name"] = "Thép (HPG)"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert chains_for_sector(root, "HSG", today=TODAY, config_path=path)["chuoi"][0]["ten"] == "Thép ([mã])"


def test_a_ticker_joined_to_digits_reads_ma_but_a_longer_word_is_kept(env):
    root, path = env
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["chains"][0]["stages"]["input"][0]["note"] = "HPG2025 tăng; HPGX và AHPG là chữ khác"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    note = chains_for_sector(root, "HSG", today=TODAY, config_path=path)["chuoi"][0]["cac_khau"]["dau_vao"][0]["ghi_chu"]
    assert note == "[mã]2025 tăng; HPGX và AHPG là chữ khác"


def test_an_unreadable_price_or_valuation_file_counts_as_no_figure(env):
    root, path = env
    _closes(root, "HPG", [[(TODAY - timedelta(days=31)).isoformat(), "10"], [(TODAY - timedelta(days=1)).isoformat(), "11"]])
    (root / "price-history" / "NKG.json").write_text("{not json", encoding="utf-8")
    _closes(root, "HSG", [["2027-13-40", "x"]])
    (root / "index-history").mkdir()
    (root / "index-history" / "HPG.json").write_text("{not json", encoding="utf-8")
    stats = chains_for_sector(root, "HPG", today=TODAY, config_path=path)["thong_ke_nganh"]
    assert stats["hieu_suat"]["so_ma_co_gia"] == 1 and stats["dinh_gia"]["so_ma_co_dinh_gia"] == 0
