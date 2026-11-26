"""Số lượng giao dịch nội bộ đọc từ văn bản HOSE (owner, 26/11/2026; docs/superpowers/specs/2026-11-26-so-luong-tu-van-ban-hose-design.md).

Many of VNDirect's insider notices carry no kind or volume; the figures are in the PDF attached to the HOSE notice. The after-close
run downloads those PDFs for watched tickers, reads them on this machine (OCR for scans, never a model) and takes a volume only
when the document's own figures add up: held before ± traded = held after, to the share. Readings live in
data/insider-docs/<HOSE news id>.json, one per notice, read once; insider_deals fills what VNDirect lacks from them at read time.
"""

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote

MEDIA = "https://api.hsx.vn/m/api/v1/1/mediafiles/1/{id}?pageIndex=1&pageSize=100&year=0"
STATIC = "https://staticfile.hsx.vn/"
LIMIT = 30
MAX_FILES = 8
MAX_BYTES = 15 * 1024 * 1024
PAUSE = 1.0
_NEWS = re.compile(r"^https://(?:www\.)?hsx\.vn/.+/(\d{1,12})$")
_ID = re.compile(r"^\d{1,12}$")
# A share count as printed in Vietnamese ("20.623.635"), or a bare 0; percentages ("1,84") and item numbers never match.
_COUNT = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|0)(?![\d.,]*\d)")
# Where an item ends: the next line opening with an item number ("6.", "| 7.") or a bullet ("- ").
_ITEM_END = re.compile(r"\n[|\s]*(?:\d{1,2}(?:\.\s|\s)|-\s)")  # "21.273.635" opening a line is a figure, not item 21
_BEFORE = re.compile(r"nam giu truoc khi thuc hien giao dich")
_AFTER = re.compile(r"nam giu sau khi thuc hien giao dich")
_TRADED_INSIDER = re.compile(r"so luong co phieu da giao dich")
_TRADED_GROUP = re.compile(r"so luong co phieu da mua/ban")
_TRADED_STATED = re.compile(r"so luong co phieu da (mua|ban)\b(?!/)")  # an organisation's report: "Số lượng cổ phiếu đã Mua: 141.000"
_KIND = re.compile(r"loai giao dich da thuc hien[^:\n]*:\s*\W*(mua|ban|duoc cho|cho)\b")
_ESOP_METHOD = "mua truc tiep tu to chuc phat hanh"
_GIFT_METHOD = re.compile(r"phuong thuc giao dich[^\n]*cho/tang")  # "... do cho/tặng", "... do được cho/tặng"
# What the stated kind means: (holding goes up, kind when it is a gift)
_STATED = {"mua": (True, None), "ban": (False, None), "duoc cho": (True, "Nhận tặng"), "cho": (False, "Cho tặng")}
MISSING = "thiếu số trước, đã giao dịch hoặc sau"


def _plain(text: str) -> str:
    """Lower case without accents, đ as d, spaces collapsed within lines: OCR gets accents wrong far more often than letters."""
    text = unicodedata.normalize("NFD", text or "").replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return "\n".join(re.sub(r"[ \t]+", " ", line) for line in text.splitlines())


def _count(text: str, label: re.Pattern) -> tuple[int | None, re.Match | None]:
    """The first share count inside the item a label opens, with that label; each place the label appears is tried in turn."""
    for m in label.finditer(text):
        rest = text[m.end():]
        end = _ITEM_END.search(rest)
        found = _COUNT.search(rest[:end.start() if end else 400][:400])
        if found:
            return int(found.group(1).replace(".", "")), m
    return None, None


_TOTAL = re.compile(r"tong ca nhom")


def _group_total(text: str) -> tuple[int, int, int] | None:
    """A foreign investor group's table: the total row's three counts, before, after and traded (a decrease in brackets), on the
    label's line or the next two; anything but exactly three counts is not taken."""
    for m in _TOTAL.finditer(text):
        lines = text[m.end():].split("\n")[:3]
        counts = [int(c.replace(".", "")) for c in _COUNT.findall("\n".join(lines))]
        if len(counts) == 3:
            return counts[0], counts[1], counts[2]
    return None


def parse_report(text: str, title: str) -> dict:
    """{kind, shares, before, after, rong} when the report's figures add up, else {reason}."""
    plain = _plain(text)
    before, after = _count(plain, _BEFORE)[0], _count(plain, _AFTER)[0]
    if before is None and after is None and (total := _group_total(plain)):
        before, after, traded = total
        if traded == 0:
            return {"reason": "không giao dịch cổ phiếu nào"}
        if abs(after - before) != traded:
            return {"reason": "cộng trừ không khớp"}
        return {"kind": "Mua" if after > before else "Bán", "shares": traded, "before": before, "after": after, "rong": True}
    stated = _KIND.search(plain)
    stated = stated.group(1) if stated else None
    traded, label = _count(plain, _TRADED_INSIDER)
    group = False
    if traded is None:
        traded, label = _count(plain, _TRADED_STATED)
        stated = label.group(1) if label else stated
    if traded is None and not stated:
        traded, label = _count(plain, _TRADED_GROUP)
        group = traded is not None
    if before is None or after is None or traded is None:
        return {"reason": MISSING}
    if traded == 0:
        return {"reason": "không giao dịch cổ phiếu nào"}
    if abs(after - before) != traded:
        return {"reason": "cộng trừ không khớp"}
    if stated and (after > before) != _STATED[stated][0]:
        return {"reason": "chiều không khớp"}
    kind = "Mua" if after > before else "Bán"  # the stated kind when there is one; the figures when its line is unreadable
    if (stated and _STATED[stated][1]) or (not stated and _GIFT_METHOD.search(plain)):
        kind = "Nhận tặng" if after > before else "Cho tặng"  # a transfer between people, not a trade on the market
    rong = False
    if group:
        cut = _AFTER.search(plain, label.end())
        part = plain[label.end():cut.start() if cut else None]
        rong = bool(re.search(r"\bmua\b", part)) and bool(re.search(r"\bban\b", part))
    if kind == "Mua" and ("esop" in _plain(title) or _ESOP_METHOD in plain):
        kind = "ESOP"
    return {"kind": kind, "shares": traded, "before": before, "after": after, "rong": rong}


def news_id(doc_url) -> str | None:
    m = _NEWS.match(str(doc_url or ""))
    return m.group(1) if m else None


def read_notice(nid: str, title: str, *, get_json: Callable[[str], dict], get_bytes: Callable[[str], bytes],
                pdf_text: Callable[[bytes], list[str]], sleep: Callable[[float], None], now: datetime) -> dict:
    """One notice's reading; a failing call raises, so nothing is stored and the notice is tried again on the next run."""
    def done(result=None, reason=None):
        return {"news_id": nid, "title": title, "read_at": now.isoformat(), "result": result, "reason": reason}
    files = [f for f in (get_json(MEDIA.format(id=nid)).get("data") or {}).get("list") or []
             if str(f.get("fileType") or "").lower() == ".pdf" and str(f.get("filePath") or "").startswith("~/")]
    if not files:
        return done(reason="không có tệp đính kèm")
    if len(files) > MAX_FILES:
        return done(reason=f"có {len(files)} tệp, quá {MAX_FILES}")
    readings = []
    for f in files:
        name = str(f.get("fileName") or "")
        sleep(PAUSE)
        data = get_bytes(STATIC + quote(f["filePath"][2:]))
        if len(data) > MAX_BYTES:
            return done(reason=f"{name}: tệp quá lớn")
        text = "\n".join(pdf_text(data))
        if not text.strip():
            return done(reason=f"{name}: không đọc được chữ")
        got = parse_report(text, title)
        if "reason" in got:
            return done(reason=f"{name}: {got['reason']}")
        readings.append(got)
    if len({r["kind"] for r in readings}) > 1:
        return done(reason="các tệp khác loại")
    one = readings[0] if len(readings) == 1 else {}
    return done({"kind": readings[0]["kind"], "shares": sum(r["shares"] for r in readings), "files": len(readings),
                 "rong": any(r["rong"] for r in readings), "before": one.get("before"), "after": one.get("after")})


class DocStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "insider-docs"

    def _path(self, nid: str) -> Path:
        if not _ID.fullmatch(str(nid)):
            raise ValueError("invalid news id")
        return self.root / f"{nid}.json"

    def read(self, nid: str) -> dict | None:
        path = self._path(nid)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, nid: str, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(nid)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def _lacking(d: dict) -> bool:
    return d.get("kind") is None or d.get("shares") is None


def fill_from_docs(deals: list[dict], docs: DocStore) -> list[dict]:
    """Deals with what VNDirect lacks filled in from accepted readings; VNDirect's own kind and volume are never replaced."""
    out = []
    for d in deals:
        nid = news_id(d.get("doc_url")) if _lacking(d) else None
        rec = docs.read(nid) if nid else None
        result = (rec or {}).get("result")
        kind = d.get("kind")
        # VNDirect's kind, when it has one, must point the same way as the document's (ESOP is a purchase)
        if result and (kind is None or (kind == "Mua") == (result["kind"] in ("Mua", "ESOP"))):
            d = {**d, "kind": kind or result["kind"], "shares": result["shares"],
                 "tu_van_ban": {"truoc": result["before"], "sau": result["after"], "so_tep": result["files"],
                                "rong": result["rong"], "doc_luc": rec.get("read_at")}}
        out.append(d)
    return out


def sync_insider_docs(data_dir: Path, symbols: list[str], *, read: Callable[..., dict], limit: int = LIMIT) -> dict:
    """Reads the newest unread HOSE result reports lacking a volume among the stored notices of the given tickers."""
    from .insider_deals import InsiderStore

    store, docs = InsiderStore(data_dir), DocStore(data_dir)
    due, seen = [], set()
    for symbol in symbols:
        try:
            record = store.read(symbol) or {}
        except ValueError:
            continue
        for d in record.get("deals") or []:
            nid = news_id(d.get("doc_url"))
            if (nid and nid not in seen and _lacking(d) and _plain(d.get("title") or "").startswith("bao cao")
                    and docs.read(nid) is None):
                seen.add(nid)
                due.append((d.get("date") or "", nid, d.get("title") or ""))
    due.sort(reverse=True)
    out = {"read": 0, "accepted": 0, "rejected": 0, "errors": 0, "left": max(0, len(due) - max(limit, 0))}
    for _, nid, title in due[:max(limit, 0)]:
        try:
            rec = read(nid, title)
        except Exception:
            out["errors"] += 1
            continue
        docs.save(nid, rec)
        out["read"] += 1
        out["accepted" if rec.get("result") else "rejected"] += 1
    return out
