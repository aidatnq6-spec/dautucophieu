"""Gold prices from Phú Quý's public price table (phuquygroup.vn home page): every kind — SJC bars, Phú Quý rings, jewellery by
purity — with Phú Quý's buying and selling price per chỉ and the time the page gives. phuquygroup.vn has no robots.txt (404: no
restriction, RFC 9309) and no bot wall (checked 06/11/2026). SJC's own price service sits behind a Cloudflare bot check and PNJ's
needs a token, so neither is used. Gold of any brand is valued at the Phú Quý kind the owner picks, and the page says "giá Phú Quý".

The table is read from HTML: the unit in its header must still be per chỉ, or nothing is stored. Silver rows are left out. Kept in
data/gold-price.json (public data only); a failed, empty or changed page keeps what was stored."""

import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

URL = "https://phuquygroup.vn/"
VN = ZoneInfo("Asia/Ho_Chi_Minh")
UNIT = "(VNĐ/Chỉ)"
_WHEN = re.compile(r"cập nhật lần cuối lúc\s+(\d{1,2}:\d{2}\s+\d{1,2}/\d{1,2}/\d{4})")


class GoldPriceStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "gold-price.json"

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)


def gold_prices(data_dir: Path | None) -> dict:
    """{source, unit: "chỉ", as_of, kinds: {name: {buy, sell}}} in đồng per chỉ (sell may be None); empty before the first sync."""
    return GoldPriceStore(data_dir).read() if data_dir is not None else {}


class _Table(HTMLParser):
    """Rows of the price list: [name, buy, sell?] from the tbody cells; the header text, for its unit."""

    def __init__(self):
        super().__init__()
        self.rows, self.header, self._row, self._cell, self._in = [], [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag in ("thead", "tbody"):
            self._in = tag
        elif tag == "tr" and self._in == "tbody":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "td" and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag in ("thead", "tbody"):
            self._in = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        elif self._in == "thead":
            self.header.append(data.strip())


def _dong(text: str) -> str | None:
    digits = text.replace(",", "").replace(".", "").strip()
    return digits if digits.isdigit() and int(digits) > 0 else None


def _parse(page: str) -> tuple[dict, str] | str:
    """(kinds, as_of) or the reason nothing can be stored."""
    when = _WHEN.search(page)
    table = _Table()
    table.feed(page)
    if not when or not table.rows:
        return "empty"
    if table.header.count(UNIT) < 2:
        return "unit"
    kinds = {}
    for row in table.rows:
        if len(row) < 2 or "bạc" in row[0].lower() or not (buy := _dong(row[1])):
            continue
        kinds[row[0]] = {"buy": buy, "sell": _dong(row[2]) if len(row) > 2 else None}
    if not kinds:
        return "empty"
    return kinds, datetime.strptime(" ".join(when.group(1).split()), "%H:%M %d/%m/%Y").replace(tzinfo=VN).isoformat()


HISTORY_FILE = "gold-price-history.json"


def gold_history(data_dir: Path | None) -> dict[str, dict[str, str]]:
    """{kind: {day: buying price per chỉ}}: the last price seen each day, kept from 11/2026 for the month waterfall."""
    path = Path(data_dir) / HISTORY_FILE if data_dir is not None else None
    return json.loads(path.read_text(encoding="utf-8")) if path is not None and path.is_file() else {}


def gold_price_sync(store: GoldPriceStore, *, get: Callable[[str], str], now: datetime) -> dict:
    try:
        parsed = _parse(get(URL))
    except Exception as exc:  # the site is down or changed: keep the stored prices
        return {"status": "error", "reason": type(exc).__name__}
    if isinstance(parsed, str):
        return {"status": "error", "reason": parsed}
    kinds, as_of = parsed
    store.save({"source": "Phú Quý", "unit": "chỉ", "url": URL, "fetched_at": now.isoformat(), "as_of": as_of, "kinds": kinds})
    history = gold_history(store.path.parent)
    for kind, price in kinds.items():
        history.setdefault(kind, {})[as_of[:10]] = price["buy"]
    path = store.path.parent / HISTORY_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return {"status": "ok", "kinds": len(kinds)}
