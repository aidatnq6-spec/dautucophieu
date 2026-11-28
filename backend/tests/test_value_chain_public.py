"""Chuỗi giá trị cho Claude (docs/superpowers/specs/2026-11-28-chuoi-gia-tri-mcp-design.md): chains by the ticker's ICB sector, never a member."""

import json
from datetime import date, timedelta

import pytest

from investment_agent.market.leading import MacroStore
from investment_agent.public_tools import PublicData
from investment_agent.services import value_chain_approvals as approvals
from investment_agent.market.value_chain_public import chains_for_sector

TODAY = date(2027, 1, 15)
SOURCE = {"title": "Câu chuyện đầu tư HT1", "publisher": "ACBS", "date": "2026-10-28", "url": "https://acbs.com.vn/x.pdf"}
REF = [{"source": "acbs-ht1", "page": 3}]
ITEM = {"name": "Quặng sắt", "note": "nhập khẩu", "share": None, "basis": None, "refs": REF}


def factor(fid, indicator, when_up="bad", weight="major"):
    return {"id": fid, "label": f"Yếu tố {fid}", "stage": "input", "indicator": indicator, "when_up": when_up, "weight": weight, "share": None,
            "why": "lý do", "refs": REF}


def chain(cid, symbols, status, factors):
    return {"id": cid, "name": cid.title(), "icb": "Tài nguyên Cơ bản", "status": status, "symbols": symbols,
            "stages": {"input": [ITEM], "middle": [ITEM], "output": [ITEM]}, "factors": factors}


@pytest.fixture
def env(tmp_path):
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "t", "listing": {
        "symbols": ["HPG", "HSG", "DHG"], "icb_codes": {"HPG": "1700", "HSG": "1700", "DHG": "4500"},
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
    assert chains_for_sector(root, "HSG", today=TODAY, config_path=path)["chuoi"] == out["chuoi"]
    stage = out["chuoi"][0]["cac_khau"]["dau_vao"][0]
    assert stage == {"ten": "Quặng sắt", "ghi_chu": "nhập khẩu", "ty_trong": None,
                     "nguon": [{"tieu_de": "Câu chuyện đầu tư HT1", "don_vi": "ACBS", "ngay": "2026-10-28", "trang": 3, "url": "https://acbs.com.vn/x.pdf"}]}
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


def test_members_without_prices_give_empty_returns_and_valuation(env):
    root, path = env
    steel = chains_for_sector(root, "HPG", today=TODAY, config_path=path)["chuoi"][0]
    assert steel["so_ma"] == 1 and steel["hieu_suat"]["so_ma_co_gia"] == 0
    assert steel["hieu_suat"]["ky"]["thang"] == {"thay_doi": None, "so_ma": 0}
    assert steel["dinh_gia"]["so_ma_co_dinh_gia"] == 0 and steel["dinh_gia"]["pe"]["hien_tai"] is None


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
