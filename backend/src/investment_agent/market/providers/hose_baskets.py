"""Rổ chỉ số từ HOSE: the latest "danh mục cổ phiếu thành phần của Chỉ số quy mô VNAllshare" notice in HOSE's news (api.hsx.vn; robots.txt
of hsx.vn allows), its PDF (staticfile.hsx.vn) read for the VN30, VNMidcap and VN100 tables, the reserve lists left out. A list is used
only when it is whole: VN30 thirty tickers, VN100 a hundred numbered without a gap and equal to VN30 with VNMidcap; anything else is
refused with its reason, never patched."""

import html
import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Callable
from urllib.parse import quote
from zoneinfo import ZoneInfo

NEWS_URL = "https://api.hsx.vn/n/api/v1/1/news/newstype/-1/1?pageIndex=1&pageSize=100"
FILES_URL = "https://api.hsx.vn/m/api/v1/1/mediafiles/1/{id}?pageIndex=1&pageSize=10&year=0"
STATIC = "https://staticfile.hsx.vn"
USER_AGENT = "investment-agent/0.1 (personal use)"
VN = ZoneInfo("Asia/Ho_Chi_Minh")
SIZES = {"VN30": 30, "VN100": 100}
_TITLE = re.compile(r"thành phần của chỉ số quy mô vnallshare", re.IGNORECASE)
_PERIOD = re.compile(r"kỳ tháng (\d{1,2}/\d{4})", re.IGNORECASE)
_EFFECTIVE = re.compile(r"hiệu lực (?:vào|từ) ngày (\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE)
_HEADING = re.compile(r"CỔ PHIẾU THÀNH PHẦN (?:CỦA )?CHỈ SỐ (VN30|VNMIDCAP|VN100|VNSMALLCAP)\b")
_ROW = re.compile(r"^(\d{1,3})\s+([A-Z0-9]{3})\s")
_WEIGHT = re.compile(r"([\d,]{4,})\s+(\d{1,3})%\s+([\d.]+)%")


class BasketError(Exception):
    pass


def parse_size_notice(pages: list[str]) -> dict[str, list[str]]:
    """Each page belongs to the index named on it (the heading is printed at its foot), or to the one before when it names none;
    a table's rows run 1, 2, 3…; a row numbered 1 again opens the reserve list, which is left out."""
    tables: dict[str, list[str]] = {}
    weights: dict[str, dict] = {}
    closed: set[str] = set()
    current = None
    for page in pages:
        named = _HEADING.search(page)
        current = named.group(1) if named else current
        if current not in ("VN30", "VNMIDCAP", "VN100"):
            continue  # VNSmallcap and the rest are not read
        for line in page.splitlines():
            row = _ROW.match(line.strip())
            if not row or current in closed:
                continue
            number, code = int(row.group(1)), row.group(2)
            members = tables.setdefault(current, [])
            if number == len(members) + 1:
                members.append(code)
                w = _WEIGHT.search(line) if current == "VN30" else None
                if w:  # shares counted by the index, free float, the cap on its weight
                    weights[code] = {"shares": w.group(1).replace(",", ""),
                                     "free_float": str((Decimal(w.group(2)) / 100).quantize(Decimal("0.01"))),
                                     "cap": str((Decimal(w.group(3)) / 100).quantize(Decimal("0.0001")))}
            elif number == 1 and members:
                closed.add(current)  # the reserve list
            else:
                raise BasketError(f"{current}: dòng số {number} không liền sau dòng {len(members)}")
    for name, size in SIZES.items():
        got = len(tables.get(name, []))
        if got != size:
            raise BasketError(f"{name} có {got} mã, cần {size}")
    if sorted(tables["VN100"]) != sorted(tables["VN30"] + tables.get("VNMIDCAP", [])):
        raise BasketError("VN100 không đúng bằng VN30 và VNMidcap trong cùng thông báo")
    out = {name: tables[name] for name in ("VN30", "VNMIDCAP", "VN100") if name in tables}
    if set(weights) == set(tables["VN30"]):  # every member's weight read, or none kept
        out["weights"] = {"VN30": weights}
    return out


def default_get_text(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=120, follow_redirects=False, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def default_get_bytes(url: str) -> bytes:
    import httpx
    response = httpx.get(url, timeout=120, follow_redirects=False, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    if len(response.content) > 20 * 1024 * 1024:
        raise BasketError("tệp đính kèm quá lớn")
    return response.content


def default_extract(data: bytes) -> list[str]:
    from investment_agent.insights.pdf import extract_pages
    return extract_pages(data, max_pages=40)


def latest_size_baskets(*, get_text: Callable[[str], str] = default_get_text, get_bytes: Callable[[str], bytes] = default_get_bytes,
                        extract: Callable[[bytes], list[str]] = default_extract) -> dict:
    """The newest size-index notice of HOSE: its id, title, period, effective day and the checked VN30, VNMidcap and VN100 lists."""
    items = json.loads(get_text(NEWS_URL))["data"]["list"] or []
    notices = sorted((i for i in items if _TITLE.search(i.get("title") or "")), key=lambda i: i.get("postedDate") or 0, reverse=True)
    if not notices:
        raise BasketError("chưa thấy thông báo danh mục chỉ số quy mô VNAllshare trong tin mới của HOSE")
    notice = notices[0]
    summary = html.unescape(re.sub(r"<[^>]+>", " ", notice.get("summary") or ""))
    effective = _EFFECTIVE.search(summary)
    if not effective:
        raise BasketError("thông báo không ghi ngày hiệu lực")
    files = json.loads(get_text(FILES_URL.format(id=notice["id"])))["data"]["list"] or []
    pdf = next((f for f in files if (f.get("fileName") or "").lower().endswith(".pdf") and f.get("filePath")), None)
    if pdf is None:
        raise BasketError("thông báo không có tệp PDF đính kèm")
    path = pdf["filePath"].replace("~", "", 1)
    data = get_bytes(STATIC + quote(path))
    if not data.startswith(b"%PDF"):
        raise BasketError("tệp đính kèm không phải PDF")
    period = _PERIOD.search(notice["title"])
    return {"notice_id": notice["id"], "title": notice["title"].strip(), "period": period.group(1) if period else None,
            "posted": datetime.fromtimestamp(notice["postedDate"], VN).date().isoformat() if notice.get("postedDate") else None,
            "effective": date(int(effective.group(3)), int(effective.group(2)), int(effective.group(1))),
            "groups": parse_size_notice(extract(data))}
