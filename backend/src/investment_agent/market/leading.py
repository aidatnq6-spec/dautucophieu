"""Leading macro indicators: free official feeds where they exist, owner entries for the rest.

Automatic sources (checked 2026-10-25): FRED public CSV downloads (WTI, US CPI,
EFFR, US 10-year yield, broad dollar index), the Vietcombank exchange-rate XML,
two public Topi pages (free-market and SBV USD/VND, 12-month deposit rate;
robots.txt allows them and the terms do not forbid reading), and HOSE's statistics
service (net foreign trading and total HOSE trading value, per trading day). Topi values are
read from page text, so a layout change shows as a source error and the owner
may enter the value by hand. Everything else in the owner's sheet (M2, PMIs,
interbank rate, VN 10-year yield, foreign flows, VN-Index turnover) has no free
licensed feed and is entered by the owner with a source link. Values are stored as decimal strings under data/macro/; nothing is
estimated when a value is missing. This is a display dashboard: analysis
evidence keeps using the vintaged series in macro.py, which these values do
not feed.
"""

import html as html_lib
import json
import os
import re
import xml.etree.ElementTree as ET
import calendar
import time
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from investment_agent.domain.pinned import CONFIG_DIR

INDICATORS_PATH = CONFIG_DIR / "macro-indicators.json"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
VCB_XML = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
TOPI_PAGE = "https://online.topi.vn/market/{page}"
STOCKBIZ_PAGE = "https://stockbiz.vn/en/macro/data/{page}"
TE_PAGE = "https://tradingeconomics.com/{country}/manufacturing-pmi"
# ECB euro reference rates, last 90 days (public, robots.txt allows); DXY is computed from them with ICE's published formula.
ECB_90D = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
DXY_WEIGHTS = {"EUR": -0.576, "JPY": 0.136, "GBP": -0.119, "CAD": 0.091, "SEK": 0.042, "CHF": 0.036}
# HOSE's own statistics service behind hsx.vn (robots.txt allows all); one trading day per call, values in million đồng.
HOSE_FOREIGN = "https://api.hsx.vn/mk/api/v1/market/foreign-trading-value-report?fromDate={day}&toDate={day}"
HOSE_DAYS = 7
VN = timezone(timedelta(hours=7))
_ID = re.compile(r"^[a-z0-9_]{1,40}$")


class MacroError(ValueError):
    pass


# Seconds before the second and third try of a timeout, dropped connection, 429 or 5xx (stockbiz timed out
# one page at a time on 2026-10-29 and 2026-10-30); any other answer is final.
RETRY_DELAYS = (2, 5)


def _transient(exc: Exception) -> bool:
    import httpx
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def _get_with_retry(get: Callable[[str], str], url: str, sleep: Callable[[float], None]) -> str:
    for delay in (*RETRY_DELAYS, None):
        try:
            return get(url)
        except Exception as exc:
            if delay is None or not _transient(exc):
                raise
            sleep(delay)


def load_indicators(path: Path = INDICATORS_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["indicators"]


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def parse_fred_csv(text: str, *, transform: str | None = None) -> list[tuple[date, str]]:
    points = []
    for line in text.strip().splitlines()[1:]:
        day, _, raw = line.partition(",")
        try:
            points.append((date.fromisoformat(day.strip()), Decimal(raw.strip())))
        except (ValueError, InvalidOperation):
            continue  # FRED marks holidays with "."
    if transform == "yoy":
        by_month = {(d.year, d.month): v for d, v in points}
        return [(d, str(((v / by_month[(d.year - 1, d.month)] - 1) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)))
                for d, v in points if (d.year - 1, d.month) in by_month]
    return [(d, _plain(v)) for d, v in points]


def parse_vcb_xml(text: str, *, currency: str, field: str) -> tuple[date, str]:
    try:
        root = ET.fromstring(text)
        stamp = datetime.strptime(root.findtext("DateTime", "").strip(), "%m/%d/%Y %I:%M:%S %p").date()
        node = next(e for e in root.iter("Exrate") if e.get("CurrencyCode") == currency)
        return stamp, _plain(Decimal(node.get(field, "").replace(",", "")))
    except (ET.ParseError, ValueError, StopIteration, InvalidOperation) as exc:
        raise MacroError(f"vcb_unreadable:{type(exc).__name__}") from None


def _page_text(page: str) -> str:
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", page))).strip()


def parse_topi_fx(page: str, *, row: str) -> str:
    """Sell rate (đồng) of one row of Topi's USD/VND table, e.g. "Tự do" or "SBV"."""
    text = _page_text(page)
    head = text.find("Bán (USD/VND)")
    m = re.search(rf"(?<!\S){re.escape(row)} ([\d.]+) ([\d.]+)(?!\S)", text[head:]) if head >= 0 else None
    if m is None:
        raise MacroError("topi_fx_unreadable")
    return _plain(Decimal(m.group(2).replace(".", "")))


def parse_topi_rate(page: str, *, term: str, column: str) -> str:
    """Deposit rate (%/year) for one term and bank group of Topi's deposit table, columns read from its header."""
    text = _page_text(page)
    head = re.search(r"Kỳ hạn ((?:NHTM \D+?)+?) (?=\d+ tháng)", text)
    names = ["NHTM " + n.strip() for n in head.group(1).split("NHTM ") if n.strip()] if head else []
    if column not in names:
        raise MacroError("topi_rate_columns_changed")
    m = re.search(rf"(?<!\d){re.escape(term)} " + " ".join([r"([\d.,]+)%"] * len(names)), text)
    if m is None:
        raise MacroError("topi_rate_unreadable")
    return _plain(Decimal(m.group(names.index(column) + 1).replace(",", ".")))


def parse_stockbiz_series(page: str, *, monthly: bool = False, scale: str = "1") -> list[tuple[date, str]]:
    """Parse Stockbiz recent readings; monthly observations use the actual period end, never fetch day."""
    text = _page_text(page)
    pattern = r"(?<!\d)(\d{1,2})/(\d{4})\s*(?:\||Â·)?\s*([\d.,]+)" if monthly else r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})\s*(?:\||Â·)?\s*([\d.,]+)%?"
    points = {}
    for match in re.finditer(pattern, text):
        try:
            if monthly:
                month, year, raw = int(match[1]), int(match[2]), match[3]
                day = date(year, month, calendar.monthrange(year, month)[1])
            else:
                month, dom, year, raw = int(match[1]), int(match[2]), int(match[3]), match[4]
                day = date(year, month, dom)
            normalized = raw.replace(".", "").replace(",", ".") if monthly else raw.replace(",", "")
            points[day] = _plain(Decimal(normalized) * Decimal(scale))
        except (ValueError, InvalidOperation):
            continue
    if not points:
        raise MacroError("stockbiz_unreadable")
    return sorted(points.items())


def parse_te_pmi(page: str, *, year: int) -> list[tuple[date, str]]:
    text = _page_text(page)
    months = {name.lower(): n for n, name in enumerate(calendar.month_name) if name}
    matches = re.findall(r"Manufacturing PMI[^.]{0,180}?(?:to|at)\s+([\d.]+)\s+points?\s+in\s+([A-Za-z]+)", text, re.I)
    points = []
    for raw, name in matches:
        month = months.get(name.lower())
        if month:
            points.append((date(year, month, calendar.monthrange(year, month)[1]), _plain(Decimal(raw))))
    if not points:
        raise MacroError("pmi_unreadable")
    return sorted(set(points))


def parse_ecb_dxy(xml: str) -> list[tuple[date, str]]:
    """US Dollar Index from ECB reference rates (units per euro): ICE's formula
    50.14348112 × EURUSD^-0.576 × USDJPY^0.136 × GBPUSD^-0.119 × USDCAD^0.091 × USDSEK^0.042 × USDCHF^0.036.
    ICE's own DXY is proprietary; this tracks it closely (the ECB fixes at 14:15 CET, so values differ slightly)."""
    days = re.findall(r'<Cube time="(\d{4}-\d{2}-\d{2})">(.*?)</Cube>\s*(?=<Cube time|</Cube>)', xml, re.S)
    points = []
    for day, block in days:
        per_eur = {k: float(v) for k, v in re.findall(r'currency="([A-Z]{3})" rate="([\d.]+)"', block)}
        if not all(k in per_eur for k in ("USD", "JPY", "GBP", "CAD", "SEK", "CHF")):
            continue
        usd = per_eur["USD"]
        quotes = {"EUR": usd, "JPY": per_eur["JPY"] / usd, "GBP": usd / per_eur["GBP"], "CAD": per_eur["CAD"] / usd,
                  "SEK": per_eur["SEK"] / usd, "CHF": per_eur["CHF"] / usd}  # EURUSD, USDJPY, GBPUSD, USDCAD, USDSEK, USDCHF
        value = 50.14348112
        for ccy, weight in DXY_WEIGHTS.items():
            value *= quotes[ccy] ** weight
        points.append((date.fromisoformat(day), f"{value:.2f}"))
    if not points:
        raise MacroError("ecb_unreadable")
    return sorted(points)


_PMI_OTHER = re.compile(r"(?i)\b(mỹ|trung quốc|nhật bản|hàn quốc|châu âu|eurozone|asean|toàn cầu|đức|ấn độ|thái lan|indonesia)\b")


def parse_news_pmi(items: list[dict]) -> list[tuple[date, str]]:
    """S&P Global Vietnam Manufacturing PMI from news headlines (CafeF, Vietstock, Vneconomy RSS), e.g.
    "PMI ngành sản xuất Việt Nam tháng 9 đạt 51,9 điểm". The publisher's own pages block automated reading, so only
    headlines that name Việt Nam, the month and the value are used; anything vaguer is skipped. Dated to the month's end."""
    found: dict[date, str] = {}
    for it in sorted(items, key=lambda i: i["published"]):
        title = it["title"]
        if "PMI" not in title or not re.search(r"(?i)việt nam", title) or _PMI_OTHER.search(title):
            continue
        month_m = re.search(r"tháng\s*(\d{1,2})(?:\s*/\s*(\d{4}))?", title)
        value_m = re.search(r"(?<![\d,.])(\d{2})[,.](\d{1,2})(?![\d,.])", title[month_m.end():]) if month_m else None
        if not value_m:
            continue
        month, value = int(month_m.group(1)), Decimal(f"{value_m.group(1)}.{value_m.group(2)}")
        published = datetime.fromisoformat(it["published"]).astimezone(VN).date()
        year = int(month_m.group(2)) if month_m.group(2) else (published.year - 1 if month > published.month else published.year)
        if 1 <= month <= 12 and Decimal(30) <= value <= Decimal(70):
            found[date(year, month, calendar.monthrange(year, month)[1])] = _plain(value)
    return sorted(found.items())


_CPI_NAME = re.compile(r"(?i)\bCPI\b|chỉ số giá tiêu dùng")
_CPI_YOY = re.compile(r"(?i)(tăng|giảm)\s*(\d{1,2})(?:[,.](\d{1,2}))?\s*%\s*so với cùng kỳ")


def parse_news_cpi(items: list[dict]) -> list[tuple[date, str]]:
    """Vietnam's CPI, year on year, from news headlines (CafeF, Vietstock, Vneconomy RSS), e.g. "CPI tháng 10 tăng 0,2% so với tháng
    trước, tăng 3,2% so với cùng kỳ". Needs the month and a "% so với cùng kỳ" figure; averages ("bình quân") and other countries
    are skipped. Dated to the month's end, like PMI."""
    found: dict[date, str] = {}
    for it in sorted(items, key=lambda i: i["published"]):
        title = it["title"]
        if not _CPI_NAME.search(title) or _PMI_OTHER.search(title):
            continue
        month_m = re.search(r"tháng\s*(\d{1,2})(?:\s*/\s*(\d{4}))?", title)
        yoy = next((m for m in _CPI_YOY.finditer(title) if "bình quân" not in title[:m.start()].lower()), None) if month_m else None
        if not yoy or "bình quân" in title[:month_m.start()].lower():
            continue
        month = int(month_m.group(1))
        value = Decimal(f"{yoy.group(2)}.{yoy.group(3) or 0}") * (-1 if yoy.group(1).lower() == "giảm" else 1)
        published = datetime.fromisoformat(it["published"]).astimezone(VN).date()
        year = int(month_m.group(2)) if month_m.group(2) else (published.year - 1 if month > published.month else published.year)
        if 1 <= month <= 12 and Decimal(-10) <= value <= Decimal(30):
            found[date(year, month, calendar.monthrange(year, month)[1])] = _plain(value)
    return sorted(found.items())


def parse_hose_foreign(text: str) -> dict[str, str] | None:
    """Net foreign buy-sell and total HOSE trading value (incl. put-through) in billion đồng; None on a day without trading."""
    try:
        rows = json.loads(text)["data"]
    except (ValueError, KeyError, TypeError):
        raise MacroError("hose_unreadable") from None
    if not rows:
        return None
    by_type = {r.get("trading_type_name"): r for r in rows}
    try:
        net = Decimal(by_type["Mua - Bán"]["foreign_trading_value"].replace(",", ""))
        market = Decimal(by_type["Mua"]["market_value"].replace(",", ""))
    except (KeyError, AttributeError, InvalidOperation):
        raise MacroError("hose_layout_changed") from None
    return {"net": _plain(net / 1000), "market_value": _plain(market / 1000)}


def evaluate(rule: str, values: list[str]) -> tuple[str | None, str | None]:
    """(trend, assessment) from the last two values, oldest first, by the owner's rules."""
    latest = Decimal(values[-1]) if values else None
    trend = None
    if len(values) >= 2:
        prev = Decimal(values[-2])
        trend = "Tăng" if latest > prev else "Giảm" if latest < prev else "Đi ngang"
    if rule == "sign" and latest is not None:
        return trend, "Tốt" if latest > 0 else "Xấu" if latest < 0 else "Trung tính"
    if trend is None:
        return None, None
    if rule == "pmi":
        return trend, "Tốt" if latest > 50 and trend != "Giảm" else "Xấu"
    if trend == "Đi ngang":
        return trend, "Trung tính"
    worse = "Tăng" if rule == "up" else "Giảm"
    return trend, "Xấu" if trend == worse else "Tốt"


class MacroStore:
    """One JSON file per indicator under data/macro/, observations sorted by date, one per date."""

    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "macro"

    def _path(self, indicator: str) -> Path:
        if not _ID.fullmatch(indicator):
            raise MacroError("invalid_indicator")
        return self.root / f"{indicator}.json"

    def read(self, indicator: str) -> list[dict]:
        path = self._path(indicator)
        return json.loads(path.read_text(encoding="utf-8"))["observations"] if path.is_file() else []

    def upsert(self, indicator: str, points: list[tuple[date, str]], *, entry: str, source_url: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        by_date = {o["date"]: o for o in self.read(indicator)}
        for day, value in points:
            by_date[day.isoformat()] = {"date": day.isoformat(), "value": value, "entry": entry, "source_url": source_url, "recorded_at": now}
        self.root.mkdir(parents=True, exist_ok=True)
        path, tmp = self._path(indicator), self._path(indicator).with_suffix(".tmp")
        tmp.write_text(json.dumps({"indicator": indicator, "observations": [by_date[k] for k in sorted(by_date)]}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path)

    def statuses(self) -> dict[str, dict]:
        path = self.root / "_status.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def record_statuses(self, results: dict[str, str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        merged = {**self.statuses(), **{k: {"status": v, "at": now} for k, v in results.items()}}
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / "_status.tmp"
        tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.root / "_status.json")


def fetch_auto(indicators: list[dict], store: MacroStore, *, get: Callable[[str], str], today: date | None = None,
               sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Fetch every automatic indicator; one failing source never stops the others. Topi pages carry no
    publication date, so their values are dated on the fetch day (Vietnam time). A host still unreachable
    after its retries is not asked again this run; its other indicators report the same error."""
    today = today or datetime.now(VN).date()
    pages: dict[str, str] = {}
    down: dict[str, Exception] = {}

    def page(url):
        host = urlsplit(url).hostname
        if host in down:
            raise down[host]
        if url not in pages:
            try:
                pages[url] = _get_with_retry(get, url, sleep)
            except Exception as exc:
                if _transient(exc):
                    down[host] = exc
                raise
        return pages[url]
    results = {}
    for ind in indicators:
        src = ind["source"]
        try:
            if src["kind"] == "fred":
                points = parse_fred_csv(page(FRED_CSV.format(series=src["series"])), transform=src.get("transform"))
            elif src["kind"] == "vcb":
                points = [parse_vcb_xml(page(VCB_XML), currency=src["currency"], field=src["field"])]
            elif src["kind"] == "topi" and "row" in src:
                points = [(today, parse_topi_fx(page(TOPI_PAGE.format(page=src["page"])), row=src["row"]))]
            elif src["kind"] == "hose":
                days = [today - timedelta(days=i) for i in range(HOSE_DAYS - 1, -1, -1)]
                parsed = [(d, parse_hose_foreign(page(HOSE_FOREIGN.format(day=d.isoformat())))) for d in days]
                points = [(d, p[src["field"]]) for d, p in parsed if p is not None]
            elif src["kind"] == "topi":
                points = [(today, parse_topi_rate(page(TOPI_PAGE.format(page=src["page"])), term=src["term"], column=src["column"]))]
            elif src["kind"] == "stockbiz":
                points = parse_stockbiz_series(page(STOCKBIZ_PAGE.format(page=src["page"])), monthly=src.get("monthly", False), scale=src.get("scale", "1"))
            elif src["kind"] == "tradingeconomics_pmi":
                points = parse_te_pmi(page(TE_PAGE.format(country=src["country"])), year=today.year)
            elif src["kind"] == "ecb_dxy":
                points = parse_ecb_dxy(page(ECB_90D))
            elif src["kind"] in ("news_pmi", "news_cpi"):
                from investment_agent.brief.news import FEEDS, parse_rss
                items, failed = [], 0
                for source, url in FEEDS:  # page() caches by URL, so PMI and CPI share one read of each feed
                    try:
                        items += parse_rss(page(url), source)
                    except Exception:
                        failed += 1
                if failed == len(FEEDS):
                    raise MacroError("news_unreachable")
                points = (parse_news_pmi if src["kind"] == "news_pmi" else parse_news_cpi)(items)
                if not points:  # no such headline in today's feeds: nothing new, not a failure
                    results[ind["id"]] = "ok"
                    continue
            else:
                continue
            if not points:
                raise MacroError("no_observations")
            store.upsert(ind["id"], points[-400:], entry="auto")
            results[ind["id"]] = "ok"
        except Exception as exc:  # network, parse or source change: reported per indicator
            results[ind["id"]] = f"error:{type(exc).__name__}"
    store.record_statuses(results)
    return results


# Long daily history for Độ nhạy với giá dầu và đồng USD (not shown in the macro table): WTI and the Fed's broad US dollar index.
FACTORS = {"factor_oil": "DCOILWTICO", "factor_usd": "DTWEXBGS"}
FACTOR_YEARS = 5


def fetch_factors(store: MacroStore, *, get: Callable[[str], str], today: date | None = None,
                  sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Five years of each factor from FRED's public CSV; a failing series is reported and the other still updates."""
    today = today or datetime.now(VN).date()
    start = today.replace(year=today.year - FACTOR_YEARS, day=min(today.day, 28) if today.month == 2 else today.day)
    results = {}
    for key, series in FACTORS.items():
        try:
            points = parse_fred_csv(_get_with_retry(get, FRED_CSV.format(series=series) + f"&cosd={start.isoformat()}", sleep))
            if not points:
                raise MacroError("no_observations")
            store.upsert(key, points, entry="auto")
            results[key] = "ok"
        except Exception as exc:
            results[key] = f"error:{type(exc).__name__}"
    return results


# Monthly world prices (IMF Primary Commodity Prices on FRED, checked 2026-10-30) for Chuỗi giá trị's input and output costs;
# kept under data/macro/ but outside macro-indicators.json, so they never show on Vĩ mô. FRED has no urea series.
COMMODITIES = {"com_coal": "PCOALAUUSDM", "com_iron_ore": "PIORECRUSDM", "com_rubber": "PRUBBUSDM", "com_sugar": "PSUGAISAUSDM",
               "com_shrimp": "PSHRIUSDM", "com_lng": "PNGASJPUSDM", "com_aluminium": "PALUMUSDM", "com_copper": "PCOPPUSDM",
               "com_wheat": "PWHEAMTUSDM", "com_soybean": "PSOYBUSDM"}
COMMODITY_YEARS = 3


def fetch_commodities(store: MacroStore, *, get: Callable[[str], str], today: date | None = None,
                      sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Three years of each monthly commodity price; a failing series is reported and the others still update."""
    today = today or datetime.now(VN).date()
    start = today.replace(year=today.year - COMMODITY_YEARS, day=min(today.day, 28) if today.month == 2 else today.day)
    results = {}
    for key, series in COMMODITIES.items():
        try:
            points = parse_fred_csv(_get_with_retry(get, FRED_CSV.format(series=series) + f"&cosd={start.isoformat()}", sleep))
            if not points:
                raise MacroError("no_observations")
            store.upsert(key, points, entry="auto")
            results[key] = "ok"
        except Exception as exc:
            results[key] = f"error:{type(exc).__name__}"
    return results


def macro_reminders(indicators: list[dict], store: MacroStore, *, today: date) -> list[str]:
    """Indicators the owner can enter by hand that have no value yet or are older than their update rhythm (max_age_days)."""
    out = []
    for r in macro_rows(indicators, store, today=today):
        if not r["manual_allowed"]:
            continue
        if r["value"] is None:
            out.append(f"{r['label']} chưa có số liệu")
        elif r["stale"]:
            out.append(f"{r['label']} đã {(today - date.fromisoformat(r['date'])).days} ngày chưa cập nhật")
    return out


def macro_rows(indicators: list[dict], store: MacroStore, *, today: date) -> list[dict]:
    rows, statuses = [], store.statuses()
    for ind in indicators:
        obs = store.read(ind["id"])
        status = statuses.get(ind["id"], {}).get("status")
        last = obs[-1] if obs else None
        trend, assessment = evaluate(ind["rule"], [o["value"] for o in obs[-2:]])
        rows.append({"id": ind["id"], "label": ind["label"], "unit": ind["unit"], "auto": ind["source"]["kind"] != "manual",
                     "value": last["value"] if last else None, "date": last["date"] if last else None,
                     "previous": obs[-2]["value"] if len(obs) >= 2 else None, "trend": trend, "assessment": assessment,
                     "stale": last is not None and (today - date.fromisoformat(last["date"])).days > ind["max_age_days"],
                     "source_url": (last or {}).get("source_url") or ind["url"], "note": ind.get("note"),
                     "source_error": status if status not in (None, "ok") else None,
                     "manual_allowed": ind["source"]["kind"] == "manual" or bool(ind["source"].get("manual_fallback"))})
    return rows
