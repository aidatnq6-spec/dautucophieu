"""Full financial statements of watched non-financial companies from VNDirect's public statements API, for Bảng số tài chính.

The free Vnstock tier keeps eight periods and has no interest expense, depreciation, borrowings or capital spending; VNDirect's
statements carry them, by quarter from 2015 and by year from 2012, each quarter on its own (not year to date: four quarters add
up to the year). robots.txt of api-finfo.vndirect.com.vn answers 404, so nothing is disallowed (checked 07/11/2026); the ratios
of banks, securities firms and insurers already come from the same API.

Only the lines the table needs are kept, as decimal strings in đồng with VNDirect's signs (costs positive, cash paid out
negative). A line given twice with different values is a conflict: no value is kept and both are listed, never one chosen.
Banks, securities firms and insurers use their own layouts (LAYOUTS) and are kept apart, under data/statements-financial, with
only the lines of their scale and valuation block. The first sync of a ticker takes the
whole history; later ones take the last two years and replace those periods, keeping the older ones. A third call keeps each
year's last unadjusted close (VNDirect prices, from 2013) for the market capitalisation of that year. One JSON file per ticker
under data/statements.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .financial_ratios import kind_of
from .leading import _get_with_retry

URL = ("https://api-finfo.vndirect.com.vn/v4/financial_statements?q=code:{symbol}~reportType:{kind}~modelType:{models}"
       "~fiscalDate:gte:{start}&size={page}")
PAGE = 60000  # rows per call: a securities firm's whole quarterly history is about 27,000; a full page may be cut and is refused
# Unadjusted daily closes (thousand đồng; from 2013), for each year's market capitalisation at that year's own price and share count.
PRICE_URL = "https://api-finfo.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{symbol}~date:gte:{start}&size=9999&fields=code,date,close"
FIRST_START, REFRESH_DAYS, MAX_AGE_DAYS, PACE_SECONDS = "2010-01-01", 730, 7, 1.0
# Raised when LINES gains lines: a non-financial ticker kept with an older version is due and takes its whole history once, so the new
# lines reach back as far as the old ones. 2: customer advances and inventory.
LINES_VERSION = 13  # 3: current assets, receivables, current and long-term liabilities, EPS; 4: the parts of receivables; 5: interest received;
# 6: inventory at cost and its provision (Khối Tồn kho, 22/11/2026); 7: no new line, the whole history read once for the update days of
# years before the 2-year refresh (Dự phòng chốt khi kiểm toán, review 23/11/2026)
# 8: fixed assets, investment property and construction in progress (Tài sản cố định, 25/11/2026); 9: prepaid expenses (Chi phí trả trước);
# 10: goodwill and its amortisation (Lợi thế thương mại); 11: borrowing cash flows, unrealised exchange differences (Nợ vay);
# 12: parts of equity and the cash to and from shareholders (Vốn chủ sở hữu); 13: current and deferred tax, tax paid, deferred balances (Thuế TNDN)
FIN_LINES_VERSION = 3  # banks, securities firms and insurers: 2: basic EPS (23001 in each of their layouts); 3: the bank's loans, loan
# reserve, accrued interest, interest income and provision expense (Chất lượng tài sản ngân hàng, 23/11/2026; the others re-read once too)
# (model, item code) → line. Model 1 balance sheet, 2 income statement, 3 cash flow (indirect); the general layout (TT200).
LINES = {
    (2, 21000): "gross_revenue", (2, 21090): "deductions", (2, 21001): "revenue", (2, 22100): "cogs", (2, 23100): "gross_profit",
    (2, 22110): "selling", (2, 22200): "admin", (2, 21500): "fin_income", (2, 22500): "fin_expense", (2, 22510): "interest",
    (2, 23300): "associates", (2, 23200): "associates_old", (2, 23900): "other_profit", (2, 23800): "pbt", (2, 22070): "tax",
    (2, 23003): "npat", (2, 23500): "minority_profit", (2, 23000): "npat_parent",
    (1, 11100): "cash", (1, 11200): "st_investments", (1, 12700): "total_assets", (1, 13000): "liabilities", (1, 13110): "st_debt",
    (1, 13340): "lt_debt", (1, 14000): "equity", (1, 14240): "minority_equity", (1, 15000): "minority_equity_outside", (1, 14110): "charter_capital",
    # Customer advances (Người mua trả tiền trước, short term 13130 and long term 13311) and inventory (11400, after its provision): names
    # from VNDirect's own model list (v4/financial_models, checked 11/11/2026), for Tiền khách trả trước of property developers.
    (1, 13130): "advances_st", (1, 13311): "advances_lt", (1, 11400): "inventory",
    (1, 11410): "inventory_gross", (1, 11490): "inventory_provision",  # Khối Tồn kho: at cost and the provision for a fall in value
    # For the fundamentals record (Chất lượng báo cáo, EPS) since Vnstock 6.0.0: current assets, short-term receivables, current and
    # long-term liabilities, basic EPS (đồng). Names from v4/financial_models, checked 13/11/2026.
    (1, 11000): "current_assets", (1, 11300): "receivables", (1, 13100): "current_liabilities", (1, 13300): "long_liabilities",
    (2, 23001): "eps",
    # Phải thu by part (short term 113xx, long term 121xx; provisions negative), for Bóc tách phải thu, số ngày thu tiền and dự phòng;
    # names from v4/financial_models (modelType 1, NON_FINANCE), checked 15/11/2026.
    (1, 11310): "ar_customers", (1, 11320): "prepay_suppliers", (1, 11345): "st_loans_receivable", (1, 11350): "other_receivables",
    (1, 11390): "bad_debt_st", (1, 12100): "receivables_lt", (1, 12110): "ar_customers_lt", (1, 12140): "lt_loans_receivable",
    (1, 12180): "other_receivables_lt", (1, 12190): "bad_debt_lt",
    # Tiền thu lãi cho vay, cổ tức và lợi nhuận được chia (investing cash flow), against financial income for Lợi nhuận giấy; checked
    # in v4/financial_models (modelType 3) on 16/11/2026
    (3, 32700): "interest_received",
    # Tài sản cố định (25/11/2026; names from v4/financial_models, checked 25/11/2026): tangible, finance-lease, intangible fixed assets and
    # investment property (net, at cost, accumulated depreciation negative); construction in progress, 12460 from 2015 and 12300 before
    (1, 12210): "ppe_net", (1, 12220): "ppe_gross", (1, 12230): "ppe_depreciation", (1, 12240): "ppe_lease_net",
    (1, 12270): "intangible_net", (1, 12280): "intangible_gross", (1, 12290): "intangible_amortisation",
    (1, 12400): "property_net", (1, 12410): "property_gross", (1, 12420): "property_depreciation", (1, 12460): "cip", (1, 12300): "cip_old",
    # Chi phí trả trước (25/11/2026; names checked the same day): short and long-term prepaid expenses, and their change in operating cash flow
    (1, 11510): "prepaid_st", (1, 12610): "prepaid_lt", (3, 31160): "prepaid_change",
    # Lợi thế thương mại (25/11/2026; names checked the same day): goodwill, and its amortisation added back in operating cash flow
    (1, 12690): "goodwill", (3, 31111): "goodwill_amort",
    # Nợ vay (25/11/2026; names checked the same day): borrowings received, principal repaid (negative), unrealised exchange gains and losses
    (3, 33300): "borrow_in", (3, 33400): "borrow_out", (3, 31100): "fx_unrealised",
    # Vốn chủ sở hữu (25/11/2026; names checked the same day): share premium, treasury shares (negative), exchange differences, development fund,
    # retained earnings; cash from shares issued and paid to buy them back (negative)
    (1, 14120): "share_premium", (1, 14140): "treasury_shares", (1, 14160): "equity_fx", (1, 14170): "dev_fund", (1, 14200): "retained",
    (3, 33100): "issue_cash", (3, 33200): "buyback_cash",
    # Thuế TNDN (25/11/2026; names checked the same day): current and deferred tax expense, tax paid (negative), deferred tax assets and liabilities
    (2, 22051): "tax_current", (2, 22052): "tax_deferred", (3, 31180): "tax_paid", (1, 12620): "deferred_tax_assets", (1, 13350): "deferred_tax_liabilities",
    (3, 22230): "depreciation", (3, 32000): "cfo", (3, 32100): "capex", (3, 33000): "cfi", (3, 34000): "cff", (3, 33600): "dividends_paid",
}
# Banks (TT49 layout: models 101 balance sheet, 102 income statement) and securities firms (TT334: 89, 90): only what their scale
# and valuation block needs. Equity includes non-controlling interests in both, as in the general layout.
_FIN_COMMON = {"charter_capital": 14110, "equity": 14000, "minority_equity": 14240, "minority_equity_outside": 15000, "total_assets": 12700}
LAYOUTS = {
    None: {"models": "1,2,3", "lines": LINES},
    "bank": {"models": "101,102,103", "lines": {**{(101, c): k for k, c in _FIN_COMMON.items()}, (102, 421701): "operating_income",
                                                 (102, 88888): "ppop", (102, 23800): "pbt", (102, 23003): "npat", (102, 23000): "npat_parent",
                                                 (102, 23001): "eps",
                                                 # Chất lượng tài sản ngân hàng (23/11/2026; names from v4/financial_models, TT49): loans to
                                                 # customers before and their reserve (negative), accrued interest and fees, interest income,
                                                 # credit provision expense of the period
                                                 (101, 412100): "loans_gross", (101, 412200): "loan_reserve", (101, 412520): "accrued_interest",
                                                 (102, 421100): "interest_income", (102, 422900): "provision_expense"},
             # No bank has nothing lent, reserved or accrued: where the source gives 0 for these (quarters before it split them out), the
             # figure is missing, and the record says so. A period's provision expense can be nil, so it is kept.
             "zero_missing": frozenset({"loans_gross", "loan_reserve", "accrued_interest"})},
    "securities": {"models": "89,90,91", "lines": {**{(89, c): k for k, c in _FIN_COMMON.items()}, (89, 13110): "st_debt", (89, 13340): "lt_debt",
                                                   (90, 21000): "operating_revenue", (90, 23800): "pbt", (90, 23003): "npat", (90, 23000): "npat_parent",
                                                   (90, 23001): "eps"}},
    # Insurers (models 411, 412): the result of insurance itself and of investments, the parts that add up to profit before tax (from
    # mid-2014; the older layout's do not), the investment book. Both associates lines are kept apart: BVH still fills the old one.
    "insurance": {"models": "411,412,413", "lines": {**{(411, c): k for k, c in _FIN_COMMON.items()}, (411, 11100): "cash",
                                                     (411, 11200): "st_investments", (411, 12500): "lt_investments", (412, 21440): "net_premium",
                                                     (412, 23110): "ins_result", (412, 22175): "fin_profit", (412, 22174): "other_ops",
                                                     (412, 23900): "other_profit", (412, 23200): "associates_before", (412, 23300): "associates",
                                                     (412, 23800): "pbt", (412, 23003): "npat", (412, 23000): "npat_parent",
                                                     (412, 23001): "eps"}},
}
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _period(fiscal: str, kind: str) -> str:
    year, month = int(fiscal[:4]), int(fiscal[5:7])
    return str(year) if kind == "ANNUAL" else f"{year}-Q{(month + 2) // 3}"


def parse_statements(text: str, *, symbol: str, kind: str, lines: dict | None = None, zero_missing: frozenset = frozenset()) -> dict:
    """Periods of named lines; a line of `zero_missing` the source gives as 0 is left out and listed under "zeros"."""
    lines = LINES if lines is None else lines
    data = json.loads(text).get("data") or []
    if len(data) >= PAGE:
        raise ValueError("page full: the answer may be cut")
    seen: dict[tuple[str, str], set[Decimal]] = {}
    created: dict[str, str] = {}
    modified: dict[str, str] = {}
    for r in data:
        try:
            if r.get("code") != symbol or r.get("reportType") != kind:
                continue
            line = lines.get((int(r["modelType"]), int(r["itemCode"])))
            value = Decimal(str(r["numericValue"]))
            period = _period(str(r["fiscalDate"]), kind)
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        if line is None or not value.is_finite():
            continue
        seen.setdefault((period, line), set()).add(value)
        day = str(r.get("createdDate") or "")[:10]
        if day and (period not in created or day < created[period]):
            created[period] = day
        # the latest day the source updated any line of the period: VNDirect's year first carries the company's own Q4 figures and the
        # audited ones only later (owner, 23/11/2026)
        changed = str(r.get("modifiedDate") or "")[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", changed) and changed > modified.get(period, ""):
            modified[period] = changed
    periods: dict[str, dict[str, str]] = {}
    conflicts, zeros = [], []
    for (period, line), values in sorted(seen.items()):
        if line in zero_missing and values == {Decimal(0)}:
            zeros.append({"period": period, "line": line})
        elif len(values) > 1:
            conflicts.append({"period": period, "line": line, "values": [_plain(v) for v in sorted(values)]})
        else:
            periods.setdefault(period, {})[line] = _plain(next(iter(values)))
    for figures in periods.values():  # the pre-2015 layout's associates line, when the current one is absent
        old = figures.pop("associates_old", None)
        if old is not None and "associates" not in figures:
            figures["associates"] = old
    for period, figures in periods.items():  # construction in progress: the layout with a figure; two different figures are a conflict
        old_cip, cip = figures.pop("cip_old", None), figures.get("cip")
        if old_cip is None or Decimal(old_cip) == 0:
            continue
        if cip is None or Decimal(cip) == 0:
            figures["cip"] = old_cip
        elif Decimal(cip) != Decimal(old_cip):
            del figures["cip"]
            conflicts.append({"period": period, "line": "cip", "values": sorted([cip, old_cip], key=Decimal)})
    return {"periods": dict(sorted(periods.items())), "created": dict(sorted(created.items())), "conflicts": conflicts, "zeros": zeros,
            "modified": dict(sorted(modified.items()))}


def parse_year_end_closes(text: str, *, symbol: str) -> dict[str, dict[str, str]]:
    """The last unadjusted close of each year with its day (the current year's latest close until the year ends)."""
    return _period_end_closes(text, symbol=symbol, period=lambda day: day[:4])


def parse_quarter_end_closes(text: str, *, symbol: str) -> dict[str, dict[str, str]]:
    """The last unadjusted close of each quarter with its day (the current quarter's latest close until it ends)."""
    return _period_end_closes(text, symbol=symbol, period=lambda day: f"{day[:4]}-Q{(int(day[5:7]) - 1) // 3 + 1}")


def _period_end_closes(text: str, *, symbol: str, period: Callable[[str], str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for r in json.loads(text).get("data") or []:
        try:
            if r.get("code") != symbol or r.get("close") is None:
                continue
            day, close = str(r["date"])[:10], Decimal(str(r["close"]))
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        key = period(day)
        if close.is_finite() and close > 0 and (key not in out or day > out[key]["date"]):
            out[key] = {"date": day, "close": _plain(close)}
    return dict(sorted(out.items()))


class StatementStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol.upper()):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol.upper()}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(record["symbol"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def _merge(old: dict | None, key: str, new: dict) -> tuple[dict, dict, list, list, dict]:
    periods = {**(old or {}).get(key, {}), **new["periods"]}
    created = {**(old or {}).get(f"{key}_created", {}), **new["created"]}
    modified = dict(sorted({**(old or {}).get(f"{key}_modified", {}), **new.get("modified", {})}.items()))
    fresh = set(new["periods"]) | {c["period"] for c in new["conflicts"]} | {z["period"] for z in new["zeros"]}

    def kept(name: str) -> list:
        return sorted([c for c in (old or {}).get(f"{key}_{name}", []) if c["period"] not in fresh] + new[name], key=lambda c: (c["period"], c["line"]))
    return dict(sorted(periods.items())), dict(sorted(created.items())), kept("conflicts"), kept("zeros"), modified


def _lines_version(sector: str | None) -> int:
    return LINES_VERSION if kind_of(sector) is None else FIN_LINES_VERSION


def _old_lines(record: dict, sector: str | None) -> bool:
    """A ticker kept before its layout had its current lines."""
    return record.get("lines_version", 1) < _lines_version(sector)


# The first version of each layout with its present set of lines: a later version only re-reads the history (7: the update days), so a
# record from it can still be compared and its revisions logged (review 23/11/2026 (4))
SAME_LINES_SINCE = {None: 6}


def _same_lines(record: dict, sector: str | None) -> bool:
    kind = kind_of(sector)
    return record.get("lines_version", 1) >= SAME_LINES_SINCE.get(kind, _lines_version(sector))


def sync_statements(store: StatementStore, sectors: dict[str, str | None], *, get: Callable[[str], str], now: datetime, limit: int | None,
                    max_age_days: int = MAX_AGE_DAYS, sleep: Callable[[float], None] = time.sleep, kinds: tuple = (None,)) -> dict[str, str]:
    """Refresh the stalest watched tickers of `kinds` (None: non-financial; "bank", "securities"), never fetched first; one failing is
    reported and the others still update."""
    ages = []
    for symbol in sorted(s for s, sector in sectors.items() if kind_of(sector) in kinds):
        rec = store.read(symbol)
        fetched = datetime.fromisoformat(rec["fetched_at"]) if rec else None
        if fetched is None or (now - fetched).days >= max_age_days or "quarter_end_close" not in rec or _old_lines(rec, sectors[symbol]):
            ages.append((fetched is not None, fetched or now, symbol))  # also synced before quarter closes, or newer lines, were kept
    todo = [s for _, _, s in sorted(ages)]
    results = {}
    for i, symbol in enumerate(todo if limit is None else todo[:limit]):
        if i:
            sleep(PACE_SECONDS)
        old = store.read(symbol)
        start = FIRST_START if old is None or _old_lines(old, sectors[symbol]) else (now.date() - timedelta(days=REFRESH_DAYS)).isoformat()
        try:
            layout = LAYOUTS[kind_of(sectors[symbol])]
            parsed = {kind: parse_statements(_get_with_retry(get, URL.format(symbol=symbol, kind=kind, start=start, models=layout["models"], page=PAGE),
                                                             sleep), symbol=symbol, kind=kind, lines=layout["lines"],
                                         zero_missing=layout.get("zero_missing", frozenset()))
                      for kind in ("QUARTER", "ANNUAL")}
            if not parsed["QUARTER"]["periods"] and not parsed["ANNUAL"]["periods"] and old is None:
                results[symbol] = "error:no_observations"
                continue
            kept = old and old.get("year_end_close") and "quarter_end_close" in old
            price_start = start if kept else FIRST_START  # synced before the closes were kept: all of them
            prices = _get_with_retry(get, PRICE_URL.format(symbol=symbol, start=price_start), sleep)
            record = {"symbol": symbol, "fetched_at": now.isoformat(), "source": "vndirect:finfo", "lines_version": _lines_version(sectors[symbol]),
                      **({"kind": kind_of(sectors[symbol])} if kind_of(sectors[symbol]) else {})}
            for key, parse in (("year_end_close", parse_year_end_closes), ("quarter_end_close", parse_quarter_end_closes)):
                record[key] = dict(sorted({**(old or {}).get(key, {}), **parse(prices, symbol=symbol)}.items()))
            for kind, key in (("QUARTER", "quarters"), ("ANNUAL", "years")):
                if old is not None and _same_lines(old, sectors[symbol]):  # Số đã công bố bị sửa: logged before it is overwritten
                    from investment_agent.market.statement_revisions import find_revisions, record_revisions
                    record_revisions(store.root.parent, symbol, find_revisions(old.get(key, {}), parsed[kind]["periods"]), kind=key,
                                     seen_on=now.date())
                (record[key], record[f"{key}_created"], record[f"{key}_conflicts"], record[f"{key}_zeros"],
                 record[f"{key}_modified"]) = _merge(old, key, parsed[kind])
            store.save(record)
            results[symbol] = "ok"
        except Exception as exc:  # one ticker never stops the others
            results[symbol] = f"error:{type(exc).__name__}"
    return results
