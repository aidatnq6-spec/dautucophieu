"""AI soạn nháp Thuyết minh TSCĐ (25/11/2026; docs/superpowers/specs/2026-11-25-ai-soan-nhap-thuyet-minh-design.md), an extension of C5b:
from the passages of one public annual report the model drafts construction projects, depreciation ranges, prepaid allocations, business
combinations, capitalised interest and tax incentives. Only the ticker, the year and the passages go out. Every figure must stand verbatim on
the page the model names, or the line is dropped with why; amounts are turned into tỷ đồng by the unit the document states. Nothing is saved."""

import json
import re

from investment_agent.ai.doc_ask import UNITS, Unverified, _digits, _numbers, _parse, _to_decimal, _user, select_passages

PART_WORDS = 2500
QUERIES = {
    "projects": "chi phí xây dựng cơ bản dở dang dự án công trình hoàn thành",
    "ranges": "thời gian khấu hao hữu dụng ước tính năm nhà cửa vật kiến trúc máy móc thiết bị phương tiện vận tải",
    "prepaid": "chi phí trả trước phân bổ trong năm công cụ dụng cụ sửa chữa lớn tiền thuê đất",
    "deals": "hợp nhất kinh doanh mua công ty con giá phí hợp nhất giá trị hợp lý tài sản thuần lợi thế thương mại",
    "interest": "chi phí đi vay được vốn hóa lãi vay vốn hóa",
    "incentives": "thuế thu nhập doanh nghiệp ưu đãi thuế suất miễn giảm",
}
GROUPS = ("buildings", "machinery", "vehicles", "office", "livestock", "other")
PREPAID_KINDS = ("tools", "overhaul", "land", "preop", "other", "total")
SYSTEM_NOTES = (
    "Bạn đọc thuyết minh báo cáo tài chính năm công khai của doanh nghiệp. Chỉ dựa trên các đoạn được cung cấp, liệt kê: "
    "projects: các dự án, công trình trong chi phí xây dựng cơ bản dở dang (name, cip_text là số dư chép nguyên văn, due_text là thời điểm dự kiến "
    "hoàn thành chép nguyên văn nếu có, không thì null); "
    "ranges: thời gian khấu hao theo nhóm tài sản cố định hữu hình, group là một trong buildings (nhà cửa, vật kiến trúc), machinery (máy móc, "
    "thiết bị), vehicles (phương tiện vận tải, truyền dẫn), office (thiết bị, dụng cụ quản lý), livestock (vật nuôi, cây lâu năm), other; from, to là "
    "số năm; "
    "prepaid: số phân bổ chi phí trả trước trong năm, kind là tools (công cụ dụng cụ), overhaul (sửa chữa lớn), land (tiền thuê đất, đền bù), preop "
    "(chi phí trước hoạt động), other, total; amount_text chép nguyên văn; "
    "deals: các thương vụ mua công ty con trong năm (name, date_text ngày mua dạng dd/mm/yyyy như trong tài liệu, share_text tỷ lệ mua, price_text "
    "giá mua, net_assets_text giá trị hợp lý tài sản thuần của công ty được mua, goodwill_text lợi thế thương mại hoặc lãi mua rẻ nếu có); "
    "capitalised_interest: chi phí đi vay được vốn hóa trong năm (amount_text) hoặc null; "
    "incentives: ưu đãi thuế TNDN của công ty con hay dự án (entity, kind là rate khi có thuế suất ưu đãi, exempt khi miễn thuế, half khi giảm 50%, "
    "rate_text thuế suất ưu đãi, until_text năm hết ưu đãi). "
    "Mỗi dòng ghi page là số trang của đoạn chứa số đó. Chép số đúng như trong đoạn, không tính toán, không ước lượng, không suy ra. Phần nào tài "
    "liệu không nêu thì để mảng rỗng. Ghi unit là đơn vị tính tài liệu dùng (đồng, nghìn đồng, triệu đồng, tỷ đồng). Trả về JSON: "
    '{"unit": "...", "projects": [], "ranges": [], "prepaid": [], "deals": [], "capitalised_interest": null, "incentives": []}.')
_QUARTER = re.compile(r"(?i)(?:quý|q)\s*([1-4])\D{0,12}(20\d{2})")
_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(20\d{2})$")


def notes_passages(pages: list[str]) -> list[tuple[int, str]]:
    """The chunks most about each part, at most PART_WORDS words a part, together and in page order."""
    seen, out = set(), []
    for query in QUERIES.values():
        for n, text in select_passages(pages, query, max_words=PART_WORDS):
            if (n, text) not in seen:
                seen.add((n, text))
                out.append((n, text))
    return sorted(out)


def notes_messages(symbol: str, year: str, passages: list[tuple[int, str]]) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_NOTES}, _user({"ticker": symbol, "year": year, "passages": [{"page": n, "text": t} for n, t in passages]})]


def _text(v) -> str:
    return " ".join(str(v or "").split())


def _plain(d) -> str:
    return format(d.normalize(), "f") if d else "0"


def check_notes(content: str | None, passages: list[tuple[int, str]], *, document_text: str) -> tuple[dict, list[dict]]:
    """The draft in the notes block's shape (amounts in tỷ đồng, each line with its page) and the lines dropped, with why."""
    data = _parse(content)
    unit = _text(data.get("unit")).casefold()
    doc = document_text.casefold()
    if unit not in UNITS or (unit not in doc and not (unit in ("đồng", "vnd") and ("vnd" in doc or "đồng" in doc))):
        raise Unverified("unit_not_stated")
    numbers, raw = {}, {}
    for n, t in passages:
        numbers.setdefault(n, set()).update(_numbers(t))
        raw[n] = raw.get(n, "") + " " + t.casefold()
    dropped: list[dict] = []

    def on_page(part: str, name: str, page, *texts) -> bool:
        if not isinstance(page, int) or page not in numbers:
            dropped.append({"part": part, "name": name, "reason": "page_not_sent"})
            return False
        if any(_digits(_text(t).replace(" ", "")) not in numbers[page] for t in texts):
            dropped.append({"part": part, "name": name, "reason": "number_not_on_page"})
            return False
        return True

    def amount(text) -> str | None:
        d = _to_decimal(_text(text))
        return None if d is None else _plain(d * UNITS[unit])

    def rows(key):
        v = data.get(key)
        return [r for r in v if isinstance(r, dict)] if isinstance(v, list) else []

    draft = {"projects": [], "ranges": {}, "prepaid": {}, "deals": [], "capitalised_interest": None, "incentives": []}
    for r in rows("projects"):
        name = _text(r.get("name"))
        if not name or not r.get("cip_text") or not on_page("projects", name, r.get("page"), r["cip_text"]):
            continue
        due_text = _text(r.get("due_text"))
        m = _QUARTER.search(due_text) if due_text and due_text.casefold() in raw[r["page"]] else None
        draft["projects"].append({"name": name, "cip_value": amount(r["cip_text"]), "due": f"Q{m.group(1)}/{m.group(2)}" if m else "",
                                  "due_text": due_text, "page": r["page"]})
    for r in rows("ranges"):
        group = r.get("group")
        if group not in GROUPS:
            continue
        try:
            low, high = int(r.get("from")), int(r.get("to"))
        except (TypeError, ValueError):
            dropped.append({"part": "ranges", "name": group, "reason": "number_not_on_page"})
            continue
        if 0 <= low <= high <= 100 and on_page("ranges", group, r.get("page"), str(low), str(high)):
            draft["ranges"][group] = {"from": low, "to": high, "page": r["page"]}
    for r in rows("prepaid"):
        kind = r.get("kind")
        if kind in PREPAID_KINDS and r.get("amount_text") and on_page("prepaid", kind, r.get("page"), r["amount_text"]):
            draft["prepaid"][kind] = {"amount": amount(r["amount_text"]), "page": r["page"]}
    for r in rows("deals"):
        name = _text(r.get("name"))
        texts = [r.get(k) for k in ("share_text", "price_text", "net_assets_text")]
        if not name or not all(texts):
            dropped.append({"part": "deals", "name": name, "reason": "missing_figure"})
            continue
        date = _DATE.match(_text(r.get("date_text")))
        if not date or _text(r["date_text"]) not in raw.get(r.get("page"), ""):
            dropped.append({"part": "deals", "name": name, "reason": "date_not_on_page"})
            continue
        goodwill = r.get("goodwill_text")
        if not on_page("deals", name, r.get("page"), *texts, *([goodwill] if goodwill else [])):
            continue
        share = _to_decimal(_text(r["share_text"]).replace("%", ""))
        draft["deals"].append({"name": name, "date": _text(r["date_text"]), "share": _plain(share) if share is not None else None,
                               "price": amount(r["price_text"]), "net_assets": amount(r["net_assets_text"]),
                               "note_goodwill": amount(goodwill) if goodwill else None, "page": r["page"]})
    ci = data.get("capitalised_interest")
    if isinstance(ci, dict) and ci.get("amount_text") and on_page("capitalised_interest", "", ci.get("page"), ci["amount_text"]):
        draft["capitalised_interest"] = {"amount": amount(ci["amount_text"]), "page": ci["page"]}
    for r in rows("incentives"):
        entity, kind = _text(r.get("entity")), r.get("kind")
        until = _text(r.get("until_text"))
        if not entity or kind not in ("rate", "exempt", "half") or not re.fullmatch(r"20\d{2}", until):
            dropped.append({"part": "incentives", "name": entity, "reason": "missing_figure"})
            continue
        rate = _text(r.get("rate_text")).replace("%", "") if kind == "rate" else ""
        if kind == "rate" and not rate:
            dropped.append({"part": "incentives", "name": entity, "reason": "missing_figure"})
            continue
        if on_page("incentives", entity, r.get("page"), until, *([rate] if rate else [])):
            draft["incentives"].append({"entity": entity, "kind": kind, "rate": rate or None, "until": until, "page": r["page"]})
    return draft, dropped
