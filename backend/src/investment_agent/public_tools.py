"""MCP dữ liệu công khai: read-only views of the public market files under data/, for Claude.

Nothing here touches Firestore or any personal record (ledger, holdings, cost, watchlist, theses, the owner's valuations): only
market files fetched from public sources. Figures are returned as stored, with their source and time; a missing file or a bad
argument comes back as {"thieu": true, "ly_do": ...}, never as a guess. There is deliberately no listing of the tickers that have
company or event files, since that list follows what the app tracks.
"""

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from investment_agent.market.price_history import read_index_sessions
from investment_agent.market.company_notes import NOTE_GROUPS, NOTE_LABELS
from investment_agent.market.insider_docs import DocStore, fill_from_docs
from investment_agent.market.prices import PriceStore
from investment_agent.market.valuation_history import own_history
from investment_agent.market.sector_compare import compare_sector
from investment_agent.market.report_flags import EPS_JUMP, eps_jumps, outside_sales_flag

REPO_ROOT = Path(__file__).resolve().parents[3]
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_SERIES = re.compile(r"^[a-z][a-z0-9_]{0,63}$")  # _status, _gaps… are run bookkeeping, not series
INDEXES = ("VNINDEX", "VN30")
MAX_DAILY = 800  # daily adjusted closes per answer
GENERAL_RATIO_NOTE = ("Số do VNDirect tự tính, giữ nguyên. Tỷ lệ, biên và tăng trưởng ở dạng thập phân (0,08 là 8%); DSO, DIO, DPO và chu kỳ "
                      "vận động vốn là số ngày; EPS_TR, BVPS_AQ là đồng; các hệ số thanh toán và DEBT_EBITDA là số lần. Quý có doanh thu rất "
                      "nhỏ làm số ngày và biên lệch rất xa: nói rõ khi gặp, không bỏ đi. EPS_TR, BVPS_AQ và các chỉ số trên mỗi cổ phiếu dùng số cổ phiếu cuối quý "
                      "của VNDirect: có đợt thưởng hay phát hành sau quý đó thì không so trực tiếp với giá hiện tại mà nói rõ hai số cổ phiếu.")
def _sessions(start: date, end: date, data_dir: Path) -> tuple[set[date], str | None]:
    """HOSE sessions between start and end from the official calendar files in config/ (the years that exist); before the first of them,
    the days VN-Index traded at VNDirect (owner, 26/11/2026), said to be no official calendar. What was read, named."""
    from investment_agent.market.calendar import TradingCalendar
    found, named = set(), []
    for path in sorted((REPO_ROOT / "config").glob("trading-calendar-hose-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        first, last = date.fromisoformat(data["first"]), date.fromisoformat(data["last"])
        lo, hi = max(start, first), min(end, last)
        if lo > hi:
            continue
        cal = TradingCalendar(version=data["version"], source=data["source"], first=first, last=last,
                              holidays=frozenset(date.fromisoformat(d) for d in data["holidays"]))
        found |= set(cal.sessions(lo, hi))
        named.append(f"config/{path.name} ({data['first']}–{data['last']})")
    official_from = min((date.fromisoformat(json.loads(p.read_text(encoding="utf-8"))["first"])
                         for p in (REPO_ROOT / "config").glob("trading-calendar-hose-*.json")), default=None)
    before = end if official_from is None else min(end, official_from - timedelta(days=1))
    if start <= before:
        index = read_index_sessions(data_dir)
        if index and index.get("dates"):
            days = {date.fromisoformat(d) for d in index["dates"] if start.isoformat() <= d <= before.isoformat()}
            found |= days
            named.append(f"phiên VN-Index của VNDirect đến {before.isoformat()} (không phải lịch chính thức; ngày cả nguồn thiếu không bắt được)")
    return found, "; ".join(named) or None


LINE_NAMES = REPO_ROOT / "config" / "statement-line-names.json"  # each stored line's own name in VNDirect's financial_models
# What the stored lines cover (statements.py: equity includes non-controlling interests in every layout)
SCOPE = {"npat": "LNST của cả doanh nghiệp, gồm phần của cổ đông không kiểm soát",
         "npat_parent": "LNST thuộc cổ đông công ty mẹ; dùng dòng này cho EPS và P/E",
         "equity": "Vốn chủ sở hữu GỒM lợi ích cổ đông không kiểm soát (minority_equity); vốn chủ của công ty mẹ = equity − minority_equity",
         "minority_equity": "Lợi ích cổ đông không kiểm soát, một phần của equity",
         "dividends_paid": "Tiền cổ tức, lợi nhuận đã trả cho chủ sở hữu trong kỳ trên báo cáo lưu chuyển tiền tệ hợp nhất (số âm); có thể gồm "
                           "phần công ty con trả cho cổ đông không kiểm soát, nên không phải cổ tức cổ đông công ty nhận. Cổ tức theo từng đợt "
                           "cho cổ đông công ty: eps_co_tuc (dividends)",
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


TIME_KEYS = frozenset({"lay_luc", "fetched_at", "tep_cap_nhat_luc", "danh_muc_lay_luc", "recorded_at", "read_at", "as_of", "at", "first_seen"})
VN_TZ = timezone(timedelta(hours=7))


def vn_times(value):
    """Every time a tool gives, in Vietnam time (owner, 26/11/2026): the stores keep UTC or +07:00 as each source wrote them."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in TIME_KEYS and isinstance(v, str) and "T" in v:
                try:
                    when = datetime.fromisoformat(v)
                except ValueError:
                    when = None
                out[k] = when.astimezone(VN_TZ).isoformat(timespec="seconds") if when and when.tzinfo else v
            else:
                out[k] = vn_times(v)
        return out
    if isinstance(value, list):
        return [vn_times(v) for v in value]
    return value


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
        window_start, window_end = start or days[0], end or days[-1]
        sessions, calendars = _sessions(window_start, window_end, self.root)
        absent = sorted(d.isoformat() for d in sessions if d not in view)
        rows = [{"ngay": d.isoformat(), "mo": str(b.open), "cao": str(b.high), "thap": str(b.low), "dong": str(b.close), "khoi_luong": b.volume}
                for d, b in ((d, view[d][0]) for d in days)]
        return {"ma": symbol, "don_vi": last.currency, "co_so_gia": last.price_basis, "nguon": last.source_id,
                "lay_luc": last.observed_at.isoformat(), "phien_moi_nhat_trong_kho": max(view).isoformat(), "phien": rows,
                "phien_thieu": absent, "lich_kiem": calendars or "Chưa có lịch HOSE trong config cho khoảng này; không kiểm phiên thiếu.",
                **({"luu_y": f"Kho giá ngày chỉ có từ {min(view).isoformat()}, nên trả {len(rows)} phiên thay vì {_count(so_phien, 60, 500)}. "
                             "Phiên xa hơn: lich_su_gia với mat_do \"ngay\" (giá đóng cửa đã điều chỉnh từ 2013)."}
                   if start is None and len(rows) < _count(so_phien, 60, 500) else {})}

    def lich_su_gia(self, ma, tu_ngay=None, den_ngay=None, mat_do="thang") -> dict:
        """VNDirect's adjusted daily closes since 2013 (price_history.py) when stored, each month's last close by default; otherwise the
        long closes kept for VN-Index P/E before 2018 (index_history.py): unadjusted, daily 2013–2017 and the month's last close from 2018.
        The ticker's share events in the range come along either way."""
        if mat_do not in ("thang", "ngay"):
            return _missing("mat_do phải là thang hoặc ngay.")
        symbol = self._symbol(ma)
        if symbol is None:
            return _missing("Mã không hợp lệ.")
        try:
            start = (date.fromisoformat(tu_ngay) if tu_ngay else date.min).isoformat()
            end = (date.fromisoformat(den_ngay) if den_ngay else date.max).isoformat()
        except (TypeError, ValueError):
            return _missing("Ngày phải theo dạng YYYY-MM-DD.")
        issues = [i for i in ((self._json("fundamentals", f"{symbol}.json") or {}).get("share_issues") or []) if start <= str(i.get("date")) <= end]
        adjusted = self._json("price-history", f"{symbol}.json")
        if adjusted and adjusted.get("closes"):
            rows = [list(c) for c in adjusted["closes"] if start <= str(c[0]) <= end]
            if mat_do == "thang":
                last = {}
                for c in rows:
                    last[c[0][:7]] = c
                rows = [last[m] for m in sorted(last)]
            else:
                rows = rows[-MAX_DAILY:]
            out = {"ma": symbol, "nguon": adjusted.get("source"), "lay_luc": adjusted.get("fetched_at"), "don_vi": "nghìn đồng",
                    "dieu_chinh": True,
                    "mat_do": "Cuối tháng: phiên cuối của mỗi tháng trong khoảng" if mat_do == "thang"
                    else f"Từng phiên, tối đa {MAX_DAILY} phiên gần nhất trong khoảng",
                    "luu_y": "Giá đã điều chỉnh của VNDirect (adClose): VNDirect tính lại cả chuỗi sau mỗi đợt thưởng hay cổ tức cổ phiếu, "
                             "nên so được giá qua các năm; số có thể khác giá khớp lệnh thực tế ngày đó.",
                    "ngay_cuoi": adjusted["closes"][-1][0], "diem": rows, "su_kien_co_phieu": issues}
            if mat_do == "ngay" and rows:
                have = {r[0] for r in rows}
                sessions, calendars = _sessions(date.fromisoformat(rows[0][0]), date.fromisoformat(rows[-1][0]), self.root)
                out["phien_thieu"] = sorted(d.isoformat() for d in sessions if d.isoformat() not in have)
                out["lich_kiem"] = calendars or "Chưa có lịch hay phiên VN-Index cho khoảng này; không kiểm phiên thiếu."
            return out
        record, missing = self._per_symbol("index-history", ma, "lịch sử giá dài hạn")
        if missing:
            return missing
        closes = [list(c) for c in record.get("closes") or [] if start <= str(c[0]) <= end]
        return {"ma": self._symbol(ma), "nguon": record.get("source"), "lay_luc": record.get("fetched_at"), "don_vi": "nghìn đồng",
                "dieu_chinh": False, "mat_do": "Từng phiên 2013–2017; từ 2018 chỉ giá đóng cửa cuối tháng (phiên cuối của tháng, và phiên mới nhất khi lấy)",
                "luu_y": "Giá chưa điều chỉnh: mỗi đợt thưởng, cổ tức bằng cổ phiếu, phát hành thêm làm giá gãy xuống; không tính lợi nhuận qua "
                         "các mốc trong su_kien_co_phieu như thể giá liền mạch. Giá ngày đã điều chỉnh gần đây: gia_ngay.",
                "ngay_cuoi": (record.get("closes") or [[None]])[-1][0], "diem": closes,
                "su_kien_co_phieu": issues}

    def so_sanh_nganh(self, ma) -> dict:
        symbol = self._symbol(ma)
        return compare_sector(self.root, symbol) if symbol else _missing("Mã không hợp lệ.")

    def dinh_gia_lich_su(self, ma) -> dict:
        symbol = self._symbol(ma)
        return own_history(self.root, symbol) if symbol else _missing("Mã không hợp lệ.")

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
        out = {"ma": symbol, "loai": record.get("kind"), "nguon": record.get("source"), "lay_luc": record.get("fetched_at"),
               "don_vi": "đồng", "pham_vi": SCOPE, "ten_dong": {k: names[k] for k in sorted(lines) if k in names}, "ky": kept}
        quarters = record.get("quarters") or {}
        if ky == "quy" and record.get("kind") is None and quarters:
            out["canh_bao_loi_nhuan_ngoai_ban_hang"] = outside_sales_flag(quarters)
        return out

    def chi_so_tai_chinh(self, ma, so_ky=8) -> dict:
        record, missing = self._per_symbol("financial-ratios", ma, "chỉ số tài chính")
        if missing:
            general, _ = self._per_symbol("financial-ratios-general", ma, "chỉ số tài chính")
            if general is None:
                return missing
            return {"ma": general.get("symbol"), "loai": "general", "nguon": general.get("source"), "lay_luc": general.get("fetched_at"),
                    "ten_chi_so": general.get("names") or {}, "luu_y": GENERAL_RATIO_NOTE,
                    "ky": _newest(general.get("quarters"), _count(so_ky, 8, 80))}
        return {"ma": record.get("symbol"), "loai": record.get("kind"), "nguon": record.get("source"), "lay_luc": record.get("fetched_at"),
                "ky": _newest(record.get("quarters"), _count(so_ky, 8, 80))}

    def eps_co_tuc(self, ma, so_ky=8) -> dict:
        record, missing = self._per_symbol("fundamentals", ma, "dữ liệu cơ bản")
        if missing:
            return missing
        n = _count(so_ky, 8, 80)
        eps_flags = eps_jumps(record.get("years") or {})
        out = {**record, **{k: _newest(record.get(k), n) for k in ("years", "quarters", "annual") if k in record}}
        statements = self._json("statements-financial", f"{record.get('symbol')}.json") or self._json("statements", f"{record.get('symbol')}.json") or {}
        minority = {kind: {p: (statements.get(kind) or {}).get(p, {}).get("minority_equity") for p in out.get(kind) or {}
                           if (statements.get(kind) or {}).get(p, {}).get("minority_equity") is not None}
                    for kind in ("years", "quarters")}
        return {**out, "chu_thich": FUNDAMENTAL_NOTES, "loi_ich_thieu_so": minority,
                "canh_bao_eps": {"nguong": format(EPS_JUMP, "f"), "cong_thuc": "(eps / eps_nam_truoc) / (npat / npat_nam_truoc)",
                                 "y_nghia": "EPS năm đổi khác hẳn LNST công ty mẹ (hơn 3 lần theo chiều nào cũng vậy): có thể là lỗi của nguồn hoặc "
                                            "phát hành nhiều cổ phiếu. Số giữ nguyên như nguồn; nói rõ năm bị gắn cờ, không tự sửa.",
                                 "nam": eps_flags}}

    def dinh_gia_ma(self, ma) -> dict:
        record, missing = self._per_symbol("valuation-check", ma, "định giá VNDirect công bố")
        if missing:
            return missing
        symbol = self._symbol(ma)
        out = {"ma": symbol, "nguon": "VNDirect", **{name: record.get(src) for name, src in VALUATION_FIELDS}}
        # Which price the published figures rest on, and how far the latest stored close has moved since (owner, 26/11/2026)
        from decimal import Decimal, InvalidOperation
        try:
            then = Decimal(str(record["market_cap"])) / Decimal(str(record["shares"]))
        except (KeyError, InvalidOperation, ZeroDivisionError, TypeError):
            then = None
        view = PriceStore(self.root).latest(symbol)
        latest = view[max(view)][0] if view else None
        out["gia_ngay_dinh_gia"] = format(then.quantize(Decimal("0.01")).normalize(), "f") if then else None
        out["gia_moi_nhat"] = {"ngay": latest.session_date.isoformat(), "gia": format(latest.close.normalize(), "f")} if latest else None
        out["lech_gia"] = format(((latest.close - then) / then).quantize(Decimal("0.001")).normalize(), "f") if then and latest else None
        out["luu_y"] = ("gia_ngay_dinh_gia = von_hoa ÷ so_co_phieu, giá VNDirect dùng cho P/E, P/B ở ngày đó (đồng). Nếu lech_gia so với giá mới nhất "
                        "trong kho quá 5% thì nói rõ; muốn quy P/E, P/B về giá mới nhất thì nhân với gia_moi_nhat ÷ gia_ngay_dinh_gia và ghi là tự tính.")
        return out

    def thuyet_minh(self, ma, ky="quy", so_ky=4) -> dict:
        record, missing = self._per_symbol("company-notes", ma, "thuyết minh BCTC")
        if missing:
            return missing
        if ky not in ("quy", "nam"):
            return _missing("Kỳ phải là quy hoặc nam.")
        periods = _newest(record.get("quarters" if ky == "quy" else "years"), _count(so_ky, 4, 40))
        ky_out = {p: {g: {k: row[k] for k in keys if k in row} for g, keys in NOTE_GROUPS.items() if any(k in row for k in keys)}
                  for p, row in periods.items()}
        return {"ma": self._symbol(ma), "nguon": record.get("source"), "lay_luc": record.get("fetched_at"), "don_vi": "đồng",
                "ten_dong": NOTE_LABELS, "ky": ky_out,
                "luu_y": "Thuyết minh BCTC từ API công khai của Vietcap, giữ nguyên số. Dòng không có trong kỳ là nguồn không ghi, không phải 0."}

    # Doanh nghiệp
    def su_kien_doanh_nghiep(self, ma) -> dict:
        record, missing = self._per_symbol("events", ma, "sự kiện doanh nghiệp")
        return missing or record

    def co_dong_ban_lanh_dao(self, ma) -> dict:
        record, missing = self._per_symbol("company", ma, "cổ đông và ban lãnh đạo")
        return missing or record

    def giao_dich_noi_bo(self, ma) -> dict:
        record, missing = self._per_symbol("insider", ma, "giao dịch nội bộ")
        if missing:
            return missing
        deals = []
        for d in fill_from_docs(record.get("deals") or [], DocStore(self.root)):
            if d.get("kind") is None or d.get("shares") is None:
                d = {**d, "thieu_so_luong": True, "van_ban": d.get("doc_url") or d.get("url")}
            deals.append(d)
        return {**record, "deals": deals,
                "luu_y": "Báo cáo có thieu_so_luong: nguồn VNDirect không có chiều mua bán và số lượng; số lượng nằm trong văn bản công bố ở van_ban. "
                         "Không suy ra chiều hay số lượng từ tiêu đề. Báo cáo có tu_van_ban: loại và số lượng đọc từ văn bản HOSE đính kèm (nhận dạng "
                         "chữ trên máy), chỉ nhận khi số nắm giữ trước ± số đã giao dịch = số sau; rong=true là số ròng của cả nhóm cổ đông lớn; "
                         "loại ESOP là cổ phiếu mua trực tiếp từ công ty, Cho tặng và Nhận tặng là chuyển cổ phiếu giữa các cá nhân, "
                         "Chuyển nhượng và Nhận chuyển nhượng là chuyển nhượng thỏa thuận giữa hai bên qua VSDC; các loại này không phải "
                         "mua bán khớp lệnh trên thị trường và không cộng vào số mua, bán 12 tháng."}

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
