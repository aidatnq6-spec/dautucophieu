"""Chất lượng báo cáo: Piotroski F-Score of the latest fiscal year and three warning signs, from the annual lines kept by
market/fundamentals.py (Vnstock free tier). Signs to look into, not a finding of fraud and not a recommendation.

A criterion without the lines it needs is "not evaluated" (passed None), never guessed; a level needs at least 7 evaluated
criteria (8–9 strong, 0–2 weak: Piotroski's cut-offs). The warning-sign thresholds are this application's own rules,
stated on the page, not research cut-offs. Banks, securities firms and insurers report on another structure: not scored.
"""

import math
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.bank_figures import derive

FINANCIAL = {"Ngân hàng", "Dịch vụ tài chính", "Bảo hiểm"}
MIN_EVALUATED = 7
RECEIVABLES_GAP = Decimal("0.20")  # receivables growth above revenue growth, in share points
ACCRUAL_SHARE = Decimal("0.10")  # three years of (profit − operating cash flow) against latest total assets
BN = Decimal(1_000_000_000)
# Sector context shown with the signs, where a sign is usual for the business rather than a warning by itself.
NOTES = {"Bất động sản": "Bất động sản: chủ đầu tư thường lãi nhưng dòng tiền kinh doanh âm khi đang đổ tiền vào quỹ đất, dự án (hàng tồn kho); "
                         "đọc dấu hiệu cùng tiến độ bàn giao."}


def _num(x: Decimal, places: int) -> str:
    q = x.quantize(Decimal(1) if places == 0 else Decimal(10) ** -places, ROUND_HALF_UP)
    sign, text = ("−" if q < 0 else ""), format(abs(q), "f")
    whole, _, frac = text.partition(".")
    whole = f"{int(whole):,}".replace(",", ".")
    return sign + whole + ("," + frac if frac else "")


def _bn(x: Decimal) -> str:
    v = x / BN
    return f"{_num(v, 0 if abs(v) >= 100 or v == v.to_integral_value() else 1)} tỷ"


def _pct(x: Decimal, places: int = 1) -> str:
    return f"{_num(x * 100, places)}%"


def _ratio(x: Decimal, places: int = 2) -> str:
    return _num(x, places)


def _versus(fmt, a: Decimal, b: Decimal) -> tuple[str, str]:
    """Both values in the format, with one more decimal when they would otherwise read the same."""
    return (fmt(a), fmt(b)) if fmt(a) != fmt(b) or a == b else (fmt(a, 2 if fmt is _pct else 3), fmt(b, 2 if fmt is _pct else 3))


def _compare(fmt, a: Decimal, b: Decimal, unit: str, y: int) -> str:
    now, before = _versus(fmt, a, b)
    return f"{now}{unit} so với {before}{unit} năm {y - 1}"


def _lines(record: dict) -> dict[int, dict[str, Decimal]]:
    out = {}
    for y, figures in (record.get("annual") or {}).items():
        out[int(y)] = {k: Decimal(v) for k, v in figures.items() if v is not None}
    return out


def _level(score: int, evaluated: int, total: int) -> str | None:
    """Piotroski's cut-offs for 9 criteria (level from 7 evaluated; 8–9 strong; 0–2 weak) scaled to `total`: at least 7/9 of the
    criteria evaluated, strong when at most one is missed, weak at no more than 2/9 of them passed."""
    if evaluated < math.ceil(total * MIN_EVALUATED / 9):
        return None
    return "strong" if score >= total - 1 else "weak" if score <= total * 2 // 9 else "medium"


def _criterion(id_: str, label: str, passed: bool | None, detail: str) -> dict:
    return {"id": id_, "label": label, "passed": passed, "detail": detail}


def _missing(id_: str, label: str, years) -> dict:
    return _criterion(id_, label, None, f"Thiếu số liệu năm {', '.join(str(y) for y in sorted(set(years)))}")


def _f_score(a: dict[int, dict[str, Decimal]], share_issues: list[dict] | None, y: int) -> dict:
    cur, prev, prev2 = a.get(y, {}), a.get(y - 1, {}), a.get(y - 2, {})

    def has(row, *keys):
        return all(k in row for k in keys)

    out = []
    roa = cur["profit"] / prev["total_assets"] if has(cur, "profit") and has(prev, "total_assets") and prev["total_assets"] > 0 else None
    roa_prev = prev["profit"] / prev2["total_assets"] if has(prev, "profit") and has(prev2, "total_assets") and prev2["total_assets"] > 0 else None
    out.append(_criterion("roa", "ROA dương", roa > 0, f"ROA {_pct(roa)} (lợi nhuận {_bn(cur['profit'])} / tài sản đầu kỳ {_bn(prev['total_assets'])})")
               if roa is not None else _missing("roa", "ROA dương", [y, y - 1]))
    out.append(_criterion("cfo", "Dòng tiền kinh doanh dương", cur["cfo"] > 0, f"Dòng tiền kinh doanh {_bn(cur['cfo'])}")
               if has(cur, "cfo") else _missing("cfo", "Dòng tiền kinh doanh dương", [y]))
    out.append(_criterion("roa_up", "ROA tăng", roa > roa_prev, f"ROA {_compare(_pct, roa, roa_prev, '', y)}")
               if roa is not None and roa_prev is not None else _missing("roa_up", "ROA tăng", [y, y - 1, y - 2]))
    out.append(_criterion("cash_over_profit", "Dòng tiền kinh doanh lớn hơn lợi nhuận", cur["cfo"] > cur["profit"],
                          f"Dòng tiền kinh doanh {_bn(cur['cfo'])}, lợi nhuận {_bn(cur['profit'])}")
               if has(cur, "cfo", "profit") else _missing("cash_over_profit", "Dòng tiền kinh doanh lớn hơn lợi nhuận", [y]))

    def ratio(row, top, bottom):
        return row[top] / row[bottom] if has(row, top, bottom) and row[bottom] > 0 else None

    lev, lev_prev = ratio(cur, "long_liabilities", "total_assets"), ratio(prev, "long_liabilities", "total_assets")
    out.append(_criterion("leverage_down", "Nợ dài hạn / tổng tài sản giảm", lev < lev_prev, _compare(_pct, lev, lev_prev, "", y))
               if lev is not None and lev_prev is not None else _missing("leverage_down", "Nợ dài hạn / tổng tài sản giảm", [y, y - 1]))
    cr, cr_prev = ratio(cur, "current_assets", "current_liabilities"), ratio(prev, "current_assets", "current_liabilities")
    out.append(_criterion("liquidity_up", "Hệ số thanh toán ngắn hạn tăng", cr > cr_prev, _compare(_ratio, cr, cr_prev, " lần", y))
               if cr is not None and cr_prev is not None else _missing("liquidity_up", "Hệ số thanh toán ngắn hạn tăng", [y, y - 1]))
    label = "Không phát hành cổ phiếu huy động vốn"
    if share_issues is None:
        out.append(_criterion("no_issue", label, None, "Chưa có số liệu phát hành cổ phiếu (chờ lần cập nhật báo cáo sau)"))
    else:
        kinds = {i["kind"] for i in share_issues if i["date"][:4] == str(y)}
        if "raise" in kinds:
            out.append(_criterion("no_issue", label, False, f"Có đợt huy động vốn bằng cổ phiếu năm {y} (quyền mua, riêng lẻ hoặc ESOP)"))
        elif "other" in kinds:
            out.append(_criterion("no_issue", label, None, f"Có đợt phát hành năm {y} không rõ loại"))
        else:
            out.append(_criterion("no_issue", label, True,
                                  f"Không có đợt huy động vốn bằng cổ phiếu năm {y} (cổ phiếu thưởng, cổ tức bằng cổ phiếu không tính)"))
    gm, gm_prev = ratio(cur, "gross_profit", "revenue"), ratio(prev, "gross_profit", "revenue")
    out.append(_criterion("margin_up", "Biên lãi gộp tăng", gm > gm_prev, _compare(_pct, gm, gm_prev, "", y))
               if gm is not None and gm_prev is not None else _missing("margin_up", "Biên lãi gộp tăng", [y, y - 1]))
    turn = cur["revenue"] / prev["total_assets"] if has(cur, "revenue") and has(prev, "total_assets") and prev["total_assets"] > 0 else None
    turn_prev = prev["revenue"] / prev2["total_assets"] if has(prev, "revenue") and has(prev2, "total_assets") and prev2["total_assets"] > 0 else None
    out.append(_criterion("turnover_up", "Vòng quay tài sản tăng", turn > turn_prev, _compare(_ratio, turn, turn_prev, " vòng", y))
               if turn is not None and turn_prev is not None else _missing("turnover_up", "Vòng quay tài sản tăng", [y, y - 1, y - 2]))

    evaluated = [c for c in out if c["passed"] is not None]
    score = sum(1 for c in evaluated if c["passed"])
    level = _level(score, len(evaluated), len(out))
    return {"kind": "f_score", "title": "F-Score", "year": str(y), "score": score, "evaluated": len(evaluated), "level": level, "criteria": out}


def _signs(a: dict[int, dict[str, Decimal]], y: int) -> list[dict]:
    last3 = [yr for yr in (y - 2, y - 1, y) if "profit" in a.get(yr, {}) and "cfo" in a.get(yr, {})]
    signs = []
    label = "Lãi nhưng dòng tiền kinh doanh âm"
    if len(last3) < 3:
        signs.append({"id": "profit_without_cash", "label": label, "flag": None, "detail": "Cần lợi nhuận và dòng tiền kinh doanh của 3 năm gần nhất"})
    else:
        hits = [yr for yr in last3 if a[yr]["profit"] > 0 and a[yr]["cfo"] < 0]
        signs.append({"id": "profit_without_cash", "label": label, "flag": len(hits) >= 2, "rule": "ít nhất 2 trong 3 năm gần nhất",
                      "detail": " · ".join(f"{yr}: lãi {_bn(a[yr]['profit'])}, dòng tiền KD {_bn(a[yr]['cfo'])}" for yr in last3)})
    cur, prev = a.get(y, {}), a.get(y - 1, {})
    label = "Phải thu tăng nhanh hơn doanh thu"
    if all(k in r and r[k] > 0 for r in (cur, prev) for k in ("receivables", "revenue")):
        rec, rev = cur["receivables"] / prev["receivables"] - 1, cur["revenue"] / prev["revenue"] - 1
        signs.append({"id": "receivables_outpace_revenue", "label": label, "flag": rec - rev >= RECEIVABLES_GAP,
                      "rule": f"năm gần nhất, phải thu tăng nhanh hơn doanh thu từ {_num(RECEIVABLES_GAP * 100, 0)} điểm % trở lên",
                      "detail": f"Năm {y}: phải thu {'+' if rec >= 0 else ''}{_pct(rec)}, doanh thu {'+' if rev >= 0 else ''}{_pct(rev)}"})
    else:
        signs.append({"id": "receivables_outpace_revenue", "label": label, "flag": None, "detail": f"Thiếu phải thu hoặc doanh thu năm {y - 1}–{y}"})
    label = "Lợi nhuận dồn tích lớn"
    if len(last3) == 3 and cur.get("total_assets", 0) > 0:
        accrued = sum(a[yr]["profit"] - a[yr]["cfo"] for yr in last3)
        share = accrued / cur["total_assets"]
        signs.append({"id": "accruals", "label": label, "flag": share > ACCRUAL_SHARE,
                      "rule": f"tổng (lợi nhuận − dòng tiền KD) 3 năm lớn hơn {_num(ACCRUAL_SHARE * 100, 0)}% tổng tài sản",
                      "detail": f"{last3[0]}–{y}: {_bn(accrued)}, bằng {_pct(share)} tổng tài sản {_bn(cur['total_assets'])}"})
    else:
        signs.append({"id": "accruals", "label": label, "flag": None, "detail": "Cần lợi nhuận, dòng tiền kinh doanh 3 năm và tổng tài sản năm gần nhất"})
    return signs


# Financial sectors: Piotroski's criteria do not fit their statements, so a health score of the app's own choosing from the
# sector ratios VNDirect publishes, latest quarter against the same quarter a year before; levels scale Piotroski's cut-offs.
_PCT2, _PCT1, _PCT0 = (lambda x, p=2: _pct(x, p)), (lambda x, p=1: _pct(x, p)), (lambda x, p=0: _pct(x, p))
_TIMES = lambda x, p=2: f"{_ratio(x, p)} lần"  # noqa: E731
_ROAA = [("roaa", "ROAA dương", "ROAA_TR_AVG4Q", "positive", _PCT2, "ROAA"), ("roaa_up", "ROAA tăng", "ROAA_TR_AVG4Q", "up", _PCT2, "ROAA")]
_EQUITY = ("equity_up", "Vốn chủ / tổng tài sản tăng", "EQUITY_TO_ASSET_AQ", "up", _PCT1, "Vốn chủ / tổng tài sản")
_MARGIN = ("margin_up", "Biên lợi nhuận ròng tăng", "NET_MARGIN_TR", "up", _PCT1, "Biên lợi nhuận ròng")
HEALTH = {
    "bank": ("Điểm sức khỏe ngân hàng", _ROAA + [
        ("npl_down", "Tỷ lệ nợ xấu giảm", "BAD_LOANS_RATIO_AQ", "down", _PCT2, "Nợ xấu"),
        ("overdue_down", "Tỷ lệ nợ quá hạn giảm", "OVERDUE_LOANS_RATIO_AQ", "down", _PCT2, "Nợ quá hạn"),
        ("coverage_up", "Bao phủ nợ xấu tăng", "PROVISION_BAD_LOANS_AQ", "up", _PCT0, "Bao phủ nợ xấu"),
        ("nim_up", "NIM tăng", "NET_INTEREST_MARGIN_TR_AVG5Q", "up", _PCT2, "NIM"), _EQUITY], False),
    "securities": ("Điểm sức khỏe công ty chứng khoán", _ROAA + [
        _MARGIN, _EQUITY, ("loans_down", "Cho vay / vốn chủ giảm", "LOANS_TO_EQUITY_AQ", "down", _TIMES, "Cho vay / vốn chủ")], True),
    "insurance": ("Điểm sức khỏe bảo hiểm", _ROAA + [
        ("combined_down", "Tỷ lệ kết hợp giảm", "COMBINED_RATIO_TR", "down", _PCT1, "Tỷ lệ kết hợp"), _MARGIN, _EQUITY], True),
}


def _quarter(iso: str) -> str:
    return f"Q{(int(iso[5:7]) + 2) // 3}/{iso[:4]}"


def _manual_bank_criteria(bank: dict[str, dict]) -> list[dict]:
    """CASA up and group-2 share down, latest owner-entered quarter against the same quarter a year before."""
    derived = {q: derive(v) for q, v in bank.items()}
    out = []
    for id_, label, key, rule, name in (("casa_up", "CASA tăng", "casa", "up", "CASA"), ("group2_down", "Tỷ lệ nợ nhóm 2 giảm", "group2_ratio", "down", "Nợ nhóm 2")):
        pairs = [q for q in sorted(derived, reverse=True) if derived[q][key] and derived.get(f"{int(q[:4]) - 1}{q[4:]}", {}).get(key)]
        if not pairs:
            latest = max((q for q in derived if derived[q][key]), default=max(derived))
            out.append(_criterion(id_, label, None, f"Cần số nhập tay của cùng quý năm trước (Q{latest[-1]}/{int(latest[:4]) - 1})"))
            continue
        q = pairs[0]
        a, b = Decimal(derived[q][key]), Decimal(derived[f"{int(q[:4]) - 1}{q[4:]}"][key])
        x, y = (_pct(a), _pct(b)) if _pct(a) != _pct(b) or a == b else (_pct(a, 2), _pct(b, 2))
        out.append(_criterion(id_, label, a > b if rule == "up" else a < b, f"{name} {x} so với {y} Q{q[-1]}/{int(q[:4]) - 1} (số nhập tay)"))
    return out


def _health(ratios: dict, share_issues: list[dict] | None, bank: dict | None = None) -> dict:
    title, criteria, with_issues = HEALTH[ratios["kind"]]
    quarters = ratios["quarters"]
    codes = {c[2] for c in criteria}

    def complete(q: str) -> bool:
        return codes <= set(quarters[q]) and codes <= set(quarters.get(f"{int(q[:4]) - 1}{q[4:]}", {}))
    # A quarter VNDirect has only partly published yet would leave criteria unevaluated: use the latest complete pair instead.
    latest = max((q for q in quarters if complete(q)), default=max(quarters))
    before_key = f"{int(latest[:4]) - 1}{latest[4:]}"
    now, before = quarters[latest], quarters.get(before_key, {})
    out = []
    for id_, label, code, rule, fmt, name in criteria:
        if code not in now or (rule != "positive" and code not in before):
            out.append(_criterion(id_, label, None, f"Thiếu {name} {_quarter(latest if code not in now else before_key)}"))
            continue
        a = Decimal(now[code])
        if rule == "positive":
            out.append(_criterion(id_, label, a > 0, f"{name} {fmt(a)}"))
            continue
        b = Decimal(before[code])
        x, y = (fmt(a), fmt(b)) if fmt(a) != fmt(b) or a == b else (fmt(a, 3), fmt(b, 3))
        out.append(_criterion(id_, label, a > b if rule == "up" else a < b, f"{name} {x} so với {y} cùng kỳ"))
    if with_issues:
        label = "Không phát hành cổ phiếu huy động vốn"
        since = (date.fromisoformat(latest) - timedelta(days=365)).isoformat()
        if share_issues is None:
            out.append(_criterion("no_issue", label, None, "Chưa có số liệu phát hành cổ phiếu (chờ lần cập nhật báo cáo sau)"))
        else:
            kinds = {i["kind"] for i in share_issues if since < i["date"] <= latest}
            out.append(_criterion("no_issue", label, False if "raise" in kinds else None if "other" in kinds else True,
                                  "Có đợt huy động vốn bằng cổ phiếu trong 12 tháng (quyền mua, riêng lẻ hoặc ESOP)" if "raise" in kinds
                                  else "Có đợt phát hành không rõ loại trong 12 tháng" if "other" in kinds
                                  else "Không có đợt huy động vốn bằng cổ phiếu trong 12 tháng (cổ phiếu thưởng, cổ tức bằng cổ phiếu không tính)"))
    if bank:
        out.extend(_manual_bank_criteria(bank))
    evaluated = [c for c in out if c["passed"] is not None]
    score = sum(1 for c in evaluated if c["passed"])
    return {"kind": "health", "title": title, "year": f"{_quarter(latest)} so với {_quarter(before_key)}",
            "score": score, "evaluated": len(evaluated), "level": _level(score, len(evaluated), len(out)), "criteria": out}


def report_quality(record: dict | None, sector: str | None, ratios: dict | None = None, bank: dict | None = None) -> dict:
    if sector in FINANCIAL:
        if not ratios or not ratios.get("quarters") or ratios.get("kind") not in HEALTH:
            return {"applicable": True, "reason": "Chưa có chỉ số ngành từ VNDirect (chờ lần cập nhật sau)", "f_score": None, "signs": [], "note": None}
        return {"applicable": True, "reason": None, "f_score": _health(ratios, (record or {}).get("share_issues"), bank), "signs": [], "note": None}
    a = _lines(record or {})
    years = [y for y, row in a.items() if "profit" in row]
    if not years:
        return {"applicable": True, "reason": "Chưa có số liệu báo cáo chi tiết (chờ lần cập nhật sau)", "f_score": None, "signs": [], "note": None}
    y = max(years)
    return {"applicable": True, "reason": None, "f_score": _f_score(a, (record or {}).get("share_issues"), y), "signs": _signs(a, y),
            "note": NOTES.get(sector)}
