"""Định giá lịch sử của một mã (owner, 26/11/2026): the ticker's own P/E and P/B at each month's last close, worked out as VN-Index's
P/E before VNDirect's series (index_history.py), so a P/E today can be set against the ticker's own past.

At each stored close: market value = unadjusted close (thousand đồng) × 1000 × shares of the quarter due by then (45 days after it ends,
docs/decisions/market-rules.md); P/E = market value ÷ the four quarters' parent profit to that quarter; P/B = market value ÷ parent equity.
A month whose quarters are missing is left out and counted; a P/E on four quarters' loss is left out and counted. Medians and quartiles,
not means: VNDirect's own averages are means of daily P/E and a few days of tiny profit throw them (KDH 1Y average 1,825.9 on 25/11/2026).
"""

import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import median, quantiles

from investment_agent.valuation.weekly import _latest_quarter_out

from .index_history import _figures, _load, _month_end

WINDOWS = {"3_nam": 3, "5_nam": 5}
_Q = Decimal("0.01")


def _plain(d: Decimal) -> str:
    return format(d.quantize(_Q, ROUND_HALF_UP).normalize(), "f")


def _summary(points: list[tuple[date, Decimal]], current: Decimal | None, *, loss: int, missing: int) -> dict:
    values = [v for _, v in points]
    out = {"so_thang": len(values), "bo_qua_lo": loss, "bo_qua_thieu": missing}
    if len(values) < 2:
        return {**out, "trung_vi": None, "ly_do": "Dưới 2 tháng có số"}
    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    out.update({"trung_vi": _plain(median(values)), "phan_vi_25": _plain(q1), "phan_vi_75": _plain(q3),
                "thap_nhat": _plain(min(values)), "cao_nhat": _plain(max(values))})
    if current is not None:
        out["thang_thap_hon_hien_tai"] = f"{sum(1 for v in values if v < current)}/{len(values)}"
    return out


def _quarter_end(q: str) -> date:
    year, n = int(q[:4]), int(q[-1])
    return _month_end(date(year, n * 3, 1))


def _bonus_factor(bonuses: list[tuple[date, Decimal]], after: date, upto: date) -> Decimal:
    """Bonus issues and stock dividends whose ex-date falls after the quarter the shares come from and by the day: the unadjusted close
    has already fallen with them, the quarter's share count has not yet risen."""
    factor = Decimal(1)
    for day, ratio in bonuses:
        if after < day <= upto:
            factor *= 1 + ratio
    return factor


def own_history(data_dir: Path, symbol: str) -> dict:
    path = Path(data_dir) / "index-history" / f"{symbol}.json"
    if not path.is_file():
        return {"thieu": True, "ly_do": f"Chưa có lịch sử báo cáo và giá dài hạn của {symbol} trong kho."}
    record = json.loads(path.read_text(encoding="utf-8"))
    quarters, closes = _load(record)
    if not closes:
        return {"thieu": True, "ly_do": f"Chưa có giá dài hạn của {symbol} trong kho."}
    issues_path = Path(data_dir) / "fundamentals" / f"{symbol}.json"
    issues = (json.loads(issues_path.read_text(encoding="utf-8")).get("share_issues") or []) if issues_path.is_file() else []
    bonuses = []
    for i in issues:
        try:
            if i.get("kind") == "bonus" and i.get("ratio") is not None:
                bonuses.append((date.fromisoformat(str(i["date"])[:10]), Decimal(str(i["ratio"]))))
        except ValueError:
            continue
    rows = []  # (day, pe or None, pb or None, why)
    for day, close in closes:
        key = _latest_quarter_out(_month_end(day))
        figures = _figures(quarters, key)
        if figures is None:
            rows.append((day, None, None, "thieu"))
            continue
        profit, equity, shares = figures
        cap = close * 1000 * shares * _bonus_factor(bonuses, _quarter_end(key), day)
        rows.append((day, cap / profit if profit > 0 else None, cap / equity if equity > 0 else None, "lo" if profit <= 0 else ""))
    last_day = closes[-1][0]
    current_pe, current_pb = rows[-1][1], rows[-1][2]
    windows = {}
    for name, years in WINDOWS.items():
        start = date(last_day.year - years, last_day.month, min(last_day.day, 28))
        inside = [r for r in rows if r[0] > start]
        windows[name] = {"tu": start.isoformat(),
                         "pe": _summary([(d, pe) for d, pe, _, _ in inside if pe is not None], current_pe,
                                        loss=sum(1 for r in inside if r[3] == "lo"), missing=sum(1 for r in inside if r[3] == "thieu")),
                         "pb": _summary([(d, pb) for d, _, pb, _ in inside if pb is not None], current_pb,
                                        loss=0, missing=sum(1 for r in inside if r[3] == "thieu"))}
    return {"ma": symbol, "nguon": "tự tính từ báo cáo và giá chưa điều chỉnh của VNDirect (index-history)", "lay_luc": record.get("fetched_at"),
            "ngay_cuoi": last_day.isoformat(),
            "cong_thuc": "Mỗi giá đóng cửa trong kho (cuối tháng từ 2018): vốn hóa = giá chưa điều chỉnh × số cổ phiếu của quý đã công bố "
                         "(quý tính là công bố 45 ngày sau khi kết thúc); P/E = vốn hóa ÷ LNST công ty mẹ 4 quý đến quý đó; P/B = vốn hóa ÷ vốn chủ "
                         "công ty mẹ. Đợt thưởng hay cổ tức cổ phiếu có ngày giao dịch không hưởng quyền sau cuối quý đó và trước ngày tính thì số cổ "
                         "phiếu nhân thêm (1 + tỷ lệ), vì giá đã giảm theo; phát hành thêm có thu tiền không được tính thêm. Tháng thiếu quý bị bỏ "
                         "(bo_qua_thieu); P/E khi lỗ 4 quý bị bỏ (bo_qua_lo).",
            "cua_so": windows,
            "hien_tai": {"ngay": last_day.isoformat(), "pe": _plain(current_pe) if current_pe is not None else None,
                         "pb": _plain(current_pb) if current_pb is not None else None},
            "luu_y": "Số tự tính, không phải số VNDirect công bố; điểm hiện tại là giá đóng cửa cuối cùng trong chuỗi này (ngay_cuoi), có thể "
                     "cũ hơn dinh_gia_ma. Dùng trung vị và tứ phân vị, không dùng trung bình."}
