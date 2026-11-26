"""MCP dữ liệu công khai: read-only views of the public market files under data/, for Claude.

Nothing here touches Firestore or any personal record (ledger, holdings, cost, watchlist, theses, the owner's valuations): only
market files fetched from public sources. Figures are returned as stored, with their source and time; a missing file or a bad
argument comes back as {"thieu": true, "ly_do": ...}, never as a guess. There is deliberately no listing of the tickers that have
company or event files, since that list follows what the app tracks.
"""

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

from investment_agent.market.prices import PriceStore

REPO_ROOT = Path(__file__).resolve().parents[3]
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_SERIES = re.compile(r"^[a-z][a-z0-9_]{0,63}$")  # _status, _gaps… are run bookkeeping, not series
INDEXES = ("VNINDEX", "VN30")
LINE_NAMES = REPO_ROOT / "config" / "statement-line-names.json"  # each stored line's own name in VNDirect's financial_models
# What the stored lines cover (statements.py: equity includes non-controlling interests in every layout)
SCOPE = {"npat": "LNST của cả doanh nghiệp, gồm phần của cổ đông không kiểm soát",
         "npat_parent": "LNST thuộc cổ đông công ty mẹ; dùng dòng này cho EPS và P/E",
         "equity": "Vốn chủ sở hữu GỒM lợi ích cổ đông không kiểm soát (minority_equity); vốn chủ của công ty mẹ = equity − minority_equity",
         "minority_equity": "Lợi ích cổ đông không kiểm soát, một phần của equity",
         "don_vi": "đồng; eps là đồng/cổ phiếu; chi phí, dòng tiền chi ra và dự phòng giữ dấu như VNDirect"}
FUNDAMENTAL_NOTES = {"npat": "LNST thuộc cổ đông công ty mẹ (dòng npat_parent của BCTC)",
                     "eps": "Lãi cơ bản trên cổ phiếu do VNDirect công bố, đồng/cổ phiếu",
                     "equity": "Vốn chủ sở hữu GỒM lợi ích cổ đông không kiểm soát; trừ loi_ich_thieu_so cùng kỳ để ra vốn chủ của công ty mẹ",
                     "annual": "Các dòng năm của BCTC, đồng; selling và admin mang dấu âm"}
VALUATION_FIELDS = (("ngay", "date"), ("lay_luc", "fetched_at"), ("von_hoa", "market_cap"), ("pe", "pe"), ("pb", "pb"),
                    ("so_co_phieu", "shares"), ("quy_loi_nhuan", "profit_quarter"))
RATIOS = ("pe", "pb")


def default_data_dir() -> Path:
    return Path(os.environ.get("INVESTMENT_DATA_DIR") or REPO_ROOT / "data").resolve()


def _missing(reason: str) -> dict:
    return {"thieu": True, "ly_do": reason}


def _count(value, default: int, cap: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, cap))


def _newest(periods: dict | None, n: int) -> dict:
    return {k: (periods or {})[k] for k in sorted(periods or {})[-n:]}


class PublicData:
    def __init__(self, data_dir: Path | str):
        self.root = Path(data_dir)

    def _json(self, *parts: str):
        path = self.root.joinpath(*parts)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def _written_at(self, *parts: str) -> str | None:
        """When the file was last written, for files that keep no fetch time of their own; a write time, not a source's publish time."""
        path = self.root.joinpath(*parts)
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else None

    @staticmethod
    def _symbol(value) -> str | None:
        s = str(value or "").strip().upper()
        return s if _SYMBOL.fullmatch(s) else None

    def _per_symbol(self, folder: str, value, what: str):
        symbol = self._symbol(value)
        if symbol is None:
            return None, _missing("Mã không hợp lệ.")
        record = self._json(folder, f"{symbol}.json")
        if record is None:
            return None, _missing(f"Chưa có {what} của {symbol} trong kho.")
        return record, None

    # Giá và chỉ số
    def thong_tin_ma(self, ma) -> dict:
        symbol = self._symbol(ma)
        if symbol is None:
            return _missing("Mã không hợp lệ.")
        listing = self._json("hose-listing.json") or {}
        industries = self._json("industries.json") or {}
        groups = self._json("index-groups.json") or {}
        return {"ma": symbol, "niem_yet_hose": symbol in (listing.get("listing") or {}).get("symbols", []),
                "nganh_icb": (industries.get("sectors") or {}).get(symbol),
                "nhom_chi_so": [g for g, members in (groups.get("groups") or {}).items() if symbol in members],
                "nguon": {"niem_yet": listing.get("at"), "nganh": industries.get("as_of"), "nhom": groups.get("as_of")}}

    def gia_ngay(self, ma, tu_ngay=None, den_ngay=None, so_phien=60) -> dict:
        symbol = self._symbol(ma)
        if symbol is None:
            return _missing("Mã không hợp lệ.")
        try:
            start = date.fromisoformat(tu_ngay) if tu_ngay else None
            end = date.fromisoformat(den_ngay) if den_ngay else None
        except (TypeError, ValueError):
            return _missing("Ngày phải theo dạng YYYY-MM-DD.")
        view = PriceStore(self.root).latest(symbol)
        if not view:
            return _missing(f"Chưa có giá ngày của {symbol} trong kho.")
        days = [d for d in sorted(view) if (start is None or d >= start) and (end is None or d <= end)][-_count(so_phien, 60, 500):]
        if not days:
            return _missing(f"Không có phiên nào của {symbol} trong khoảng ngày này.")
        last = view[days[-1]][0]
        rows = [{"ngay": d.isoformat(), "mo": str(b.open), "cao": str(b.high), "thap": str(b.low), "dong": str(b.close), "khoi_luong": b.volume}
                for d, b in ((d, view[d][0]) for d in days)]
        return {"ma": symbol, "don_vi": last.currency, "co_so_gia": last.price_basis, "nguon": last.source_id,
                "lay_luc": last.observed_at.isoformat(), "phien_moi_nhat_trong_kho": max(view).isoformat(), "phien": rows}

    def dinh_gia_chi_so(self, chi_so="VNINDEX", ty_le="pe", so_diem=60) -> dict:
        index, ratio = str(chi_so or "").upper(), str(ty_le or "").lower()
        if index not in INDEXES or ratio not in RATIOS:
            return _missing("Chỉ có VNINDEX hoặc VN30, tỷ lệ pe hoặc pb.")
        series = self._json("index-valuation", f"{index}-{ratio}-1d.json")
        if not series:
            return _missing(f"Chưa có {ratio.upper()} của {index} trong kho.")
        return {"chi_so": index, "ty_le": ratio, "nguon": "VNDirect", "tep_cap_nhat_luc": self._written_at("index-valuation", f"{index}-{ratio}-1d.json"),
                "diem": series.get("points", [])[-_count(so_diem, 60, 1000):]}

    # Báo cáo tài chính
    def bao_cao_tai_chinh(self, ma, ky="quy", so_ky=8) -> dict:
        symbol = self._symbol(ma)
        if symbol is None:
            return _missing("Mã không hợp lệ.")
        if ky not in ("quy", "nam"):
            return _missing("Kỳ phải là quy hoặc nam.")
        record = self._json("statements-financial", f"{symbol}.json") or self._json("statements", f"{symbol}.json")
        if record is None:
            return _missing(f"Chưa có BCTC của {symbol} trong kho.")
        kept = _newest(record.get("quarters" if ky == "quy" else "years"), _count(so_ky, 8, 80))
        names = (json.loads(LINE_NAMES.read_text(encoding="utf-8")) if LINE_NAMES.is_file() else {}).get(record.get("kind") or "general") or {}
        lines = {line for row in kept.values() for line in row}
        return {"ma": symbol, "loai": record.get("kind"), "nguon": record.get("source"), "lay_luc": record.get("fetched_at"),
                "don_vi": "đồng", "pham_vi": SCOPE, "ten_dong": {k: names[k] for k in sorted(lines) if k in names}, "ky": kept}

    def chi_so_tai_chinh(self, ma, so_ky=8) -> dict:
        record, missing = self._per_symbol("financial-ratios", ma, "chỉ số tài chính")
        if missing:
            return missing
        return {"ma": record.get("symbol"), "loai": record.get("kind"), "nguon": record.get("source"), "lay_luc": record.get("fetched_at"),
                "ky": _newest(record.get("quarters"), _count(so_ky, 8, 80))}

    def eps_co_tuc(self, ma, so_ky=8) -> dict:
        record, missing = self._per_symbol("fundamentals", ma, "dữ liệu cơ bản")
        if missing:
            return missing
        n = _count(so_ky, 8, 80)
        out = {**record, **{k: _newest(record.get(k), n) for k in ("years", "quarters", "annual") if k in record}}
        statements = self._json("statements-financial", f"{record.get('symbol')}.json") or self._json("statements", f"{record.get('symbol')}.json") or {}
        minority = {kind: {p: (statements.get(kind) or {}).get(p, {}).get("minority_equity") for p in out.get(kind) or {}
                           if (statements.get(kind) or {}).get(p, {}).get("minority_equity") is not None}
                    for kind in ("years", "quarters")}
        return {**out, "chu_thich": FUNDAMENTAL_NOTES, "loi_ich_thieu_so": minority}

    def dinh_gia_ma(self, ma) -> dict:
        record, missing = self._per_symbol("valuation-check", ma, "định giá VNDirect công bố")
        if missing:
            return missing
        return {"ma": self._symbol(ma), "nguon": "VNDirect", **{name: record.get(src) for name, src in VALUATION_FIELDS}}

    # Doanh nghiệp
    def su_kien_doanh_nghiep(self, ma) -> dict:
        record, missing = self._per_symbol("events", ma, "sự kiện doanh nghiệp")
        return missing or record

    def co_dong_ban_lanh_dao(self, ma) -> dict:
        record, missing = self._per_symbol("company", ma, "cổ đông và ban lãnh đạo")
        return missing or record

    def giao_dich_noi_bo(self, ma) -> dict:
        record, missing = self._per_symbol("insider", ma, "giao dịch nội bộ")
        return missing or record

    # Vĩ mô và thế giới
    def _series_names(self) -> list[str]:
        folder = self.root / "macro"
        return sorted(p.stem for p in folder.glob("*.json") if _SERIES.fullmatch(p.stem)) if folder.is_dir() else []

    def danh_sach_vi_mo(self) -> dict:
        status = self._json("macro", "_status.json") or {}
        return {"chi_bao": [{"ma": s, "trang_thai": (status.get(s) or {}).get("status"), "cap_nhat": (status.get(s) or {}).get("at")}
                            for s in self._series_names()]}

    def chi_bao_vi_mo(self, ma, so_diem=24) -> dict:
        name = str(ma or "")
        if name not in self._series_names():
            return _missing("Không có chỉ báo này; xem danh_sach_vi_mo.")
        record = self._json("macro", f"{name}.json") or {}
        return {"ma": name, "quan_sat": (record.get("observations") or [])[-_count(so_diem, 24, 1000):]}

    def chi_so_chau_a(self) -> dict:
        return self._json("macro", "asia-indices.json") or _missing("Chưa có chỉ số châu Á trong kho.")

    def gia_vang(self) -> dict:
        return self._json("gold-price.json") or _missing("Chưa có giá vàng trong kho.")

    def gia_vang_lich_su(self, loai=None, so_ngay=30) -> dict:
        history = self._json("gold-price-history.json")
        if not history:
            return _missing("Chưa có lịch sử giá vàng trong kho.")
        if not loai:
            return {"nguon": "Phú Quý", "tep_cap_nhat_luc": self._written_at("gold-price-history.json"), "loai": sorted(history)}
        if loai not in history:
            return _missing("Không có loại vàng này; gọi không kèm loai để xem danh sách.")
        points = sorted(history[loai].items())[-_count(so_ngay, 30, 1000):]
        return {"loai": loai, "gia": "mua", "don_vi": "đồng/chỉ", "nguon": "Phú Quý", "tep_cap_nhat_luc": self._written_at("gold-price-history.json"),
                "diem": [list(p) for p in points]}

    # Quỹ mở (Fmarket, toàn thị trường). fund-scores.json is the app's own scoring and stays out.
    def quy_mo(self, ma=None, so_ngay=30) -> dict:
        navs = self._json("fund-nav.json")
        if not navs:
            return _missing("Chưa có NAV quỹ mở trong kho.")
        funds, profiles = navs.get("funds") or {}, navs.get("profiles") or {}
        if not ma:
            return {"nguon": navs.get("source"), "lay_luc": navs.get("fetched_at"),
                    "quy": [{"ma": code, "ten": f.get("name"), "loai": (profiles.get(code) or {}).get("kind"), "nav": f.get("nav"), "ngay": f.get("date")}
                            for code, f in sorted(funds.items())]}
        code = str(ma).strip().upper()
        if code not in funds:
            return _missing("Không có quỹ này; gọi không kèm ma để xem danh sách.")
        history = (self._json("fund-nav-history.json") or {}).get(code) or {}
        holdings = self._json("fund-holdings.json") or {}
        return {"ma": code, "nguon": navs.get("source"), "lay_luc": navs.get("fetched_at"), "nav": funds[code], "ho_so": profiles.get(code),
                "lich_su_nav": _newest(history, _count(so_ngay, 30, 1000)),
                "danh_muc_cong_bo": (holdings.get("funds") or {}).get(code), "danh_muc_lay_luc": holdings.get("fetched_at")}

    def omo(self, so_phien=5) -> dict:
        record = self._json("omo.json")
        if not record:
            return _missing("Chưa có số OMO trong kho.")
        return {"tep_cap_nhat_luc": self._written_at("omo.json"), "sessions": sorted(record.get("sessions", []), key=lambda s: s.get("date", ""))[-_count(so_phien, 5, 60):]}
