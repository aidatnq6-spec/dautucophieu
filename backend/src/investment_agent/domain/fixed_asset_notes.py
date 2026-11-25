"""Thuyết minh TSCĐ nhập tay: the construction projects and depreciation ranges of a company as the owner reads them in its notes, which
VNDirect's statements do not carry. A project's expected quarter of completion changes only by a postponement, which is kept with its day
and reason; it closes when the owner confirms it done. Due once the report of that quarter is stored: the company's construction in
progress and cost of tangible assets are shown beside it, for the owner to judge (the statements do not split them by project). Not advice."""

import re
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from investment_agent.domain.property_projects import ProjectError, _amount

MAX_PROJECTS = 20
GROUPS = {"buildings": "Nhà cửa, vật kiến trúc", "machinery": "Máy móc, thiết bị", "vehicles": "Phương tiện vận tải, truyền dẫn",
          "office": "Thiết bị, dụng cụ quản lý", "livestock": "Vật nuôi, cây lâu năm", "other": "TSCĐ khác"}
_QUARTER = (re.compile(r"^Q([1-4])/(20\d{2})$"), re.compile(r"^(20\d{2})-Q([1-4])$"))
_YEAR = re.compile(r"^20\d{2}$")


class NoteError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def parse_quarter(raw) -> str:
    """Q3/2027 or 2027-Q3 → 2027-Q3."""
    text = str(raw or "").strip().upper()
    if m := _QUARTER[0].fullmatch(text):
        return f"{m.group(2)}-Q{m.group(1)}"
    if _QUARTER[1].fullmatch(text):
        return text
    raise NoteError("invalid_quarter", "Quý dạng Q3/2027.")


def _period(raw) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if _YEAR.fullmatch(text):
        return text
    try:
        return parse_quarter(text)
    except NoteError:
        raise NoteError("invalid_period", "Kỳ báo cáo dạng 2025 hoặc Q2/2026.") from None


def _money(raw) -> str | None:
    try:
        return _amount(raw)
    except ProjectError as exc:
        raise NoteError(exc.code, exc.message) from None


def _ranges(raw: dict) -> dict:
    groups = {}
    for key, value in raw.items():
        if key == "period":
            continue
        if key not in GROUPS:
            raise NoteError("invalid_group", "Nhóm tài sản không có trong thuyết minh.")
        try:
            low, high = int(str(value.get("from")).strip()), int(str(value.get("to")).strip())
        except (AttributeError, TypeError, ValueError):
            raise NoteError("invalid_range", "Số năm khấu hao là số nguyên.") from None
        if not 0 <= low <= high <= 100:
            raise NoteError("invalid_range", "Số năm khấu hao từ 0 đến 100, \"từ\" không lớn hơn \"đến\".")
        groups[key] = {"from": low, "to": high}
    return {"period": _period(raw.get("period")), "groups": {k: groups[k] for k in GROUPS if k in groups}}


def validate_notes(raw_projects: list, raw_ranges: dict, *, stored: list[dict]) -> tuple[list[dict], dict]:
    """The owner's projects and ranges; a stored project keeps its status, completion day and postponements, and its quarter unless postponed."""
    if len(raw_projects) > MAX_PROJECTS:
        raise NoteError("too_many", f"Tối đa {MAX_PROJECTS} dự án mỗi mã.")
    kept = {p["id"]: p for p in stored}
    out = []
    for p in raw_projects:
        name = str(p.get("name") or "").strip()
        if not name or len(name) > 120:
            raise NoteError("invalid_name", "Tên dự án từ 1 đến 120 ký tự.")
        due = parse_quarter(p.get("due"))
        url = str(p.get("source_url") or "").strip()
        if url and not re.fullmatch(r"https?://\S{3,500}", url):
            raise NoteError("invalid_source", "Link nguồn phải bắt đầu bằng http:// hoặc https://.")
        old = kept.get(str(p.get("id") or ""))
        if old and old["due"] != due:
            raise NoteError("due_locked", "Đổi quý hoàn thành dự kiến bằng nút Lùi hạn.")
        out.append({"id": old["id"] if old else uuid.uuid4().hex[:12], "name": name, "due": due, "read_period": _period(p.get("read_period")),
                    "cip_value": _money(p.get("cip_value")), "budget": _money(p.get("budget")), "source_url": url or None,
                    "note": str(p.get("note") or "").strip()[:500], "status": old["status"] if old else "open",
                    "done_on": old["done_on"] if old else None, "postpones": old["postpones"] if old else []})
    return out, _ranges(raw_ranges or {})


def _find(projects: list[dict], pid: str) -> dict:
    p = next((p for p in projects if p["id"] == pid), None)
    if p is None:
        raise NoteError("not_found", "Không thấy dự án này; hãy tải lại.")
    if p["status"] != "open":
        raise NoteError("not_open", "Dự án đã ghi là hoàn thành.")
    return p


def postpone(projects: list[dict], pid: str, to, reason: str, *, today: date) -> list[dict]:
    p, new = _find(projects, pid), parse_quarter(to)
    if new <= p["due"]:
        raise NoteError("not_later", "Quý mới phải sau quý hoàn thành dự kiến hiện tại.")
    entry = {"from": p["due"], "to": new, "on": today.isoformat(), "reason": str(reason or "").strip()[:200]}
    return [{**x, "due": new, "postpones": [*x["postpones"], entry]} if x["id"] == pid else x for x in projects]


def complete(projects: list[dict], pid: str, *, today: date) -> list[dict]:
    _find(projects, pid)
    return [{**x, "status": "done", "done_on": today.isoformat()} if x["id"] == pid else x for x in projects]


def _quarter_end(q: str) -> date:
    year, n = int(q[:4]), int(q[-1])
    return date(year + 1, 1, 1) if n == 4 else date(year, 3 * n + 1, 1)


def _figures(statements: dict, period: str | None) -> dict | None:
    if not period:
        return None
    row = (statements.get("years" if _YEAR.fullmatch(period) else "quarters") or {}).get(period)
    return None if row is None else {"period": period, "cip": row.get("cip"), "ppe_gross": row.get("ppe_gross")}


def due_view(projects: list[dict], statements: dict, *, today: date) -> list[dict]:
    """Each project with its state (done; due: its quarter's report is stored; waiting_report: the quarter is over, the report not yet;
    upcoming) and the company's figures at the period read, at the due quarter and at the latest stored quarter."""
    quarters = statements.get("quarters") or {}
    latest = max((q for q, row in quarters.items() if "cip" in row), default=None)
    out = []
    for p in projects:
        at_due = _figures(statements, p["due"]) if "cip" in (quarters.get(p["due"]) or {}) else None
        state = "done" if p["status"] == "done" else "due" if at_due else "waiting_report" if today >= _quarter_end(p["due"]) else "upcoming"
        out.append({**p, "state": state, "at_read": _figures(statements, p["read_period"]), "at_due": at_due, "latest": _figures(statements, latest)})
    return out


# Chi phí trả trước: phân bổ trong năm (25/11/2026). The notes give each year's allocation by kind; VNDirect does not. The years left are
# the year-end long-term prepaid expenses over that year's allocation, at that pace, from the owner's figure and the stored balance.
PREPAID_KINDS = {"tools": "Công cụ dụng cụ", "overhaul": "Sửa chữa lớn", "land": "Tiền thuê đất, đền bù", "preop": "Chi phí trước hoạt động",
                 "other": "Khác"}
MAX_PREPAID_YEARS = 15


def validate_prepaid(raw: dict) -> dict[str, dict[str, str]]:
    """year → {kind: tỷ đồng, and "total" when the notes give it}."""
    if len(raw) > MAX_PREPAID_YEARS:
        raise NoteError("too_many", f"Tối đa {MAX_PREPAID_YEARS} năm.")
    out = {}
    for year, items in raw.items():
        if not _YEAR.fullmatch(str(year)):
            raise NoteError("invalid_year", "Năm dạng 2021.")
        kept = {}
        for kind, value in (items or {}).items():
            if kind != "total" and kind not in PREPAID_KINDS:
                raise NoteError("invalid_kind", "Loại chi phí trả trước không có trong danh sách.")
            if (amount := _money(value)) is not None:
                kept[kind] = amount
        if not kept:
            raise NoteError("empty_year", f"Năm {year}: nhập ít nhất một số.")
        out[str(year)] = {k: kept[k] for k in [*PREPAID_KINDS, "total"] if k in kept}
    return dict(sorted(out.items()))


def prepaid_view(prepaid: dict[str, dict[str, str]], statements: dict) -> list[dict]:
    """Each year with its total (as written, or the kinds added up), the stored long-term prepaid expenses at that year's end, the years
    left at that pace and the allocation against that year's profit before tax (none when a figure is missing or not positive)."""
    out = []
    for year, items in prepaid.items():
        kinds = {k: v for k, v in items.items() if k != "total"}
        summed = "total" not in items
        total = Decimal(items["total"]) if not summed else sum((Decimal(v) for v in kinds.values()), Decimal(0))
        row = (statements.get("years") or {}).get(year) or {}
        lt, pbt = row.get("prepaid_lt"), row.get("pbt")
        per_year = total * 10**9
        out.append({"year": year, "items": kinds, "total": format(total.normalize(), "f"), "summed": summed, "prepaid_lt": lt,
                    "years_left": str((Decimal(lt) / per_year).quantize(Decimal("0.1"), ROUND_HALF_UP)) if lt is not None and per_year > 0 else None,
                    "to_pbt": str((per_year / Decimal(pbt)).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if pbt is not None and Decimal(pbt) > 0 else None})
    return out


# Thương vụ mua bán, sáp nhập (25/11/2026), from the notes on business combinations, which VNDirect does not carry. Goodwill by the
# lesson's formula: price − share × fair value of the net assets bought; positive, an asset amortised straight-line over the years the
# owner writes (VAS: at most 10); negative, a bargain purchase booked as a one-off gain in the year of the deal.
MAX_DEALS, MAX_YEARS = 20, 10
_DMY = re.compile(r"^(\d{1,2})/(\d{1,2})/(20\d{2})$")


def _signed(raw, *, required: bool = True) -> str:
    text = str(raw or "").strip()
    negative = text.startswith(("-", "−"))
    value = _money(text[1:] if negative else text)
    if value is None:
        if required:
            raise NoteError("invalid_amount", "Nhập số tỷ đồng.")
        return None
    return format((-Decimal(value) if negative else Decimal(value)).normalize(), "f")


def _day(raw) -> str:
    text = str(raw or "").strip()
    m = _DMY.fullmatch(text)
    try:
        return (date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else date.fromisoformat(text)).isoformat()
    except (TypeError, ValueError):
        raise NoteError("invalid_date", "Ngày mua dạng 15/03/2024.") from None


def validate_deals(raw: list) -> list[dict]:
    if len(raw) > MAX_DEALS:
        raise NoteError("too_many", f"Tối đa {MAX_DEALS} thương vụ mỗi mã.")
    out = []
    for d in raw:
        name = str(d.get("name") or "").strip()
        if not name or len(name) > 120:
            raise NoteError("invalid_name", "Tên công ty được mua từ 1 đến 120 ký tự.")
        day = _day(d.get("date"))
        try:
            share = Decimal(str(d.get("share") or "").strip().replace(",", "."))
        except InvalidOperation:
            share = Decimal(-1)
        if not share.is_finite() or not 0 < share <= 100:
            raise NoteError("invalid_share", "Tỷ lệ mua từ trên 0 đến 100%.")
        years_raw = str(d.get("years") or "").strip()
        try:
            years = int(years_raw) if years_raw else None
        except ValueError:
            years = 0
        if years is not None and not 1 <= years <= MAX_YEARS:
            raise NoteError("invalid_years", f"Số năm phân bổ từ 1 đến {MAX_YEARS} (VAS).")
        url = str(d.get("source_url") or "").strip()
        if url and not re.fullmatch(r"https?://\S{3,500}", url):
            raise NoteError("invalid_source", "Link nguồn phải bắt đầu bằng http:// hoặc https://.")
        out.append({"id": str(d.get("id") or uuid.uuid4().hex[:12])[:32], "name": name, "date": day, "share": format(share.normalize(), "f"),
                    "price": _signed(d.get("price")), "net_assets": _signed(d.get("net_assets")), "years": years, "source_url": url or None,
                    "note": str(d.get("note") or "").strip()[:500],
                    # Hợp nhất kinh doanh (25/11/2026): the goodwill as the notes give it, and the part of non-controlling interests
                    "note_goodwill": _signed(d.get("note_goodwill"), required=False), "nci_part": _money(d.get("nci_part"))})
    return sorted(out, key=lambda d: d["date"])


def deals_view(deals: list[dict], *, today: date) -> list[dict]:
    """Each deal with its goodwill (tỷ), kind (goodwill or bargain), yearly charge and end of the schedule when the years are written,
    whether it still charges profit today, and for a bargain the year of its one-off gain."""
    out = []
    for d in deals:
        computed = Decimal(d["price"]) - Decimal(d["share"]) / 100 * Decimal(d["net_assets"])
        note = Decimal(d["note_goodwill"]) if d.get("note_goodwill") is not None else None
        goodwill = computed if note is None else note  # the notes' figure, when written, is the one the statements carry
        bought = date.fromisoformat(d["date"])
        row = {**d, "note_goodwill": d.get("note_goodwill"), "nci_part": d.get("nci_part"), "computed": _text(computed),
               "gap": None if note is None else _text(computed - note),
               "goodwill": _text(goodwill), "kind": "goodwill" if goodwill > 0 else "bargain" if goodwill < 0 else "none",
               "per_year": None, "ends": None, "charging": False, "gain_year": str(bought.year) if goodwill < 0 else None}
        if goodwill > 0 and d["years"]:
            ends = bought.replace(year=bought.year + d["years"]) if not (bought.month == 2 and bought.day == 29) else date(bought.year + d["years"], 2, 28)
            row |= {"per_year": format((goodwill / d["years"]).quantize(Decimal("0.1"), ROUND_HALF_UP).normalize(), "f"), "ends": ends.isoformat(),
                    "charging": bought <= today < ends}
        out.append(row)
    return out


def _text(v: Decimal) -> str:
    return format(v.normalize(), "f") if v else "0"


def validate_amort(raw: dict) -> dict[str, str]:
    """year → goodwill amortised that year as the notes give it (tỷ đồng); VNDirect's line is mostly empty."""
    if len(raw) > MAX_PREPAID_YEARS:
        raise NoteError("too_many", f"Tối đa {MAX_PREPAID_YEARS} năm.")
    out = {}
    for year, value in raw.items():
        if not _YEAR.fullmatch(str(year)):
            raise NoteError("invalid_year", "Năm dạng 2021.")
        if (amount := _money(value)) is not None:
            out[str(year)] = amount
    return dict(sorted(out.items()))


def _bn(row: dict, key: str) -> Decimal | None:
    v = row.get(key)
    return None if v is None else Decimal(v) / 10**9


def goodwill_moves(deals: list[dict], amort: dict[str, str], statements: dict) -> list[dict]:
    """Each year with a stored year before it and goodwill at either end: opening and closing (stored), added (the positive goodwill of
    the owner's deals that year), amortised (the owner's figure from the notes), the decline opening + added − closing, and what
    amortisation leaves of it (disposals, write-offs: the statements do not tell them apart); amortisation against administrative
    expenses and profit before tax. In tỷ đồng."""
    years = statements.get("years") or {}
    out = []
    for y in sorted(years):
        before = years.get(str(int(y) - 1))
        if before is None:
            continue
        opening, closing = _bn(before, "goodwill"), _bn(years[y], "goodwill")
        if opening is None or closing is None or (opening == 0 and closing == 0 and y not in amort):
            continue
        added = sum((Decimal(d["goodwill"]) for d in deals if d["kind"] == "goodwill" and d["date"][:4] == y), Decimal(0))
        amortised = Decimal(amort[y]) if y in amort else None
        decline = opening + added - closing
        admin, pbt = _bn(years[y], "admin"), _bn(years[y], "pbt")
        q = lambda a, b: str((a / b).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if a is not None and b is not None and b > 0 else None  # noqa: E731
        out.append({"year": y, "opening": _text(opening), "added": _text(added), "amortised": None if amortised is None else _text(amortised), "closing": _text(closing),
                    "decline": _text(decline), "other": None if amortised is None else _text(decline - amortised),
                    "to_admin": q(amortised, admin), "to_pbt": q(amortised, pbt)})
    return out


BARGAIN_SHARE = Decimal("0.10")  # bargain gains against profit before tax (owner, 25/11/2026)


def bargain_years(deals: list[dict], statements: dict) -> list[dict]:
    """Each year with a bargain purchase among the owner's deals: the gain (no cash came with it), profit before tax with and without it,
    and the sign: the gain from a tenth of profit before tax, or any gain in a year of loss before tax; none without the year's profit."""
    years, out = statements.get("years") or {}, []
    for y in sorted({d["gain_year"] for d in deals if d["kind"] == "bargain"}):
        mine = [d for d in deals if d["kind"] == "bargain" and d["gain_year"] == y]
        gain = -sum((Decimal(d["goodwill"]) for d in mine), Decimal(0))
        pbt = _bn(years.get(y) or {}, "pbt")
        share = None if pbt is None or pbt <= 0 else str((gain / pbt).quantize(Decimal("0.0001"), ROUND_HALF_UP))
        out.append({"year": y, "gain": _text(gain), "deals": [d["name"] for d in mine], "pbt": None if pbt is None else _text(pbt), "share": share,
                    "pbt_without": None if pbt is None else _text(pbt - gain),
                    "flag": None if pbt is None else (pbt <= 0 or gain >= BARGAIN_SHARE * pbt)})
    return out


# Các khoản vay (25/11/2026), from the notes on borrowings, which VNDirect does not carry: lender, currency, term, balance (tỷ đồng as
# converted in the notes), rate range or a floating base with its margin, maturity year, collateral. Rates are shown as ranges, never
# averaged into one figure; the exchange scenario is the owner's own fall of the đồng, not a forecast.
MAX_LOANS = 30
CURRENCIES = ("VND", "USD", "EUR", "JPY", "CNY", "khác")
TERMS = {"short": "Ngắn hạn", "long": "Dài hạn"}


def _rate(raw) -> Decimal | None:
    text = str(raw or "").strip().replace("%", "").replace(",", ".")
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise NoteError("invalid_rate", "Lãi suất là số phần trăm/năm, ví dụ 6,5.") from None
    if not value.is_finite() or not 0 <= value <= 100:
        raise NoteError("invalid_rate", "Lãi suất từ 0 đến 100%/năm.")
    return value


def _pct_text(v: Decimal) -> str:
    return format(v.normalize(), "f")


def validate_loans(raw: list) -> list[dict]:
    if len(raw) > MAX_LOANS:
        raise NoteError("too_many", f"Tối đa {MAX_LOANS} khoản vay mỗi mã.")
    out = []
    for loan in raw:
        lender = str(loan.get("lender") or "").strip()
        if not lender or len(lender) > 120:
            raise NoteError("invalid_name", "Bên cho vay từ 1 đến 120 ký tự.")
        currency = str(loan.get("currency") or "").strip()
        if currency not in CURRENCIES:
            raise NoteError("invalid_currency", "Loại tiền: " + ", ".join(CURRENCIES) + ".")
        term = str(loan.get("term") or "").strip()
        if term not in TERMS:
            raise NoteError("invalid_term", "Kỳ hạn là ngắn hạn hoặc dài hạn.")
        balance = _money(loan.get("balance"))
        if balance is None:
            raise NoteError("invalid_amount", "Nhập dư nợ (tỷ đồng).")
        low, high, margin = _rate(loan.get("rate_from")), _rate(loan.get("rate_to")), _rate(loan.get("margin"))
        if low is not None and high is not None and low > high:
            raise NoteError("invalid_rate", "Lãi suất \"từ\" không lớn hơn \"đến\".")
        maturity = str(loan.get("maturity") or "").strip()
        if maturity and not _YEAR.fullmatch(maturity):
            raise NoteError("invalid_year", "Năm đáo hạn dạng 2025.")
        out.append({"id": str(loan.get("id") or uuid.uuid4().hex[:12])[:32], "lender": lender, "currency": currency, "term": term, "balance": balance,
                    "rate_from": None if low is None else _pct_text(low), "rate_to": None if high is None else _pct_text(high),
                    "base": str(loan.get("base") or "").strip()[:30] or None, "margin": None if margin is None else _pct_text(margin),
                    "maturity": maturity or None, "collateral": str(loan.get("collateral") or "").strip()[:300],
                    "note": str(loan.get("note") or "").strip()[:500]})
    return out


def validate_debt_notes(raw: dict) -> dict:
    """The period the loans were read from, the long-term debt due within a year (the notes), and the owner's fall of the đồng (%)."""
    out = {}
    if (period := _period(raw.get("period"))) is not None:
        out["period"] = period
    if (portion := _money(raw.get("current_portion"))) is not None:
        out["current_portion"] = portion
    shock = str(raw.get("fx_shock") or "").strip().replace(",", ".").replace("%", "")
    if shock:
        try:
            value = Decimal(shock)
        except InvalidOperation:
            value = Decimal(-1)
        if not value.is_finite() or not 0 < value <= 100:
            raise NoteError("invalid_shock", "Mức đồng Việt Nam mất giá từ trên 0 đến 100%.")
        out["fx_shock"] = _pct_text(value)
    return out


def debt_view(loans: list[dict], notes: dict, statements: dict) -> dict:
    """Totals of the owner's loans by currency, term and maturity year (tỷ đồng), each currency's rate range and floating rates, the
    borrowings on the balance sheet at the period read and the share the loans cover, and the exchange scenario: the foreign-currency
    balance × the owner's fall of the đồng, against that period's profit before tax."""
    def add(bucket: dict, key: str, v: Decimal) -> None:
        bucket[key] = bucket.get(key, Decimal(0)) + v
    by_currency, by_term, maturities, rates = {}, {}, {}, {}
    for loan in loans:
        v = Decimal(loan["balance"])
        add(by_currency, loan["currency"], v)
        add(by_term, loan["term"], v)
        add(maturities, loan["maturity"] or "none", v)
        r = rates.setdefault(loan["currency"], {"from": None, "to": None, "floating": []})
        for key, pick in (("rate_from", min), ("rate_to", max)):
            if loan[key] is not None:
                cur = r["from" if key == "rate_from" else "to"]
                r["from" if key == "rate_from" else "to"] = loan[key] if cur is None else _pct_text(pick(Decimal(cur), Decimal(loan[key])))
        if loan["base"] or loan["margin"]:
            margin = f" + {loan['margin'].replace('.', ',')}%" if loan["margin"] else ""
            r["floating"].append(f"{loan['base'] or 'thả nổi'}{margin}")
    total = sum(by_currency.values(), Decimal(0))
    period = notes.get("period")
    row = ((statements.get("years" if period and _YEAR.fullmatch(period) else "quarters") or {}).get(period) or {}) if period else {}
    st, lt = _bn(row, "st_debt"), _bn(row, "lt_debt")
    reported = None if st is None or lt is None else st + lt
    foreign = sum((v for c, v in by_currency.items() if c != "VND"), Decimal(0))
    shock = Decimal(notes["fx_shock"]) / 100 if "fx_shock" in notes else None
    loss = None if shock is None else foreign * shock
    pbt = _bn(row, "pbt")
    def text(d: dict) -> dict:
        return {k: _text(v) for k, v in sorted(d.items())}
    return {"period": period, "total": _text(total), "by_currency": text(by_currency), "by_term": text(by_term),
            "maturities": dict(sorted(text(maturities).items(), key=lambda kv: (kv[0] == "none", kv[0]))), "rates": dict(sorted(rates.items())),
            "reported": None if reported is None else _text(reported),
            "covered": str((total / reported).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if reported else None,
            "current_portion": notes.get("current_portion"), "fx_shock": notes.get("fx_shock"), "foreign": _text(foreign),
            "fx_loss": None if loss is None else _text(loss),
            "fx_to_pbt": str((loss / pbt).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if loss is not None and pbt is not None and pbt > 0 else None}


# Doanh thu, giá vốn theo mảng (25/11/2026), from the notes on revenue and cost of sales (HPG 2021: notes 31, 32), which VNDirect does not
# split: each period's segments with their revenue and cost of sales (tỷ đồng); gross profit, margin and share of the total gross profit
# follow, and the totals are checked against the stored net revenue and cost of sales.
MAX_SEGMENTS, MAX_SEGMENT_PERIODS = 12, 15


def validate_segments(raw: dict) -> dict[str, list[dict]]:
    if len(raw) > MAX_SEGMENT_PERIODS:
        raise NoteError("too_many", f"Tối đa {MAX_SEGMENT_PERIODS} kỳ.")
    out = {}
    for period_raw, items in raw.items():
        period = _period(period_raw)
        if period is None:
            raise NoteError("invalid_period", "Kỳ báo cáo dạng 2025 hoặc Q2/2026.")
        if not items:
            raise NoteError("empty_year", f"Kỳ {period_raw}: ghi ít nhất một mảng.")
        if len(items) > MAX_SEGMENTS:
            raise NoteError("too_many", f"Tối đa {MAX_SEGMENTS} mảng mỗi kỳ.")
        rows = []
        for item in items:
            name = str(item.get("name") or "").strip()
            if not name or len(name) > 120:
                raise NoteError("invalid_name", "Tên mảng từ 1 đến 120 ký tự.")
            revenue, cogs = _money(item.get("revenue")), _money(item.get("cogs"))
            if revenue is None or cogs is None:
                raise NoteError("invalid_amount", "Nhập doanh thu và giá vốn của mảng (tỷ đồng).")
            rows.append({"name": name, "revenue": revenue, "cogs": cogs})
        out[period] = rows
    return dict(sorted(out.items()))


def _share(a: Decimal, b: Decimal) -> str | None:
    return str((a / b).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if b else None


def segments_view(segments: dict[str, list[dict]], statements: dict) -> list[dict]:
    out = []
    for period, items in segments.items():
        rows, revenue, cogs = [], Decimal(0), Decimal(0)
        for item in items:
            r, c = Decimal(item["revenue"]), Decimal(item["cogs"])
            revenue, cogs = revenue + r, cogs + c
            rows.append({**item, "gross": _text(r - c), "margin": _share(r - c, r) if r > 0 else None})
        gross = revenue - cogs
        for row in rows:
            row["share"] = _share(Decimal(row["gross"]), gross) if gross > 0 else None
        stored = (statements.get("years" if _YEAR.fullmatch(period) else "quarters") or {}).get(period) or {}
        reported_revenue, reported_cogs = _bn(stored, "revenue"), _bn(stored, "cogs")
        out.append({"period": period, "rows": rows, "revenue": _text(revenue), "cogs": _text(cogs), "gross": _text(gross),
                    "margin": _share(gross, revenue) if revenue > 0 else None,
                    "reported_revenue": None if reported_revenue is None else _text(reported_revenue),
                    "reported_cogs": None if reported_cogs is None else _text(reported_cogs),
                    "revenue_gap": None if reported_revenue is None else _text(revenue - reported_revenue),
                    "cogs_gap": None if reported_cogs is None else _text(cogs - reported_cogs)})
    return out


# Doanh thu tài chính theo loại và lãi vay vốn hóa (25/11/2026), from the notes on financial income and borrowing costs, which VNDirect does
# not split: the part hard to repeat or not yet cashed (interest on loans to related parties, gains on disposals, unrealised exchange gains),
# profit before tax without it, and the interest the company really bore (expensed + capitalised into construction in progress).
FIN_KINDS = {"deposit": "Lãi tiền gửi", "lending": "Lãi cho vay", "lending_related": "trong đó: cho bên liên quan vay", "dividends": "Cổ tức, lợi nhuận được chia",
             "fx_realised": "Lãi tỷ giá đã thực hiện", "fx_unrealised": "Lãi tỷ giá chưa thực hiện", "disposals": "Lãi thanh lý, chuyển nhượng đầu tư",
             "other": "Doanh thu tài chính khác", "capitalised_interest": "Lãi vay đã vốn hóa trong năm"}
_NOT_INCOME = ("lending_related", "capitalised_interest")  # a part of lending; not financial income at all
HARD_TO_REPEAT = ("lending_related", "disposals", "fx_unrealised")


def validate_fin_notes(raw: dict) -> dict[str, dict[str, str]]:
    if len(raw) > MAX_PREPAID_YEARS:
        raise NoteError("too_many", f"Tối đa {MAX_PREPAID_YEARS} năm.")
    out = {}
    for year, items in raw.items():
        if not _YEAR.fullmatch(str(year)):
            raise NoteError("invalid_year", "Năm dạng 2021.")
        kept = {}
        for kind, value in (items or {}).items():
            if kind not in FIN_KINDS:
                raise NoteError("invalid_kind", "Loại doanh thu tài chính không có trong danh sách.")
            if (amount := _money(value)) is not None:
                kept[kind] = amount
        if not kept:
            raise NoteError("empty_year", f"Năm {year}: nhập ít nhất một số.")
        if "lending_related" in kept and Decimal(kept["lending_related"]) > Decimal(kept.get("lending", "0")):
            raise NoteError("related_over_lending", "Lãi cho bên liên quan vay là một phần của lãi cho vay, không lớn hơn lãi cho vay.")
        out[str(year)] = {k: kept[k] for k in FIN_KINDS if k in kept}
    return dict(sorted(out.items()))


def fin_notes_view(notes: dict[str, dict[str, str]], statements: dict) -> list[dict]:
    years, out = statements.get("years") or {}, []
    for year, items in notes.items():
        d = {k: Decimal(v) for k, v in items.items()}
        entered = sum((v for k, v in d.items() if k not in _NOT_INCOME), Decimal(0))
        hard = sum((d.get(k, Decimal(0)) for k in HARD_TO_REPEAT), Decimal(0))
        row = years.get(year) or {}
        reported, pbt, interest = _bn(row, "fin_income"), _bn(row, "pbt"), _bn(row, "interest")
        capitalised = d.get("capitalised_interest")
        out.append({"year": year, "items": items, "entered": _text(entered), "reported": None if reported is None else _text(reported),
                    "gap": None if reported is None else _text(entered - reported), "hard_to_repeat": _text(hard),
                    "pbt": None if pbt is None else _text(pbt), "share": _share(hard, pbt) if pbt is not None and pbt > 0 else None,
                    "pbt_without": None if pbt is None else _text(pbt - hard), "interest_expensed": None if interest is None else _text(interest),
                    "interest_total": None if interest is None or capitalised is None else _text(interest + capitalised),
                    "capitalised_share": _share(capitalised, pbt) if capitalised is not None and pbt is not None and pbt > 0 else None})
    return out


# Ưu đãi thuế (25/11/2026), from the notes on income tax (HPG 2021: note 40.3): which subsidiary or project is taxed below the standard 20%,
# exempt or halved, and until which year; in that year Việc cần xem says the effective rate may rise from the next.
INCENTIVE_KINDS = {"rate": "thuế suất ưu đãi", "exempt": "miễn thuế", "half": "giảm 50% thuế"}
MAX_INCENTIVES = 20
STANDARD_RATE = Decimal(20)


def validate_incentives(raw: list) -> list[dict]:
    if len(raw) > MAX_INCENTIVES:
        raise NoteError("too_many", f"Tối đa {MAX_INCENTIVES} ưu đãi mỗi mã.")
    out = []
    for item in raw:
        entity = str(item.get("entity") or "").strip()
        if not entity or len(entity) > 120:
            raise NoteError("invalid_name", "Công ty con hoặc dự án từ 1 đến 120 ký tự.")
        kind = str(item.get("kind") or "").strip()
        if kind not in INCENTIVE_KINDS:
            raise NoteError("invalid_kind", "Loại ưu đãi: thuế suất ưu đãi, miễn thuế hoặc giảm 50%.")
        rate = _rate(item.get("rate")) if kind == "rate" else None
        if kind == "rate" and (rate is None or not 0 < rate < STANDARD_RATE):
            raise NoteError("invalid_rate", "Thuế suất ưu đãi từ trên 0 đến dưới 20%.")
        until = str(item.get("until") or "").strip()
        if not _YEAR.fullmatch(until):
            raise NoteError("invalid_year", "Năm hết ưu đãi dạng 2026.")
        url = str(item.get("source_url") or "").strip()
        if url and not re.fullmatch(r"https?://\S{3,500}", url):
            raise NoteError("invalid_source", "Link nguồn phải bắt đầu bằng http:// hoặc https://.")
        out.append({"id": str(item.get("id") or uuid.uuid4().hex[:12])[:32], "entity": entity, "kind": kind,
                    "rate": None if rate is None else _pct_text(rate), "until": until, "source_url": url or None, "note": str(item.get("note") or "").strip()[:500]})
    return sorted(out, key=lambda i: i["until"])


def incentives_view(incentives: list[dict], *, today: date) -> list[dict]:
    """Each incentive with its state: ending (its last year is this one), ended, or active."""
    year = str(today.year)
    return [{**i, "state": "ending" if i["until"] == year else "ended" if i["until"] < year else "active"} for i in incentives]


def incentive_text(i: dict) -> str:
    return f"thuế suất ưu đãi {i['rate'].replace('.', ',')}%" if i["kind"] == "rate" else INCENTIVE_KINDS[i["kind"]]
