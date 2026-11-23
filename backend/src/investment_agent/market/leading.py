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
import html
import json
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
import io
import calendar
import csv
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
# Earlier sources (robots.txt allows each): WTI front-month futures 10 minutes late; the State Bank's own interbank rates, out about 05:30
# the next morning; the US Treasury's daily yield curve, out the same US afternoon. Each keeps its older source as a fallback.
OILPRICE_PAGE = "https://oilprice.com/oil-price-charts/"
# gold-api.com: the live price endpoint is free, without a key or a rate limit (terms of 10/09/2026; no robots.txt); its history needs a
# paid key, so the app keeps its own daily series from the live price.
GOLD_API = "https://api.gold-api.com/price/XAU"
# Bộ Công Thương's own releases on each fuel price period (robots.txt allows; checked 16/11/2026). Not every period gets a release
# on these pages: the missing ones are entered by hand. Petrolimex's price service is closed to robots (robots.txt: Disallow /).
MOIT = "https://moit.gov.vn"
MOIT_PAGES = (MOIT + "/", MOIT + "/quan-ly-thi-truong")
MOIT_PER_RUN = 3
SJC_KIND = "Vàng miếng SJC"
SBV_INTERBANK = "https://sbv.gov.vn/o/headless-delivery/v1.0/content-structures/3450260/structured-contents?pageSize=30&sort=datePublished:desc"
TREASURY_CSV = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
                "?type={curve}&field_tdr_date_value={year}&page&_format=csv")
# the nominal par yield curve, and the real (TIPS) one for the US real yield (robots.txt allows all; checked 20/11/2026)
TREASURY_CURVES = {"nominal": "daily_treasury_yield_curve", "real": "daily_treasury_real_yield_curve"}
# ECB euro reference rates, last 90 days (public, robots.txt allows); DXY is computed from them with ICE's published formula.
ECB_90D = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
# Cục Thống kê's own site (WordPress): its public posts API, category 94 (Dữ liệu và số liệu thống kê); robots.txt disallows only
# /wp-admin/ (checked 14/11/2026). The monthly CPI post opens with the month's year-on-year figure.
NSO_CPI = ("https://www.nso.gov.vn/wp-json/wp/v2/posts?categories=94&search=Ch%E1%BB%89%20s%E1%BB%91%20gi%C3%A1%20ti%C3%AAu%20d%C3%B9ng"
           "&per_page=20&_fields=date,title,content")
# The State Bank's pages (robots.txt allows all, checked 15/11/2026): the day's central rate is in the page itself; /vi/ answers without
# a redirect. Cục Thống kê's monthly socio-economic report (category 78) gives the trade balance and disbursed FDI.
SBV_CENTRAL = "https://sbv.gov.vn/vi/t%E1%BB%B7-gi%C3%A1"
# NHNN's Tổng phương tiện thanh toán và tiền gửi của khách hàng tại TCTD (readable again on 16/11/2026): only the latest month is shown,
# so the history builds up from each run (stockbiz stays the fallback)
SBV_M2 = ("https://sbv.gov.vn/vi/t%E1%BB%95ng-ph%C6%B0%C6%A1ng-ti%E1%BB%87n-thanh-to%C3%A1n-v%C3%A0-ti%E1%BB%81n-g%E1%BB%ADi-c%E1%BB%A7a-"
          "kh%C3%A1ch-h%C3%A0ng-t%E1%BA%A1i-tctd")
# CafeF's PMI topic page (robots.txt allows all, checked 15/11/2026): each month's article on S&P Global's Vietnam PMI opens with the
# figure ("PMI ngành sản xuất Việt Nam đạt 52,3 điểm trong tháng 10/2026"); only months not stored yet are opened, three per run.
CAFEF_PMI = "https://cafef.vn/pmi.html"
CAFEF_BASE = "https://cafef.vn"
CAFEF_PMI_PER_RUN = 3
# An indicator whose stored history is shorter than this takes FRED's series once ("history" in its source), e.g. Brent.
HISTORY_MIN_POINTS, HISTORY_YEARS = 60, 2
NSO_REPORT = "https://www.nso.gov.vn/wp-json/wp/v2/posts?categories=78&per_page=24&_fields=date,title,content"
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


def error_name(exc: Exception) -> str:
    """The error as a run reports it: a server's 429 or 5xx is "ServerError" (asked again after the pause, 21/11/2026), any other
    answer keeps its type name (a 404 stays "HTTPStatusError", final)."""
    import httpx
    if isinstance(exc, httpx.HTTPStatusError) and _transient(exc):
        return "ServerError"
    return type(exc).__name__


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


def fred_yoy_gap(text: str) -> dict | None:
    """The newest month the source has a figure for but whose year-ago figure is blank, so its change on a year cannot be worked out
    (the US did not publish October 2025's CPI). None when the newest month has its change. Never filled in (owner, 21/11/2026)."""
    raw, yoy = parse_fred_csv(text), parse_fred_csv(text, transform="yoy")
    if not raw or (yoy and yoy[-1][0] >= raw[-1][0]):
        return None
    month = raw[-1][0]
    return {"month": f"{month.year}-{month.month:02d}", "base": f"{month.year - 1}-{month.month:02d}"}


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


def _grouped(raw: str) -> str:
    """A number whose separators all group thousands ("20,775", "20.456", "1,234,567") loses them; otherwise a comma is the decimal point."""
    raw = raw.strip(".,")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", raw):
        return re.sub(r"[.,]", "", raw)
    return raw.replace(".", "").replace(",", ".") if raw.count(",") == 1 else raw


def moit_release_links(page: str) -> list[str]:
    """Links to Bộ Công Thương's fuel price releases ("…điều hành giá xăng dầu…"), newest first as the page lists them."""
    out = []
    # the ministry's slugs vary: "dieu-hang" (a typo, 19/11/2026) and "dieu-hanh-gia-ban" (its letter of the period)
    for href in re.findall(r'href="([^"]*dieu-han[hg]-gia(?:-ban)?-xang-dau[^"]*\.html)"', page):
        url = href if href.startswith("http") else MOIT + href
        if url not in out:
            out.append(url)
    return out


_MOIT_ITEMS = {"e5ron92": r"Xăng E5\s*RON\s*92(?:-II)?", "ron95": r"Xăng E10\s*RON\s*95-III", "diesel": r"Dầu điêzen 0[.,]05S"}


def parse_moit_fuel(page: str) -> dict:
    """The ceilings of one period (section 3.2, "không cao hơn … đồng/lít") and the day it applies from (section 4)."""
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    out = {}
    for key, name in _MOIT_ITEMS.items():
        m = re.search(name + r"\s*:\s*không cao hơn ([\d.]+) đồng/lít", text)
        if m:
            out[key] = m.group(1).replace(".", "")
    when = re.search(r"Thời gian thực hiện.*?ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})", text)
    if not out.get("ron95") or not when:
        raise MacroError("moit_fuel_unreadable")
    return {"date": date(int(when.group(3)), int(when.group(2)), int(when.group(1))), **out}


def parse_gold_api(text: str) -> list[tuple[date, str]]:
    """XAU/USD from gold-api.com, dated on the Vietnam day it was taken."""
    from zoneinfo import ZoneInfo
    try:
        data = json.loads(text)
        if data.get("symbol") != "XAU" or data.get("currency", "USD") != "USD":
            raise ValueError("not XAU/USD")
        price = Decimal(str(data["price"]))
        at = datetime.fromisoformat(str(data["updatedAt"]).replace("Z", "+00:00"))
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        raise MacroError("gold_api_unreadable") from exc
    if price <= 0:
        raise MacroError("gold_api_unreadable")
    return [(at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date(), str(price.quantize(Decimal("0.01"), ROUND_HALF_UP)))]


def parse_oilprice(page: str, *, blend: str) -> list[tuple[date, str]]:
    """oilprice.com's price table: the blend's last price, dated on New York time when it was taken (10 minutes late)."""
    from zoneinfo import ZoneInfo
    row = re.search(r"<tr[^>]*data-name=['\"]" + re.escape(blend) + r"['\"][^>]*>(.*?)</tr>", page, re.S)
    price = re.search(r"data-price=['\"]([\d.]+)['\"]", row[1]) if row else None
    stamp = re.search(r"data-stamp=['\"](\d{9,11})['\"]", row[1]) if row else None
    if not price or not stamp:
        raise MacroError("oilprice_unreadable")
    day = datetime.fromtimestamp(int(stamp[1]), timezone.utc).astimezone(ZoneInfo("America/New_York")).date()
    return [(day, _plain(Decimal(price[1])))]


def parse_sbv_interbank(text: str, *, term: str) -> list[tuple[date, str]]:
    """The State Bank's average interbank rates (% a year) for one term ("Qua đêm", "1 Tuần", ...), by the Vietnam day they apply to."""
    points = {}
    for item in json.loads(text).get("items", []):
        fields = item.get("contentFields", [])
        applied = next((f.get("contentFieldValue", {}).get("data") for f in fields if f.get("label") == "Ngày áp dụng"), None)
        if not applied:
            continue
        day = datetime.fromisoformat(applied.replace("Z", "+00:00")).astimezone(VN).date()
        for f in fields:
            kids = {c.get("label"): c.get("contentFieldValue", {}).get("data") for c in f.get("nestedContentFields", [])}
            rate = kids.get("Lãi suất BQ liên Ngân hàng (% năm)")
            if kids.get("Thời hạn") == term and rate:
                try:
                    points[day] = _plain(Decimal(str(rate).replace(",", ".")))
                except InvalidOperation:
                    continue
    if not points:
        raise MacroError("sbv_unreadable")
    return sorted(points.items())


def parse_treasury_csv(text: str, *, column: str) -> list[tuple[date, str]]:
    """The US Treasury's daily par yield curve CSV: one column (e.g. "10 Yr"), days without a value left out."""
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or column not in rows[0]:
        raise MacroError("treasury_unreadable")
    points = []
    for r in rows:
        try:
            points.append((datetime.strptime(r["Date"], "%m/%d/%Y").date(), _plain(Decimal(r[column]))))
        except (ValueError, InvalidOperation, KeyError):
            continue
    if not points:
        raise MacroError("treasury_unreadable")
    return sorted(points)


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
            normalized = _grouped(raw) if monthly else raw.replace(",", "")
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


_PMI_LINK = re.compile(r'<a[^>]+href="(/[^"]+?\.chn)"[^>]*title="([^"]+)"')
_PMI_LEAD = re.compile(r"(?i)PMI\)?[^.]{0,160}?(\d{2})[,.](\d{1,2})\s*điểm\s*(?:trong|của)?\s*tháng\s*(\d{1,2})")


def parse_cafef_pmi_links(page: str) -> list[tuple[int, int | None, str]]:
    """(month, year or None, article path) of each Vietnam manufacturing PMI article on CafeF's topic page, newest first."""
    out, seen = [], set()
    for path, raw in _PMI_LINK.findall(page):
        title = html_lib.unescape(raw)
        if "PMI" not in title or not re.search(r"(?i)việt nam", title) or _PMI_OTHER.search(title) or path in seen:
            continue
        m = re.search(r"tháng\s*(\d{1,2})(?:\s*/\s*(\d{4}))?", title)
        if m and 1 <= int(m.group(1)) <= 12:
            month, year = int(m.group(1)), int(m.group(2)) if m.group(2) else None
            published = re.search(r"-188(\d{2})(\d{2})(\d{2})\d{6,}\.chn$", path)  # CafeF's article number: 188, then yymmdd
            if year is None and published and 1 <= int(published.group(2)) <= 12:
                year = 2000 + int(published.group(1)) - (1 if month > int(published.group(2)) else 0)
            seen.add(path)
            out.append((month, year, path))
    if not out:
        raise MacroError("cafef_pmi_unreadable")
    return out


def parse_cafef_pmi_article(page: str, *, month: int, year: int | None) -> tuple[date, str] | None:
    """The month's figure from the article's first sentence naming it; the month in that sentence must be the title's. Without a
    year in the title, the year is the one published in (the year before for a December figure read in January)."""
    body = _text(re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", page))
    for m in _PMI_LEAD.finditer(body):
        if int(m.group(3)) != month:
            continue
        value = Decimal(f"{m.group(1)}.{m.group(2)}")
        if not Decimal(30) <= value <= Decimal(70):
            return None
        if year is None:
            pub = re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{2})', page)
            if not pub:
                return None
            year = int(pub.group(1)) - (1 if month > int(pub.group(2)) else 0)
        return date(year, month, calendar.monthrange(year, month)[1]), _plain(value)
    return None


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


_VN_MONTHS = {"mười một": 11, "mười hai": 12, "một": 1, "giêng": 1, "hai": 2, "ba": 3, "tư": 4, "bốn": 4, "năm": 5, "sáu": 6, "bảy": 7,
              "tám": 8, "chín": 9, "mười": 10}
_NSO_MONTH = re.compile(r"(?i)tháng\s+(mười một|mười hai|giêng|một|hai|ba|tư|bốn|năm|sáu|bảy|tám|chín|mười|\d{1,2})\b")
_NSO_YOY = re.compile(r"(?i)(tăng|giảm)\s*(\d{1,2})(?:,(\d{1,2}))?\s*%\s*so với cùng kỳ năm trước")


def parse_nso_cpi(text: str) -> list[tuple[date, str]]:
    """Vietnam's CPI, year on year, from Cục Thống kê's monthly post "Chỉ số giá tiêu dùng … tháng Mười … năm 2026": the first
    "% so với cùng kỳ năm trước" before any average ("bình quân", "tính chung"). Other posts (the monthly overview, the price press
    release) are skipped: only a title that starts with "Chỉ số giá tiêu dùng". Dated to the month's end."""
    found: dict[date, str] = {}
    for post in json.loads(text):
        title = html_lib.unescape(re.sub(r"<[^>]+>", " ", (post.get("title") or {}).get("rendered") or "")).strip()
        if not title.lower().startswith("chỉ số giá tiêu dùng"):
            continue
        month_m, year_m = _NSO_MONTH.search(title), re.search(r"năm\s+(\d{4})", title)
        if not month_m or not year_m:
            continue
        word = month_m.group(1).lower()
        month, year = int(word) if word.isdigit() else _VN_MONTHS[word], int(year_m.group(1))
        body = re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", (post.get("content") or {}).get("rendered") or "")))
        cut = min([i for i in (body.lower().find("bình quân"), body.lower().find("tính chung")) if i >= 0] or [len(body)])
        yoy = _NSO_YOY.search(body[:cut])
        if not yoy or not 1 <= month <= 12:
            continue
        value = Decimal(f"{yoy.group(2)}.{yoy.group(3) or 0}") * (-1 if yoy.group(1).lower() == "giảm" else 1)
        if Decimal(-10) <= value <= Decimal(30):
            found[date(year, month, calendar.monthrange(year, month)[1])] = _plain(value)
    return sorted(found.items())


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment or "")))


def _vn_number(raw: str) -> Decimal:
    """ "1.012,07" → 1012.07; ",00" → 0."""
    return Decimal(raw.replace(".", "").replace(",", ".").rstrip(".") or "0")


_CENTRAL = re.compile(r"(?is)áp dụng cho ngày\s+(\d{1,2})/(\d{1,2})/(\d{4}).{0,400}?1\s+Đô la Mỹ\s*=\s*([\d.]+)\s*VND")


_SBV_M2 = re.compile(r"(?is)THÁNG\s+(\d{1,2})\s+NĂM\s+(\d{4}).{0,600}?Tổng phương tiện thanh toán\s*\(\*\)\s*([\d.]+)")


def parse_sbv_m2(page: str) -> list[tuple[date, str]]:
    """The latest month's money supply (tỷ đồng) from NHNN's statistics page, dated to the month's end."""
    m = _SBV_M2.search(unicodedata.normalize("NFC", _text(page)))
    if not m:
        raise MacroError("sbv_m2_unreadable")
    y, mo, value = int(m.group(2)), int(m.group(1)), int(m.group(3).replace(".", ""))
    if not 1 <= mo <= 12 or not 1_000_000 <= value <= 1_000_000_000:
        raise MacroError("sbv_m2_out_of_range")
    return [(date(y, mo, calendar.monthrange(y, mo)[1]), str(value))]


# Tỷ giá trung tâm đầu năm: NHNN's page shows only the latest day, so the first week of a year is read once from the daily central-rate
# article of Thị trường Tài chính Tiền tệ (the banking association's paper; robots.txt allows all but /search), found through its daily
# sitemaps (checked 16/11/2026). One point on or before 7 January is all Thanh khoản và tỷ giá needs for the change since January.
TTT_SITEMAP = "https://thitruongtaichinhtiente.vn/sitemap-article-{day}.xml"
_TTT_CENTRAL = re.compile(r"(?is)ngày\s+(\d{1,2})/(\d{1,2}),\s*tỷ giá trung tâm.{0,250}?ở mức\s+([\d.]+)\s*(?:đồng|VND)")


def parse_ttt_sitemap(xml: str) -> list[str]:
    return [u for u in re.findall(r"<loc>([^<]+)</loc>", xml) if "ty-gia-trung-tam" in u]


def parse_ttt_central(page: str) -> tuple[date, str] | None:
    """The day's central rate from the article's own opening sentence ("Sáng ngày 6/1, tỷ giá trung tâm … ở mức 25.122 đồng")."""
    m = _TTT_CENTRAL.search(unicodedata.normalize("NFC", _text(re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", page))))
    pub = re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{2})', page)
    if not m or not pub:
        return None
    day, month, value = int(m.group(1)), int(m.group(2)), int(m.group(3).replace(".", ""))
    year = int(pub.group(1)) - (1 if month > int(pub.group(2)) else 0)
    if not 15_000 <= value <= 40_000:
        return None
    try:
        return date(year, month, day), str(value)
    except ValueError:
        return None


def fetch_central_baseline(store: "MacroStore", data_dir: Path, *, get: Callable[[str], str], today: date) -> str:
    """"ok" when a central rate of 1–7 January of this year is stored (looked up once if needed), "waiting" before 8 January,
    "not_found" when the first week had no article (that year is not searched again)."""
    year = today.year
    if any(date(year, 1, 1).isoformat() <= o["date"] <= date(year, 1, 7).isoformat() for o in store.read("usd_vnd_central")):
        return "ok"
    if today < date(year, 1, 8):
        return "waiting"
    marker = Path(data_dir) / "macro" / "_central_baseline.json"
    tried = json.loads(marker.read_text(encoding="utf-8")).get("not_found", []) if marker.is_file() else []
    if year in tried:
        return "not_found"
    for d in range(1, 8):
        for url in parse_ttt_sitemap(get(TTT_SITEMAP.format(day=date(year, 1, d).isoformat()))):
            found = parse_ttt_central(get(url))
            if found and found[0].year == year and found[0].month == 1 and found[0].day <= 7:
                store.upsert("usd_vnd_central", [found], entry="auto", source_url=url)
                return "ok"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"not_found": sorted({*tried, year})}), encoding="utf-8")
    return "not_found"


def parse_sbv_central(page: str) -> list[tuple[date, str]]:
    """The State Bank's central USD/VND rate, dated on the day it applies to (published the evening before, weekends included)."""
    m = _CENTRAL.search(_text(page))
    if not m:
        raise MacroError("sbv_central_unreadable")
    value = int(m.group(4).replace(".", ""))
    if not 10_000 <= value <= 100_000:
        raise MacroError("sbv_central_out_of_range")
    return [(date(int(m.group(3)), int(m.group(2)), int(m.group(1))), str(value))]


_QUARTER_END = {"i": 3, "ii": 6, "iii": 9, "iv": 12}
_TRADE_MONTH = re.compile(r"(?i)cán cân thương mại hàng hóa tháng [^,.;]{1,30}?(xuất|nhập) siêu ([\d.,]+) tỷ USD")
_TRADE_YTD = re.compile(r"(?i)cán cân thương mại hàng hóa (?!tháng)[^,.;]{0,40}?(xuất|nhập) siêu ([\d.,]+) tỷ USD")
_AMOUNT = r"(?:gần |khoảng |hơn )?[\d.,]+ nghìn tỷ đồng"
_RETAIL = re.compile(r"(?i)tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng [^,;.]{1,30}?ước đạt " + _AMOUNT
                     + r", (?:(?:tăng|giảm) [\d.,]+% so với tháng trước và )?(tăng|giảm) ([\d.,]+)% so với cùng kỳ năm trước")
# since January: the sentence that gives the share of the year's plan (January's own sentence is the year to date)
_PUBLIC_INVEST = re.compile(r"(?i)vốn đầu tư thực hiện từ nguồn ngân sách nhà nước (?:tháng [^,;.]{1,12}? )?ước đạt " + _AMOUNT
                            + r", bằng [\d.,]+% kế hoạch năm và (tăng|giảm) ([\d.,]+)% so với cùng kỳ năm trước")
_FDI = re.compile(r"(?i)vốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam [^.;]{0,80}?đạt ([\d.,]+) tỷ USD, (tăng|giảm) ([\d.,]+)%")


def _report_month(title: str) -> date | None:
    year = re.search(r"năm\s+(\d{4})", title)
    quarter = re.search(r"(?i)quý\s+(IV|III|II|I)\b", title)
    if quarter:
        month = _QUARTER_END[quarter.group(1).lower()]
    else:
        m = _NSO_MONTH.search(title)
        if not m:
            return None
        word = m.group(1).lower()
        month = int(word) if word.isdigit() else _VN_MONTHS[word]
    if not year or not 1 <= month <= 12:
        return None
    y = int(year.group(1))
    return date(y, month, calendar.monthrange(y, month)[1])


def parse_nso_report(text: str, *, field: str) -> list[tuple[date, str]]:
    """From each "Báo cáo tình hình kinh tế – xã hội …" post (the press releases repeat it): the month's goods trade balance, the balance
    since January, disbursed FDI since January (bn USD) or its change on a year before (%), the month's retail sales against a year
    before (%), or budget-funded investment since January against a year before (%); dated to the month's end. A deficit is
    negative. A report without the sentence gives nothing for that month (quarter reports give no budget investment figure)."""
    found: dict[date, str] = {}
    for post in json.loads(text):
        # some reports type accents as separate marks ("tháng"): compose them first so the sentences match
        nfc = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731
        title = nfc(_text((post.get("title") or {}).get("rendered") or "")).strip()
        if not title.lower().startswith("báo cáo tình hình kinh tế"):
            continue
        month = _report_month(title)
        if month is None:
            continue
        body = nfc(_text((post.get("content") or {}).get("rendered") or ""))
        value = None
        if field in ("retail_yoy", "public_invest_yoy"):
            m = (_RETAIL if field == "retail_yoy" else _PUBLIC_INVEST).search(body)
            if m:
                value = _vn_number(m.group(2)) * (-1 if m.group(1).lower() == "giảm" else 1)
        elif field in ("trade_month", "trade_ytd"):
            m = (_TRADE_MONTH if field == "trade_month" else _TRADE_YTD).search(body)
            if m:
                value = _vn_number(m.group(2)) * (-1 if m.group(1).lower() == "nhập" else 1)
        else:
            m = _FDI.search(body)
            if m:
                value = _vn_number(m.group(1)) if field == "fdi_ytd" else _vn_number(m.group(3)) * (-1 if m.group(2).lower() == "giảm" else 1)
        if value is not None:
            found.setdefault(month, _plain(value))  # newest post first: a later revision of the same month wins
    if not found:
        raise MacroError("nso_report_unreadable")
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
    if rule == "none":
        return trend, None
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

    def upsert(self, indicator: str, points: list[tuple[date, str]], *, entry: str, source_url: str | None = None, replace: bool = False) -> None:
        """Adds or overwrites the points by date; with replace, the stored points are dropped first (a series moved to a source in other units)."""
        now = datetime.now(timezone.utc).isoformat()
        before = {o["date"]: o for o in self.read(indicator)}
        by_date = {} if replace else dict(before)
        for day, value in points:
            key = day.isoformat()
            # first_seen: when this date first came in, kept through later runs and revisions, so a source's real delay can be read
            # (owner, 22/11/2026); a figure stored before then has none: unknown, never filled in
            seen = before[key].get("first_seen") if key in before else now
            by_date[key] = {"date": key, "value": value, "entry": entry, "source_url": source_url, "recorded_at": now,
                            **({"first_seen": seen} if seen else {})}
        self.root.mkdir(parents=True, exist_ok=True)
        path, tmp = self._path(indicator), self._path(indicator).with_suffix(".tmp")
        tmp.write_text(json.dumps({"indicator": indicator, "observations": [by_date[k] for k in sorted(by_date)]}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path)

    def statuses(self) -> dict[str, dict]:
        path = self.root / "_status.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def gaps(self) -> dict[str, dict]:
        """Per indicator, the newest month the source could not give a change for (fred_yoy_gap)."""
        path = self.root / "_gaps.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def record_gaps(self, gaps: dict[str, dict | None]) -> None:
        merged = {k: v for k, v in {**self.gaps(), **gaps}.items() if v is not None}
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / "_gaps.tmp"
        tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.root / "_gaps.json")

    def record_statuses(self, results: dict[str, str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        merged = {**self.statuses(), **{k: {"status": v, "at": now} for k, v in results.items()}}
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / "_status.tmp"
        tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.root / "_status.json")


MAX_PARALLEL_SOURCES = 6
# Source kinds that read the same host share a group, so that host is asked one request at a time.
SOURCE_GROUPS = {"sbv_interbank": "sbv", "sbv_central": "sbv", "sbv_m2": "sbv", "nso_report": "nso", "nso_cpi": "nso",
                 "gold_api": "gold_vcb", "sjc_gap": "gold_vcb", "vcb": "gold_vcb"}
LAST = {"real_rate"}  # reads series fetched earlier in the same run


def source_group(indicator: dict) -> str | None:
    """The group an indicator is read in (its source's host); None for one read after every group has finished."""
    kind = indicator["source"]["kind"]
    return None if kind in LAST else SOURCE_GROUPS.get(kind, kind)


def fetch_auto(indicators: list[dict], store: MacroStore, *, get: Callable[[str], str], today: date | None = None,
               sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Fetch every automatic indicator; one failing source never stops the others. Topi pages carry no
    publication date, so their values are dated on the fetch day (Vietnam time). A host still unreachable
    after its retries is not asked again this run; its other indicators report the same error."""
    today = today or datetime.now(VN).date()
    pages: dict[str, str] = {}
    down: dict[str, Exception] = {}
    specs = {**{i["id"]: i for i in load_indicators()}, **{i["id"]: i for i in indicators}}

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
    def read(src: dict, known: set[str]):
        """The source's points; None when it has nothing new today (not a failure), False for a manual source; raises when it fails."""
        if src["kind"] == "cafef_pmi":
            due = [(m, y, p) for m, y, p in parse_cafef_pmi_links(page(CAFEF_PMI))
                   if not (y and date(y, m, calendar.monthrange(y, m)[1]).isoformat() in known)][:CAFEF_PMI_PER_RUN]
            found = [parse_cafef_pmi_article(page(CAFEF_BASE + p), month=m, year=y) for m, y, p in due]
            points = sorted({d: v for d, v in (f for f in found if f) if d.isoformat() not in known}.items())
            return points or None
        if src["kind"] == "oilprice":
            points = parse_oilprice(page(OILPRICE_PAGE), blend=src["blend"])
        elif src["kind"] == "gold_api":
            points = parse_gold_api(page(GOLD_API))
        elif src["kind"] == "moit_fuel":
            links = []
            for listing in MOIT_PAGES:
                links += [u for u in moit_release_links(page(listing)) if u not in links]
            found = []
            for u in links[:MOIT_PER_RUN + 1]:  # one more: the letter of a period sits beside its release
                try:
                    found.append(parse_moit_fuel(page(u)))
                except MacroError:  # an attachment page with no ceilings in its text: the release of that period is read instead
                    continue
            if links and not found:
                raise MacroError("moit_fuel_unreadable")
            points = sorted({f["date"]: f[src["field"]] for f in found if f.get(src["field"]) and f["date"].isoformat() not in known}.items())
            return points or None  # no new period published: nothing new, not a failure
        elif src["kind"] == "sjc_gap":
            from investment_agent.market.gold_price import gold_prices
            sjc = (((gold_prices(store.root.parent).get("kinds") or {}).get(SJC_KIND) or {}).get("sell"))
            if not sjc:
                raise MacroError("no_sjc_price")
            xau = Decimal(parse_gold_api(page(GOLD_API))[0][1])
            fx = Decimal(str(parse_vcb_xml(page(VCB_XML), currency="USD", field="Sell")[1]).replace(",", ""))
            world = xau * fx * Decimal("3.75") / Decimal("31.1034768")  # đồng a chỉ
            points = [(today, str(((Decimal(sjc) / world - 1) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)))]
        elif src["kind"] == "real_rate":
            # a rate less inflation, from the two stored series (fetched earlier in the run: the config lists them first); never from a
            # missing or out-of-date figure, each judged by its own update rhythm
            values = []
            for key in (src["rate"], src["inflation"]):
                last = (store.read(key) or [None])[-1]
                if last is None:
                    raise MacroError(f"real_rate_missing:{key}")
                if (today - date.fromisoformat(last["date"])).days > specs[key]["max_age_days"]:
                    raise MacroError(f"real_rate_stale:{key}")
                values.append(Decimal(last["value"]))
            points = [(today, _plain((values[0] - values[1]).quantize(Decimal("0.01"), ROUND_HALF_UP)))]
        elif src["kind"] == "sbv_interbank":
            points = parse_sbv_interbank(page(SBV_INTERBANK), term=src["term"])
        elif src["kind"] == "treasury":
            curve = TREASURY_CURVES[src.get("curve", "nominal")]
            points = parse_treasury_csv(page(TREASURY_CSV.format(year=today.year, curve=curve)), column=src["column"])
        elif src["kind"] == "fred":
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
        elif src["kind"] == "sbv_m2":
            points = parse_sbv_m2(page(SBV_M2))
        elif src["kind"] == "sbv_central":
            points = parse_sbv_central(page(SBV_CENTRAL))
        elif src["kind"] == "nso_report":
            points = parse_nso_report(page(NSO_REPORT), field=src["field"])
        elif src["kind"] == "nso_cpi":
            points = parse_nso_cpi(page(NSO_CPI))
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
                return None
        else:
            return False
        if not points:
            raise MacroError("no_observations")
        return points

    results, gaps = {}, {}

    def run(ind):
        src, first_error = ind["source"], None
        known = {o["date"] for o in store.read(ind["id"])}
        while src:
            try:
                points = read(src, known)
                if points is False:  # manual: nothing to fetch
                    break
                if points:
                    store.upsert(ind["id"], points[-400:], entry="auto")
                history = ind["source"].get("history")
                if history and len(store.read(ind["id"])) < HISTORY_MIN_POINTS:
                    start = today.replace(year=today.year - HISTORY_YEARS, day=min(today.day, 28))
                    older = parse_fred_csv(page(FRED_CSV.format(series=history["series"]) + f"&cosd={start.isoformat()}"))
                    have = {o["date"] for o in store.read(ind["id"])}
                    store.upsert(ind["id"], [p for p in older if p[0].isoformat() not in have], entry="auto")
                results[ind["id"]] = "ok"
                if src["kind"] == "fred" and src.get("transform") == "yoy":  # a month the source cannot give a change for is named
                    gaps[ind["id"]] = fred_yoy_gap(page(FRED_CSV.format(series=src["series"])))
                break
            except Exception as exc:  # network, parse or source change: the fallback is tried; a timeout anywhere is the error
                if first_error is None or ("Timeout" in type(exc).__name__ and "Timeout" not in type(first_error).__name__):
                    first_error = exc  # reported, so a slow source gets its second, slower try in macro_sync
                src = src.get("fallback")
        if ind["id"] not in results and first_error is not None:
            results[ind["id"]] = f"error:{error_name(first_error)}"

    # Sources on different hosts side by side; one host's indicators one after another (21/11/2026: about 58 s a run, read in
    # sequence). The real rate reads two series of this run, so it goes last.
    groups: dict[str, list] = {}
    for ind in indicators:
        if (g := source_group(ind)) is not None:
            groups.setdefault(g, []).append(ind)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SOURCES) as pool:
        for done in pool.map(lambda members: [run(i) for i in members], list(groups.values())):
            pass
    for ind in indicators:
        if source_group(ind) is None:
            run(ind)
    results = {i["id"]: results[i["id"]] for i in indicators if i["id"] in results}  # in the configured order
    store.record_statuses(results)
    if gaps:
        store.record_gaps(gaps)
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


# Monthly world prices for Chuỗi giá trị's input and output costs, kept under data/macro/ but outside macro-indicators.json, so they never
# show on Vĩ mô. FRED's copy of the IMF prices ran two to three months behind (20/11/2026: September last), so the others moved to the
# World Bank's sheet (WB_COMMODITIES, fetch_chain_series). World shrimp, which the sheet dropped in 2023, was read here until the
# owner removed Thủy sản (21/11/2026).
# US private investment in software (BEA, quarterly, billions a year) is the owner's chosen stand-in for IT demand abroad (20/11/2026):
# FPT's largest market is Japan, which has no such public series, so it is labelled a stand-in on the page.
# US clothing stores' inventories to sales (Census, monthly) stands for US apparel demand in Dệt may (owner, 21/11/2026), the ratio
# Shinhan's MSH report reads (24/08/2026, p. 1 and 3).
COMMODITIES = {"us_software_invest": "B985RC1Q027SBEA", "us_apparel_inv_ratio": "MRTSIR448USS"}
# The US 3-2-1 crack spread stands for the refining margin in Xăng dầu (owner, 21/11/2026): no Singapore crack is public. EIA's daily
# spot prices on FRED, each day with all three: (2 x New York Harbor gasoline + 1 x New York Harbor ULSD) x 42 / 3 - Brent, USD a barrel.
CRACK_SERIES = {"gasoline": "DGASNYH", "diesel": "DDFUELNYH", "brent": "DCOILBRENTEU"}
CRACK_KEY, CRACK_DAYS = "crack_321_us", 400
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
    try:
        since = (today - timedelta(days=CRACK_DAYS)).isoformat()
        legs = {k: dict((d, Decimal(v)) for d, v in parse_fred_csv(_get_with_retry(get, FRED_CSV.format(series=s) + f"&cosd={since}", sleep)))
                for k, s in CRACK_SERIES.items()}
        days = sorted(set(legs["gasoline"]) & set(legs["diesel"]) & set(legs["brent"]))
        points = [(d, _plain(((2 * legs["gasoline"][d] + legs["diesel"][d]) * 42 / 3 - legs["brent"][d]).quantize(Decimal("0.01"), ROUND_HALF_UP)))
                  for d in days]
        if not points:
            raise MacroError("no_observations")
        store.upsert(CRACK_KEY, points, entry="auto")
        results[CRACK_KEY] = "ok"
    except Exception as exc:
        results[CRACK_KEY] = f"error:{type(exc).__name__}"
    return results


# Chuỗi giá trị series from other public sources (checked 15/11/2026), kept like the commodity prices (never on Vĩ mô):
# - urea from the World Bank's monthly commodity prices ("Pink Sheet"; worldbank.org robots.txt allows the page, thedocs has none), whose
#   workbook link changes each month, so it is read from the page; fetched only while last month's price is missing;
# - Vietnam's container throughput against a year before, from the monthly posts of the Vietnam Seaports Association (robots.txt allows
#   all but /wp-admin/), which began in 10/2026, so the series fills in month by month.
WB_COMMODITY_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
VPA_POSTS = "https://www.vpa.org.vn/wp-json/wp/v2/posts?search=container%20throughput&per_page=24&_fields=date,title"
# Columns of the sheet's "Monthly Prices", the same goods as the IMF series they replace (rubber: RSS3, as IMF's PRUBBUSDM; sugar: the
# world price, as PSUGAISAUSDM; wheat: US hard red winter, as PWHEAMTUSDM). Units are the World Bank's.
WB_COMMODITIES = {"com_urea": "Urea", "com_coal": "Coal, Australian", "com_iron_ore": "Iron ore, cfr spot", "com_rubber": "Rubber, RSS3",
                  "com_sugar": "Sugar, world", "com_lng": "Liquefied natural gas, Japan", "com_aluminium": "Aluminum", "com_copper": "Copper",
                  "com_wheat": "Wheat, US HRW", "com_soybean": "Soybeans",
                  "com_cotton": "Cotton, A Index"}  # Dệt may (owner, 21/11/2026)
# More Chuỗi giá trị series (checked 20/11/2026, robots.txt read first), fetched by fetch_chain_extras:
# - the FAO Dairy Price Index (2014-2016 = 100), monthly, in FAO's public food price index file (fao.org allows /media/docs/); read only
#   while last month is missing;
# - the water flowing into Vietnam's large hydropower reservoirs (EVN's public reservoir page, no robots.txt), each day at 00:00 against
#   the same day a year before, over the reservoirs reported on both days: inflow follows the seasons, so a month-on-month move would
#   read every dry season as bad. The last seven days are kept (two pages a missing day).
FAO_INDICES = "https://www.fao.org/media/docs/worldfoodsituationlibraries/wfs-library/food_price_indices_data.csv"
EVN_RESERVOIRS = "https://hochuathuydien.evn.com.vn/PageHoChuaThuyDienEmbedEVN.aspx"
HYDRO_DAYS, HYDRO_MIN_RESERVOIRS = 7, 10
# Freight and steel from China's exchanges (checked 20/11/2026; neither site has a robots.txt), fetched by fetch_chain_markets:
# - the Shanghai Shipping Exchange's public current index (no login): the composite of SCFI (container freight out of Shanghai, weekly)
#   and CTFI (crude tankers into China, daily), each with the period before, so a move reads from the first run;
# - the Shanghai Futures Exchange's public daily data: the settlement price of the hot-rolled coil contract most held (CNY a tonne),
#   for the last week's weekdays and, once, the first trading day found a month back. Days without trading (holidays) are skipped.
SSE_INDEX = "https://en.sse.net.cn/currentIndex"
SSE_SERIES = {"com_container_scfi": ("scfi", "SCFI_T"), "com_tanker_ctfi": ("ctfi", "CTFI_T")}
SHFE_DAILY = "https://www.shfe.com.cn/data/tradedata/future/dailydata/kx{day}.dat"
SHFE_WEEK, SHFE_MONTH_BACK, SHFE_RECENT = 7, (30, 37), 10
CHAIN_SERIES = (*WB_COMMODITIES, "port_container_yoy", CRACK_KEY, "com_dairy", "vn_hydro_inflow_yoy", *SSE_SERIES, "com_steel_hrc")
_XL = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_XL_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_EN_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                                          "november", "december"), start=1)}
_VPA = re.compile(r"(?i)^(" + "|".join(_EN_MONTHS) + r")\s+(\d{4})\s+container throughput\b.*?\b(up|down)\s+([\d.]+)%\s+year[\s-]+on[\s-]+year")


def parse_wb_link(page: str) -> str:
    m = re.search(r'href="(https://thedocs\.worldbank\.org/[^"]+/CMO-Historical-Data-Monthly\.xlsx)"', page)
    if not m:
        raise MacroError("wb_link_missing")
    return m.group(1)


def parse_wb_monthly(data: bytes, *, column: str) -> list[tuple[date, str]]:
    """One column of the "Monthly Prices" sheet, dated to the month's first day like the FRED series; blanks ("…") are skipped."""
    z = zipfile.ZipFile(io.BytesIO(data))
    rid = next((s.get(_XL_REL + "id") for s in ET.fromstring(z.read("xl/workbook.xml")).iter(_XL + "sheet") if s.get("name") == "Monthly Prices"), None)
    target = next((r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")) if r.get("Id") == rid), None)
    if target is None:
        raise MacroError("wb_sheet_missing")
    strings = ["".join(t.text or "" for t in si.iter(_XL + "t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
    rows = []
    for row in ET.fromstring(z.read("xl/" + target.lstrip("/").removeprefix("xl/"))).iter(_XL + "row"):
        cells = {}
        for c in row.iter(_XL + "c"):
            v = c.find(_XL + "v")
            if v is not None and v.text is not None:
                cells[re.match(r"[A-Z]+", c.get("r")).group(0)] = strings[int(v.text)] if c.get("t") == "s" else v.text
        rows.append(cells)
    col = next((k for r in rows for k, v in r.items() if v.strip() == column), None)
    if col is None:
        raise MacroError("wb_column_missing")
    out = []
    for r in rows:
        m = re.fullmatch(r"(\d{4})M(\d{2})", r.get("A", "").strip())
        try:
            value = Decimal(r.get(col, ""))
        except InvalidOperation:
            continue
        if m and value > 0:
            out.append((date(int(m.group(1)), int(m.group(2)), 1), _plain(value)))
    if not out:
        raise MacroError("wb_no_observations")
    return out


def parse_vpa_container(text: str) -> list[tuple[date, str]]:
    """Each "<Month> <year> container throughput reaches … , up|down x% year on year" post, dated to the month's end."""
    found = {}
    for post in json.loads(text):
        m = _VPA.search(html_lib.unescape((post.get("title") or {}).get("rendered") or "").strip())
        if m:
            y, mo = int(m.group(2)), _EN_MONTHS[m.group(1).lower()]
            found.setdefault(date(y, mo, calendar.monthrange(y, mo)[1]), _plain(Decimal(m.group(4)) * (-1 if m.group(3).lower() == "down" else 1)))
    if not found:
        raise MacroError("vpa_unreadable")
    return sorted(found.items())



def fetch_chain_series(store: MacroStore, *, get: Callable[[str], str], get_bytes: Callable[[str], bytes] | None, today: date | None = None,
                       sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """The World Bank's world prices (only with a bytes fetcher, and only while one lacks last month or still holds points from another
    source; each series is then replaced whole) and container throughput; each reported apart."""
    today = today or datetime.now(VN).date()
    results = {}
    if get_bytes is not None:
        last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

        def due(key: str) -> bool:
            have = store.read(key)
            return not have or date.fromisoformat(have[-1]["date"]) < last_month or any(o.get("source_url") != WB_COMMODITY_PAGE for o in have)
        try:
            sheet = None
            if any(due(k) for k in WB_COMMODITIES):
                sheet = get_bytes(parse_wb_link(_get_with_retry(get, WB_COMMODITY_PAGE, sleep)))
            for key, column in WB_COMMODITIES.items():
                try:
                    if sheet is not None and due(key):
                        store.upsert(key, parse_wb_monthly(sheet, column=column)[-COMMODITY_YEARS * 12:], entry="auto",
                                     source_url=WB_COMMODITY_PAGE, replace=True)
                    results[key] = "ok"
                except Exception as exc:
                    results[key] = f"error:{type(exc).__name__}"
        except Exception as exc:
            results.update({k: f"error:{type(exc).__name__}" for k in WB_COMMODITIES})
    try:
        store.upsert("port_container_yoy", parse_vpa_container(_get_with_retry(get, VPA_POSTS, sleep)), entry="auto")
        results["port_container_yoy"] = "ok"
    except Exception as exc:
        results["port_container_yoy"] = f"error:{type(exc).__name__}"
    return results


def parse_fao_dairy(text: str) -> list[tuple[date, str]]:
    """The Dairy column of FAO's food price indices, dated to the month's first day; blank months are skipped."""
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    head = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Date"), None)
    if head is None or "Dairy" not in [c.strip() for c in rows[head]]:
        raise MacroError("fao_column_missing")
    col, out = [c.strip() for c in rows[head]].index("Dairy"), []
    for r in rows[head + 1:]:
        m = re.fullmatch(r"(\d{4})-(\d{2})", (r[0] if r else "").strip())
        try:
            value = Decimal(r[col].strip()) if m and len(r) > col else None
        except InvalidOperation:
            value = None
        if m and value is not None and value > 0:
            out.append((date(int(m.group(1)), int(m.group(2)), 1), _plain(value)))
    if not out:
        raise MacroError("fao_no_observations")
    return out


def parse_evn_inflow(page: str) -> dict[str, Decimal]:
    """Each reservoir's inflow (m3/s, the "Lưu lượng đến hồ" column) on EVN's reservoir page; blank or dashed cells are skipped."""
    out = {}
    for row in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", page):
        cells = [html_lib.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"(?s)<td[^>]*>(.*?)</td>", row)]
        if len(cells) < 6 or "Mực nước" in cells[0]:
            continue
        name = re.split(r"Đồng bộ lúc", unicodedata.normalize("NFC", cells[0]))[0].strip()
        try:
            flow = Decimal(cells[5].replace(",", ""))
        except InvalidOperation:
            continue
        if name and flow >= 0:
            out[name] = flow
    return out


def fetch_chain_extras(store: MacroStore, *, get: Callable[[str], str], today: date | None = None,
                       sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """FAO's dairy index and the hydropower inflow against a year before; each reported apart."""
    today = today or datetime.now(VN).date()
    results = {}
    try:
        have = store.read("com_dairy")
        last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        if not have or date.fromisoformat(have[-1]["date"]) < last_month:
            store.upsert("com_dairy", parse_fao_dairy(_get_with_retry(get, FAO_INDICES, sleep))[-COMMODITY_YEARS * 12:], entry="auto",
                         source_url=FAO_INDICES)
        results["com_dairy"] = "ok"
    except Exception as exc:
        results["com_dairy"] = f"error:{type(exc).__name__}"
    points = []
    try:
        known = {o["date"] for o in store.read("vn_hydro_inflow_yoy")}
        for back in range(HYDRO_DAYS - 1, -1, -1):
            day = today - timedelta(days=back)
            if day.isoformat() in known:
                continue
            before = day.replace(year=day.year - 1, day=28 if day.month == 2 and day.day == 29 else day.day)
            page = lambda d: parse_evn_inflow(_get_with_retry(get, f"{EVN_RESERVOIRS}?td={d:%d/%m/%Y}%2000:00&vm=&lv=&hc=", sleep))  # noqa: E731
            now, then = page(day), page(before)
            shared = [n for n in now if n in then]
            total_then = sum((then[n] for n in shared), Decimal(0))
            if len(shared) < HYDRO_MIN_RESERVOIRS or total_then <= 0:
                raise MacroError("evn_too_few_reservoirs")
            change = (sum((now[n] for n in shared), Decimal(0)) / total_then - 1) * 100
            points.append((day, str(change.quantize(Decimal("0.1"), ROUND_HALF_UP))))
        if points:
            store.upsert("vn_hydro_inflow_yoy", points, entry="auto", source_url=EVN_RESERVOIRS)
        results["vn_hydro_inflow_yoy"] = "ok"
    except Exception as exc:
        if points:
            store.upsert("vn_hydro_inflow_yoy", points, entry="auto", source_url=EVN_RESERVOIRS)
        results["vn_hydro_inflow_yoy"] = f"error:{type(exc).__name__}"
    return results


def parse_sse_index(text: str, item: str) -> list[tuple[date, str]]:
    """The composite (item, e.g. SCFI_T) of the period before and this one, from the exchange's current index."""
    data = json.loads(text).get("data") or {}
    line = next((x for x in data.get("lineDataList") or [] if x.get("dataItemTypeName") == item), None)
    if line is None or line.get("currentContent") is None:
        raise MacroError("sse_index_missing")
    out = [(date.fromisoformat(data["lastDate"]), line.get("lastContent")), (date.fromisoformat(data["currentDate"]), line["currentContent"])]
    return [(d, _plain(Decimal(str(v)))) for d, v in out if v is not None]


def parse_shfe_hrc(text: str) -> str:
    """The settlement price of the hot-rolled coil contract (hc) with the most open interest that day."""
    rows = [r for r in json.loads(text).get("o_curinstrument") or []
            if str(r.get("PRODUCTID", "")).strip() == "hc_f" and re.fullmatch(r"\d{4}", str(r.get("DELIVERYMONTH", "")).strip())
            and isinstance(r.get("SETTLEMENTPRICE"), (int, float)) and r["SETTLEMENTPRICE"] > 0]
    if not rows:
        raise MacroError("shfe_no_hrc")
    return _plain(Decimal(str(max(rows, key=lambda r: r.get("OPENINTEREST") or 0)["SETTLEMENTPRICE"])))


SHFE_QUARTERS, SHFE_QUARTER_BACK, SHFE_PACE_SECONDS = 12, 10, 2  # HRC cuối quý (owner, 23/11/2026)


def _shfe_state(store: MacroStore) -> Path:
    return Path(store.root).parent / "macro-state" / "shfe-hrc-quarters.json"


def _shfe_answer(get: Callable[[str], str], day: date) -> tuple[str, str | None]:
    """("price", the HRC price), ("none", None) when SHFE answered there was no trading that day (a 404, or a day file without hot-rolled
    coil), or ("error", None) when it could not be asked: a failure is not a holiday (review 23/11/2026)."""
    import httpx
    try:
        return "price", parse_shfe_hrc(get(SHFE_DAILY.format(day=f"{day:%Y%m%d}")))
    except MacroError:
        return "none", None
    except httpx.HTTPStatusError as exc:
        return ("none", None) if exc.response.status_code == 404 else ("error", None)
    except Exception:  # noqa: BLE001 - the network, a timeout, a page that does not read
        return "error", None


def _shfe_quarter_ends(store: MacroStore, today: date, known: set[str], answer, sleep) -> tuple[list[tuple[date, str]], set[str]]:
    """HRC cuối quý (owner, 23/11/2026): the last trading day of each of the last 12 closed quarters, the year-before price that Giá bán
    giảm, dự phòng không tăng needs: from the quarter's end a day at a time, at most 10 days; a day already stored is that last trading day
    and ends the step back. A quarter is marked tried (data/macro-state/shfe-hrc-quarters.json) only once every day asked was answered, so
    a network failure is tried again on the next run (review 23/11/2026). Calls 2 seconds apart. Returns the prices found and the quarters
    now tried, for the caller to record once the prices are stored."""
    state_path = _shfe_state(store)
    try:
        tried = set(json.loads(state_path.read_text(encoding="utf-8"))["tried"]) if state_path.is_file() else set()
    except (OSError, ValueError, KeyError, TypeError):
        tried = set()
    ends, y, n = [], today.year, (today.month - 1) // 3  # the quarter before the current one
    while len(ends) < SHFE_QUARTERS:
        if n == 0:
            y, n = y - 1, 4
        month = 3 * n
        ends.append(date(y, month, 31 if month in (3, 12) else 30))
        n -= 1
    out, done, called = [], set(), False
    for end in ends:
        key = end.isoformat()
        if key in tried:
            continue
        answered = True
        for day in (end - timedelta(days=k) for k in range(SHFE_QUARTER_BACK)):
            if day.weekday() >= 5:
                continue
            if day.isoformat() in known:
                break  # the quarter's last trading day is already stored
            if called:
                sleep(SHFE_PACE_SECONDS)
            called = True
            kind, price = answer(day)
            if kind == "price":
                out.append((day, price))
                break
            if kind == "error":
                answered = False
                break
        if answered:
            done.add(key)
    return out, tried | done


def _record_shfe_tried(store: MacroStore, tried: set[str]) -> None:
    state_path = _shfe_state(store)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"tried": sorted(tried)}), encoding="utf-8")
    os.replace(tmp, state_path)


def fetch_chain_markets(store: MacroStore, *, get: Callable[[str], str], today: date | None = None,
                        sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Container and tanker freight from the Shanghai Shipping Exchange and the hot-rolled coil price from the Shanghai Futures Exchange;
    each reported apart."""
    today = today or datetime.now(VN).date()
    results = {}
    for key, (name, item) in SSE_SERIES.items():
        try:
            store.upsert(key, parse_sse_index(_get_with_retry(get, f"{SSE_INDEX}?indexName={name}", sleep), item), entry="auto",
                         source_url=SSE_INDEX)
            results[key] = "ok"
        except Exception as exc:
            results[key] = f"error:{type(exc).__name__}"

    def day_price(day: date) -> str | None:
        try:
            return parse_shfe_hrc(get(SHFE_DAILY.format(day=f"{day:%Y%m%d}")))
        except Exception:  # no trading that day (or the page failed): the day is simply missing
            return None
    try:
        known = {o["date"] for o in store.read("com_steel_hrc")}
        points = []
        for back in range(SHFE_WEEK - 1, -1, -1):
            day = today - timedelta(days=back)
            if day.weekday() < 5 and day.isoformat() not in known and (price := day_price(day)):
                points.append((day, price))
        if not any(d <= (today - timedelta(days=SHFE_MONTH_BACK[0])).isoformat() for d in known):
            for back in range(SHFE_MONTH_BACK[0], SHFE_MONTH_BACK[1] + 1):
                day = today - timedelta(days=back)
                if day.weekday() < 5 and (price := day_price(day)):
                    points.append((day, price))
                    break
        quarter_points, tried = _shfe_quarter_ends(store, today, known, lambda day: _shfe_answer(get, day), sleep)
        points += quarter_points
        if points:
            store.upsert("com_steel_hrc", points, entry="auto", source_url=SHFE_DAILY.format(day=""))
        _record_shfe_tried(store, tried)  # only once the prices found are stored (review 23/11/2026)
        have = store.read("com_steel_hrc")
        if not have or (today - date.fromisoformat(have[-1]["date"])).days > SHFE_RECENT:
            raise MacroError("shfe_no_recent")
        results["com_steel_hrc"] = "ok"
    except Exception as exc:
        results["com_steel_hrc"] = f"error:{type(exc).__name__}"
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


def _sessions_after(last: date, today: date, is_session) -> int:
    """HOSE sessions after the figure's day up to today."""
    return sum(1 for i in range(1, (today - last).days + 1) if is_session(last + timedelta(days=i)))


def macro_rows(indicators: list[dict], store: MacroStore, *, today: date, is_session=None) -> list[dict]:
    """A session indicator (max_age_sessions, owner 22/11/2026) is old by the HOSE sessions it has missed, so a long holiday is not an
    alert; the others by calendar days (max_age_days)."""
    if is_session is None:
        from investment_agent.market.sessions import is_session
    rows, statuses, gaps = [], store.statuses(), store.gaps()
    for ind in indicators:
        obs = store.read(ind["id"])
        status = statuses.get(ind["id"], {}).get("status")
        last = obs[-1] if obs else None
        trend, assessment = evaluate(ind["rule"], [o["value"] for o in obs[-2:]])
        sessions = ind.get("max_age_sessions")
        age_sessions = _sessions_after(date.fromisoformat(last["date"]), today, is_session) if last and sessions else None
        stale = last is not None and (age_sessions > sessions if sessions else (today - date.fromisoformat(last["date"])).days > ind["max_age_days"])
        rows.append({"id": ind["id"], "label": ind["label"], "unit": ind["unit"], "auto": ind["source"]["kind"] != "manual", "period": ind.get("period"),
                     "value": last["value"] if last else None, "date": last["date"] if last else None,
                     "previous": obs[-2]["value"] if len(obs) >= 2 else None, "trend": trend, "assessment": assessment,
                     "stale": stale, "age_sessions": age_sessions,
                     "source_url": (last or {}).get("source_url") or ind["url"], "note": ind.get("note"), "gap": gaps.get(ind["id"]),
                     # a hand-entered indicator has no source to fail; a status left from an older automatic source is not shown
                     "source_error": status if status not in (None, "ok") and ind["source"]["kind"] != "manual" else None,
                     "manual_allowed": ind["source"]["kind"] == "manual" or bool(ind["source"].get("manual_fallback"))})
    return rows
