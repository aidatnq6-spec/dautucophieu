"""Cảnh báo báo cáo (owner, 26/11/2026): profit mostly outside sales, and EPS that moved far apart from parent profit.

Shared by the public-data MCP tools and Bảng số tài chính (docs/superpowers/specs/2026-11-26-canh-bao-bang-so-tai-chinh-design.md).
Figures are read as stored; nothing is corrected, and a case that cannot be worked out says why.
"""

from decimal import Decimal, InvalidOperation

OUTSIDE_SALES = Decimal("0.3")  # flag when financial income and other profit are above 30% of profit before tax
EPS_JUMP = Decimal("3")  # flag a year whose EPS moved more than 3 times further than parent profit did (KDH 2024, 80 đồng)


def dec(value) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if d.is_finite() else None


def eps_jumps(years: dict) -> list[dict]:
    """Years whose EPS moved more than EPS_JUMP times further than parent profit did, against the year before; all four must be positive."""
    out = []
    for y in sorted(years):
        prev = years.get(str(int(y) - 1)) if y.isdigit() else None
        if not prev:
            continue
        e, ep, n, npv = (dec(years[y].get("eps")), dec(prev.get("eps")), dec(years[y].get("npat")), dec(prev.get("npat")))
        if None in (e, ep, n, npv) or min(e, ep, n, npv) <= 0:
            continue
        gap = (e / ep) / (n / npv)
        if gap > EPS_JUMP or gap < 1 / EPS_JUMP:
            out.append({"nam": y, "eps": years[y]["eps"], "eps_nam_truoc": prev["eps"], "npat": years[y]["npat"], "npat_nam_truoc": prev["npat"],
                        "lech": format(gap.quantize(Decimal("0.001")).normalize(), "f")})
    return out


def outside_share(rows: list[dict], keys: list[str], *, need: int) -> dict:
    """(financial income + other profit) ÷ profit before tax over the given quarters, summed; associates are left out."""
    if len(keys) < need:
        return {"ky": keys, "ty_le": None, "vuot_nguong": None, "ly_do": f"Chưa đủ {need} quý"}
    parts = [(dec(r.get("pbt")), dec(r.get("fin_income")), dec(r.get("other_profit"))) for r in rows]
    if any(v is None for p in parts for v in p):
        return {"ky": keys, "ty_le": None, "vuot_nguong": None, "ly_do": "Thiếu dòng LNTT, doanh thu tài chính hoặc lợi nhuận khác"}
    pbt = sum(p[0] for p in parts)
    if pbt <= 0:
        return {"ky": keys, "ty_le": None, "vuot_nguong": None, "ly_do": "LNTT không dương"}
    share = sum(p[1] + p[2] for p in parts) / pbt
    return {"ky": keys, "ty_le": format(share.quantize(Decimal("0.0001")).normalize(), "f"), "vuot_nguong": share > OUTSIDE_SALES}


def outside_sales_flag(quarters: dict) -> dict | None:
    """The latest quarter and the last four of a general company's stored quarters; None when there are none."""
    if not quarters:
        return None
    keys = sorted(quarters)
    latest = outside_share([quarters[keys[-1]]], [keys[-1]], need=1)
    latest = {k: v for k, v in latest.items() if k != "ky"} | {"ky": keys[-1]}
    return {"nguong": format(OUTSIDE_SALES, "f"), "cong_thuc": "(fin_income + other_profit) / pbt",
            "y_nghia": "Phần LNTT đến từ doanh thu tài chính và lợi nhuận khác, không từ bán hàng; vượt ngưỡng thì P/E dựa nhiều vào khoản này. "
                       "Lãi tiền gửi đều đặn cũng nằm trong doanh thu tài chính, nên vượt ngưỡng không có nghĩa là khoản một lần.",
            "quy_gan_nhat": latest, "bon_quy": outside_share([quarters[k] for k in keys[-4:]], keys[-4:], need=4)}
