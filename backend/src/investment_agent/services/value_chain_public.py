"""Chuỗi giá trị cho Claude (owner, 28/11/2026; docs/superpowers/specs/2026-11-28-chuoi-gia-tri-mcp-design.md).

Every value chain of a ticker's ICB level-2 sector, as Thị trường & Ngành scores it, with the chain's average returns and median valuation
against five years. Chains are found by sector, never by their member lists, and no member is named: 25 chains hold about the watched
tickers, so a chain per member would tell which tickers are watched. Nothing personal is read (held is always empty).
"""

import json
from datetime import date
from pathlib import Path

from investment_agent.api.routes.value_chains import scored_chains
from investment_agent.market.value_chains import VALUE_CHAINS_PATH, load_value_chains
from investment_agent.services.chain_valuation import chain_valuation_board
from investment_agent.services.flow_board import chain_board

LABELS = {"tailwind": "thuan_loi", "neutral": "trung_tinh", "headwind": "bat_loi", "insufficient": "chua_du_du_lieu", None: None}
STATUS = {"good": "tot", "bad": "xau", "neutral": "trung_tinh", "unknown": "chua_danh_gia", "event": "su_kien"}
DIRECTION = {"up": "tang", "down": "giam", "flat": "di_ngang", None: None}
WEIGHT = {"major": "chinh", "minor": "phu", "small": "nho"}
STAGES = {"input": "dau_vao", "middle": "trung_gian", "output": "dau_ra"}
PERIODS = {"w1": "tuan", "m1": "thang", "m3": "quy", "y1": "nam", "ytd": "tu_dau_nam"}
DRAFT_NOTE = "Chuỗi chưa được chủ sở hữu duyệt; không có nhận định tổng, chỉ có nhận định từng yếu tố."
NOTE = ("Chuỗi theo ngành ICB cấp 2 của mã, không cho biết mã có thuộc danh sách của chuỗi hay không: tự xét chuỗi nào sát với hoạt động "
        "của mã và nói rõ khi chưa chắc. Nhận định là phép tính trên chiều 1 tháng của chỉ báo theo trọng số đã đặt, không phải dự báo. "
        "Hiệu suất là bình quân các mã của chuỗi, không theo vốn hóa; P/E, P/B là trung vị. Tỷ lệ ở dạng thập phân (0,05 là 5%).")
SOURCE = "config/value-chains.json; chuỗi vĩ mô, giá đóng cửa và định giá trong kho"


def _missing(reason: str, **extra) -> dict:
    return {"thieu": True, "ly_do": reason, **extra}


def _why_missing(m: dict | None) -> str | None:
    if m is None:
        return None
    return {"no_series": "ứng dụng chưa có chuỗi số cho chỉ báo này", "no_data": "chưa có số trong kho",
            "stale": f"số mới nhất quá {m.get('max_age_days')} ngày", "one_point": "mới có một điểm số, chưa có chiều"}.get(m["reason"], m["reason"])


def chains_for_sector(data_dir: Path, symbol: str, *, today: date, config_path: Path = VALUE_CHAINS_PATH) -> dict:
    root = Path(data_dir)
    path = root / "hose-listing.json"
    listing = (json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}).get("listing") or {}
    code = (listing.get("icb_codes") or {}).get(symbol)
    if code is None:
        return _missing(f"Chưa có ngành ICB của {symbol} trong danh sách HOSE.", ma=symbol)
    sector = (listing.get("icb_names") or {}).get(code, code)
    config = load_value_chains(config_path)
    own = [c for c in config.chains if c.icb == sector]
    if not own:
        return _missing(f"Chưa có chuỗi giá trị cho ngành {sector}.", ma=symbol, nganh=sector)
    ids = {c.id for c in own}
    scored = [c for c in scored_chains(root, config, today=today, held=set()) if c["id"] in ids]
    plain = [{"id": c.id, "name": c.name, "symbols": list(c.symbols)} for c in own]
    returns = {r["id"]: r for r in chain_board(root, plain, today=today)}
    valuation = {r["id"]: r for r in chain_valuation_board(root, plain, today=today)}
    sources = {k: v.model_dump(mode="json") for k, v in config.sources.items()}

    def refs(items: list[dict]) -> list[dict]:
        out = []
        for r in items or []:
            s = sources.get(r["source"]) or {}
            out.append({"tieu_de": s.get("title"), "don_vi": s.get("publisher"), "ngay": s.get("date"), "trang": r.get("page"), "url": s.get("url")})
        return out

    def factor(f: dict) -> dict:
        r = f["reading"]
        return {"ten": f["label"], "khau": STAGES.get(f["stage"], f["stage"]), "chi_bao": f.get("indicator_label") or f.get("indicator"),
                "chieu": DIRECTION.get(r["direction"]) if r else None, "tac_dong": STATUS[f["status"]], "trong_so": WEIGHT.get(f["weight"], f["weight"]),
                "so_moi_nhat": {"ngay": r["date"], "gia_tri": r["value"]} if r else None, "thay_doi": r.get("change") if r else None,
                "ly_do": f.get("why"), "thieu": _why_missing(f["missing"]), "nguon": refs(f.get("refs"))}

    def side(v: dict) -> dict:
        return {"hien_tai": v.get("now"), "trung_vi_5_nam": v.get("median_5y"), "vi_tri": v.get("position"), "so_ma": v.get("n"), "so_tuan": v.get("weeks")}

    chains = []
    for c in scored:
        ret, val = returns[c["id"]], valuation[c["id"]]
        approved = c["status"] == "approved"
        chains.append({
            "id": c["id"], "ten": c["name"], "da_duyet": approved, "duyet_ngay": (c["approval"] or {}).get("on") if approved else None,
            "nhan": LABELS.get(c["label"]), "ghi_chu_duyet": None if approved else DRAFT_NOTE,
            "ty_trong": {STATUS[k]: v for k, v in c["score"].items()},
            "cac_khau": {STAGES[k]: [{"ten": i["name"], "ghi_chu": i.get("note"), "ty_trong": i.get("share"), "nguon": refs(i.get("refs"))} for i in items]
                         for k, items in c["stages"].items()},
            "yeu_to": [factor(f) for f in c["factors"]],
            "so_ma": ret["members"],
            "hieu_suat": {"so_ma_co_gia": ret["priced"], "ky": {PERIODS[k]: {"thay_doi": p["change"], "so_ma": p["n"]} for k, p in ret["periods"].items()},
                          "phien_gan_nhat": {"tang": ret["breadth"]["up"], "giam": ret["breadth"]["down"], "dung": ret["breadth"]["flat"]},
                          "vi_tri_52_tuan": ret["position_52w"]},
            "dinh_gia": {"so_ma_co_dinh_gia": val["priced"], "pe": side(val["pe"]), "pb": side(val["pb"]), "tu_ngay": val["since"]}})
    return {"ma": symbol, "nganh": sector, "ngay": today.isoformat(), "chuoi": chains, "nguon": SOURCE, "luu_y": NOTE}
