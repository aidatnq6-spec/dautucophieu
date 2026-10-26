"""News for the brief: public RSS headlines (CafeF, Vietstock, Vneconomy), filtered on this machine without AI.

robots.txt of these sites allows the feeds (checked 2026-10-26); VnExpress disallows all crawling and is not used.
Only title, link, source and time are kept.
"""

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from investment_agent.insights.sources import safe_url

FEEDS = (("CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"), ("CafeF", "https://cafef.vn/vi-mo-dau-tu.rss"),
         ("Vietstock", "https://vietstock.vn/830/chung-khoan/co-phieu.rss"), ("Vietstock", "https://vietstock.vn/761/kinh-te/vi-mo.rss"),
         ("Vneconomy", "https://vneconomy.vn/chung-khoan.rss"))
MACRO_KEYWORDS = ("lãi suất", "tỷ giá", "fed", "gdp", "cpi", "lạm phát", "nhnn", "ngân hàng nhà nước", "thuế quan", "xuất khẩu",
                  "nhập khẩu", "fdi", "trái phiếu chính phủ", "room tín dụng")
_ITEM = re.compile(r"<item\b.*?</item>", re.S)
VN = ZoneInfo("Asia/Ho_Chi_Minh")


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}\b[^>]*>(.*?)</{name}>", block, re.S)
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S) if m else ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def parse_rss(xml: str, source: str) -> list[dict]:
    out = []
    for block in _ITEM.findall(xml):
        title, url = _tag(block, "title"), safe_url(_tag(block, "link"))
        try:
            published = parsedate_to_datetime(_tag(block, "pubDate"))
        except (TypeError, ValueError):
            continue
        if title and url and published.tzinfo is not None:
            out.append({"title": title, "url": url, "source": source, "published": published.astimezone(VN).isoformat()})
    return out


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", title.casefold())).strip()


def window_items(items: list[dict], *, since: datetime, until: datetime) -> list[dict]:
    seen, out = set(), []
    for it in sorted(items, key=lambda i: datetime.fromisoformat(i["published"]), reverse=True):
        when = datetime.fromisoformat(it["published"])
        key = _norm(it["title"])
        if since <= when <= until and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _mentions(title: str, symbol: str) -> bool:
    # Whole word, and not the tail of a dotted name such as "TP.HCM" (HCM is also a ticker).
    return re.search(rf"(?<![\w.]){re.escape(symbol)}(?!\w)", title) is not None


def pick_news(items: list[dict], *, watched: list[str], held: set[str], sector_names: set[str], limit: int) -> list[dict]:
    """Local relevance: held ticker 3, watched ticker 2, its sector 1, macro keyword 1; ties go to the newest."""
    scored = []
    for it in items:
        title, low = it["title"], it["title"].casefold()
        hit_held = next((s for s in sorted(held) if _mentions(title, s)), None)
        hit_watch = next((s for s in watched if _mentions(title, s)), None)
        hit_sector = next((n for n in sorted(sector_names) if n.casefold() in low), None)
        hit_macro = any(k in low for k in MACRO_KEYWORDS)
        score = 3 if hit_held else 2 if hit_watch else 1 if (hit_sector or hit_macro) else 0
        if score:
            reason = hit_held or hit_watch or hit_sector or "vĩ mô"
            scored.append((score, datetime.fromisoformat(it["published"]), {**it, "reason": reason}))
    ordered = sorted(scored, key=lambda x: (x[0], x[1]), reverse=True)
    return [x[2] for x in ordered[:limit]]
