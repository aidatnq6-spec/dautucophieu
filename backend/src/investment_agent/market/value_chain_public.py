"""Chuỗi giá trị cho Claude (owner, 28/11/2026; docs/superpowers/specs/2026-11-28-chuoi-gia-tri-mcp-design.md).

Every value chain of a ticker's ICB level-2 sector, as Thị trường & Ngành scores it, with the sector's average returns and median
valuation against five years. Chains are found by sector, never by their member lists, and no member is named: 25 chains hold about the
watched tickers, so a chain per member would tell which tickers are watched. For the same reason (owner, 28/11/2026) the returns and
valuation are worked out over every HOSE ticker of the sector in price-history and index-history (all listed tickers), never over a
chain's members or the trend-sources store (watched tickers mostly), and HOSE tickers in the chains' text read "[mã]". Nothing personal
is read (held is always empty).
"""

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median

from investment_agent.market.value_chain_scores import scored_chains
from investment_agent.market.value_chains import VALUE_CHAINS_PATH, load_value_chains
from investment_agent.domain.chain_returns import chain_returns
from investment_agent.market.price_history import PriceHistoryStore
from investment_agent.market.valuation_history import own_history

LABELS = {"tailwind": "thuan_loi", "neutral": "trung_tinh", "headwind": "bat_loi", "insufficient": "chua_du_du_lieu", None: None}
STATUS = {"good": "tot", "bad": "xau", "neutral": "trung_tinh", "unknown": "chua_danh_gia", "event": "su_kien"}
DIRECTION = {"up": "tang", "down": "giam", "flat": "di_ngang", None: None}
WEIGHT = {"major": "chinh", "minor": "phu", "small": "nho"}
STAGES = {"input": "dau_vao", "middle": "trung_gian", "output": "dau_ra"}
PERIODS = {"w1": "tuan", "m1": "thang", "m3": "quy", "y1": "nam", "ytd": "tu_dau_nam"}
DRAFT_NOTE = "Chuỗi chưa được chủ sở hữu duyệt; không có nhận định tổng, chỉ có nhận định từng yếu tố."
NOTE = ("Chuỗi theo ngành ICB cấp 2 của mã, không cho biết mã có thuộc danh sách của chuỗi hay không: tự xét chuỗi nào sát với hoạt động "
        "của mã và nói rõ khi chưa chắc. Mã HOSE trong phần chữ được thay bằng [mã]. Nhận định là phép tính trên chiều 1 tháng của chỉ báo "
        "theo trọng số đã đặt, không phải dự báo. thong_ke_nganh tính trên mọi mã HOSE cùng ngành ICB cấp 2 có số trong kho, không theo "
        "chuỗi: hiệu suất là bình quân giá đã điều chỉnh, không theo vốn hóa; P/E, P/B là trung vị của số tự tính từng mã (như "
        "dinh_gia_lich_su), so_ma_thap_hon_5_nam là số mã đang thấp hơn trung vị 5 năm của chính nó, so_ma_duoi_60_thang là số mã chưa đủ 60 tháng có số trong cửa sổ 5 năm (vẫn được tính); các mã được làm mới lần lượt nên số hiện tại của từng mã có ngày khác nhau, từ ngay_cuoi_cu_nhat đến ngay_cuoi_moi_nhat. Nguồn có tên mã thì không ghi ngày. Tỷ lệ ở dạng thập phân (0,05 là 5%).")
SOURCE = "config/value-chains.json; chuỗi vĩ mô; giá đã điều chỉnh (price-history) và lịch sử định giá (index-history) trong kho"
NOT_TICKERS = {"HRC", "VND"}  # hot-rolled coil and the currency in the chains' text, also HOSE tickers


def _missing(reason: str, **extra) -> dict:
    return {"thieu": True, "ly_do": reason, **extra}


def _why_missing(m: dict | None) -> str | None:
    if m is None:
        return None
    return {"no_series": "ứng dụng chưa có chuỗi số cho chỉ báo này", "no_data": "chưa có số trong kho",
            "stale": f"số mới nhất quá {m.get('max_age_days')} ngày", "one_point": "mới có một điểm số, chưa có chiều"}.get(m["reason"], m["reason"])


def _num(v) -> Decimal | None:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if d.is_finite() else None


def _plain(d) -> str | None:
    return None if d is None else format(Decimal(d).normalize(), "f")


def sector_valuation(histories: dict[str, dict]) -> dict:
    """histories: symbol -> own_history output. Each ratio over the tickers with both a current figure and a 5-year median."""
    found = {s: h for s, h in histories.items() if not h.get("thieu")}
    days = [h["ngay_cuoi"] for h in found.values() if h.get("ngay_cuoi")]  # tickers are refreshed in turns: say both ends
    out = {"so_ma_co_dinh_gia": len(found), "ngay_cuoi_moi_nhat": max(days, default=None), "ngay_cuoi_cu_nhat": min(days, default=None)}
    for ratio in ("pe", "pb"):
        pairs = []
        for h in found.values():
            now = _num((h.get("hien_tai") or {}).get(ratio))
            window = (((h.get("cua_so") or {}).get("5_nam") or {}).get(ratio) or {})
            five = _num(window.get("trung_vi"))
            if now is not None and five is not None:
                pairs.append((now, five, window.get("so_thang") or 0))
        out[ratio] = {"hien_tai_trung_vi": _plain(median(n for n, _, _ in pairs)) if pairs else None,
                      "trung_vi_5_nam_trung_vi": _plain(median(f for _, f, _ in pairs)) if pairs else None,
                      "so_ma": len(pairs), "so_ma_thap_hon_5_nam": sum(1 for n, f, _ in pairs if n < f),
                      # counted, not left out (owner, 28/11/2026): a length threshold would mostly drop tickers with loss months
                      "so_ma_duoi_60_thang": sum(1 for _, _, m in pairs if m < 60)}
    return out


def _sector_returns(root: Path, symbols: list[str], sector: str, *, today: date) -> dict:
    store = PriceHistoryStore(root)
    closes = {}
    for s in symbols:
        rec = store.read(s) or {}
        closes[s] = [(date.fromisoformat(d), Decimal(str(v))) for d, v in rec.get("closes") or []]
    r = chain_returns([{"id": "sector", "name": sector, "symbols": symbols}], closes, today=today)[0]
    return {"so_ma_co_gia": r["priced"], "ky": {PERIODS[k]: {"thay_doi": p["change"], "so_ma": p["n"]} for k, p in r["periods"].items()},
            "phien_gan_nhat": {"tang": r["breadth"]["up"], "giam": r["breadth"]["down"], "dung": r["breadth"]["flat"]},
            "vi_tri_52_tuan": r["position_52w"]}


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
    members = sorted(s for s, c in (listing.get("icb_codes") or {}).items() if c == code)
    names = sorted((set(listing.get("symbols") or []) | set(listing.get("icb_codes") or {})) - NOT_TICKERS, key=len, reverse=True)
    tickers = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, names)) + r")(?![A-Za-z0-9])") if names else None

    def text(value):
        return tickers.sub("[mã]", value) if tickers and isinstance(value, str) else value
    sources = {k: v.model_dump(mode="json") for k, v in config.sources.items()}

    def refs(items: list[dict]) -> list[dict]:
        out = []
        for r in items or []:
            s = sources.get(r["source"]) or {}
            # company reports' titles and links name the ticker (owner, 28/11/2026): the title reads [mã], the link is left out, and
            # so is the date of a report whose title named a ticker, since publisher and date find it (review, 28/11/2026)
            title = text(s.get("title"))
            named = title != s.get("title")
            out.append({"tieu_de": title, "don_vi": s.get("publisher"), "ngay": None if named else s.get("date"), "trang": r.get("page")})
        return out

    def factor(f: dict) -> dict:
        r = f["reading"]
        return {"ten": text(f["label"]), "khau": STAGES.get(f["stage"], f["stage"]), "chi_bao": text(f.get("indicator_label") or f.get("indicator")),
                "chieu": DIRECTION.get(r["direction"]) if r else None, "tac_dong": STATUS[f["status"]], "trong_so": WEIGHT.get(f["weight"], f["weight"]),
                "so_moi_nhat": {"ngay": r["date"], "gia_tri": r["value"]} if r else None, "thay_doi": r.get("change") if r else None,
                "ly_do": text(f.get("why")), "thieu": _why_missing(f["missing"]), "nguon": refs(f.get("refs"))}

    chains = []
    for c in scored:
        approved = c["status"] == "approved"
        chains.append({
            "id": c["id"], "ten": c["name"], "da_duyet": approved, "duyet_ngay": (c["approval"] or {}).get("on") if approved else None,
            "nhan": LABELS.get(c["label"]), "ghi_chu_duyet": None if approved else DRAFT_NOTE,
            "ty_trong": {STATUS[k]: v for k, v in c["score"].items()},
            "cac_khau": {STAGES[k]: [{"ten": text(i["name"]), "ghi_chu": text(i.get("note")), "ty_trong": i.get("share"), "nguon": refs(i.get("refs"))} for i in items]
                         for k, items in c["stages"].items()},
            "yeu_to": [factor(f) for f in c["factors"]]})
    stats = {"so_ma_nganh": len(members), "hieu_suat": _sector_returns(root, members, sector, today=today),
             "dinh_gia": sector_valuation({s: own_history(root, s) for s in members})}
    return {"ma": symbol, "nganh": sector, "ngay": today.isoformat(), "chuoi": chains, "thong_ke_nganh": stats, "nguon": SOURCE, "luu_y": NOTE}
