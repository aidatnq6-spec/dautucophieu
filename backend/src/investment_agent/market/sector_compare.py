"""So sánh ngành (owner, 26/11/2026): one ticker against its ICB level-2 peers on HOSE, on VNDirect's quarterly ratios.

Shared by the public-data MCP tool so_sanh_nganh and Bảng số tài chính's "Trung vị ngành" column (docs/superpowers/specs/
2026-11-26-so-sanh-nganh-design.md, 2026-11-26-trung-vi-nganh-trang-ma-design.md). Only peers with a figure for the ticker's own
latest quarter count; another quarter never stands in. Medians and quartiles are statistics over VNDirect's figures, the ticker left out.
"""

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median, quantiles

from .financial_ratios import DISPLAY, INVESTMENT_SERVICES, kind_of

# The sixteen ratios the owner chose, in this order
SECTOR_CODES = ("ROAE_TR_AVG4Q", "ROIC_TR_AVG4Q", "GROSS_MARGIN_TR", "NET_MARGIN_TR", "DEBT_TO_EQUITY_AQ", "INTEREST_COVERAGE_TR",
                "CURRENT_RATIO_AQ", "DEBT_EBITDA", "CFO_TO_SALES_TR", "DSO_TR_AVG5Q", "DIO_TR_AVG5Q", "CASH_CONVERSION_CYCLE_TR_AVG5Q",
                "NET_SALES_TR_GRYOY", "NET_PROFIT_TR_GRYOY", "EPS_TR_GR3YR", "DIVIDEND_PAYOUT_TR")
# Trung vị ngành cho ngân hàng (owner, 27/11/2026): a bank against the other HOSE banks on VNDirect's bank rows of Bảng số tài chính
BANK_CODES = tuple(code for code, _, _ in DISPLAY["bank"])
BANK_NAMES = {code: label for code, label, _ in DISPLAY["bank"]}
# and a securities firm against the other HOSE firms of ICB level 4 "Dịch vụ đầu tư" (owner, 27/11/2026), EVF and the like left out
SECURITIES_CODES = tuple(code for code, _, _ in DISPLAY["securities"])
SECURITIES_NAME = "Dịch vụ đầu tư (chứng khoán)"
OWN = {"bank": (BANK_CODES, BANK_NAMES), "securities": (SECURITIES_CODES, {code: label for code, label, _ in DISPLAY["securities"]})}
MIN_PEERS = 3
NOTE = ("So với các doanh nghiệp cùng ngành ICB cấp 2 trên HOSE có số ở đúng quý này; trung vị và tứ phân vị là phép tính thống kê "
        "trên số VNDirect, không gồm mã đang xem. Không gắn nhãn tốt hay xấu: cao hơn không phải lúc nào cũng tốt (nợ vay, số "
        "ngày phải thu, tồn kho). Tỷ lệ ở dạng thập phân (0,08 là 8%); số ngày là ngày; hệ số là lần.")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")


def _missing(reason: str) -> dict:
    return {"thieu": True, "ly_do": reason}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _num(v) -> Decimal | None:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if d.is_finite() else None


def _plain(d: Decimal) -> str:
    return format(d.normalize(), "f")


def compare_sector(data_dir: Path, symbol: str, codes: tuple[str, ...] | None = None) -> dict:
    """codes: None for the ticker's own set (BANK_CODES for a bank, SECURITIES_CODES for a securities firm, SECTOR_CODES otherwise)."""
    root = Path(data_dir)
    if not _SYMBOL.fullmatch(symbol or ""):
        return _missing("Mã không hợp lệ.")
    listing = (_json(root / "hose-listing.json") or {}).get("listing") or {}
    icb, names = listing.get("icb_codes") or {}, listing.get("icb_names") or {}
    code = icb.get(symbol)
    if code is None:
        return _missing(f"Chưa có ngành ICB của {symbol} trong danh sách HOSE.")
    sector = names.get(code, code)
    kind = kind_of(sector)
    if kind == "insurance":
        return _missing(f"{sector} có bộ chỉ số riêng; so sánh ngành có cho doanh nghiệp thường, ngân hàng và công ty chứng khoán.")
    group = icb
    if kind == "securities":
        level4 = listing.get("icb4_codes")
        if level4 is None:
            return _missing("Chưa có ngành ICB cấp 4 trong danh sách HOSE (danh sách được làm mới ở lượt chạy kế tiếp).")
        if level4.get(symbol) != INVESTMENT_SERVICES:
            return _missing(f"{symbol} không thuộc nhóm Dịch vụ đầu tư (ICB cấp 4, công ty chứng khoán); không có nhóm để so.")
        group, code, sector = level4, INVESTMENT_SERVICES, SECURITIES_NAME
    folder = "financial-ratios-general" if kind is None else "financial-ratios"
    codes = codes or (OWN[kind][0] if kind else SECTOR_CODES)
    own = _json(root / folder / f"{symbol}.json")
    quarters = [q for q, v in ((own or {}).get("quarters") or {}).items() if any(c in v for c in codes)]
    if not quarters:
        return _missing(f"Chưa có chỉ số tài chính VNDirect của {symbol} trong kho.")
    quarter = max(quarters)
    mine = own["quarters"][quarter]
    peers = sorted(s for s, c in group.items() if c == code and s != symbol)
    rows, no_file, no_quarter = {}, 0, 0
    for s in peers:
        rec = _json(root / folder / f"{s}.json") if _SYMBOL.fullmatch(s) else None
        if not rec:
            no_file += 1
        elif quarter not in (rec.get("quarters") or {}):
            no_quarter += 1
        else:
            rows[s] = rec["quarters"][quarter]
    out = []
    for c in codes:
        value = _num(mine.get(c))
        others = [v for v in (_num(r.get(c)) for r in rows.values()) if v is not None]
        item = {"ma_chi_so": c, "ten": OWN[kind][1].get(c, c) if kind else (own.get("names") or {}).get(c, c), "gia_tri": mine.get(c)}
        if value is None:
            out.append({**item, "trung_vi": None, "so_doanh_nghiep": len(others), "ly_do": f"{symbol} chưa có số quý này"})
            continue
        if len(others) < MIN_PEERS:
            out.append({**item, "trung_vi": None, "so_doanh_nghiep": len(others), "ly_do": f"Dưới {MIN_PEERS} doanh nghiệp cùng ngành có số quý này"})
            continue
        q1, _, q3 = quantiles(others, n=4, method="inclusive")
        rank = 1 + sum(1 for v in others if v > value)
        out.append({**item, "trung_vi": _plain(median(others)), "phan_vi_25": _plain(q1), "phan_vi_75": _plain(q3),
                    "so_doanh_nghiep": len(others), "thu_hang": f"{rank}/{len(others) + 1} (cao xuống thấp)"})
    return {"ma": symbol, "nganh": sector, "ma_nganh": code, "quy": quarter, "nguon": own.get("source"), "lay_luc": own.get("fetched_at"),
            "so_doanh_nghiep_nganh": len(peers), "chua_co_quy_nay": no_quarter, "chua_co_chi_so": no_file, "chi_so": out, "luu_y": NOTE.replace("ICB cấp 2", "ICB cấp 4 (Dịch vụ đầu tư)") if kind == "securities" else NOTE}
