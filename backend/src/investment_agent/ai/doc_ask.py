"""Hỏi AI về tài liệu công khai (C5): the pure part, run on this machine before and after a model call.

What may go out: the ticker of the page, a question that passed screen_question, and passages of one public document chosen by
keyword here. Nothing personal: the question is refused when it carries an amount, words about the owner ("tôi", "danh mục",
"đang nắm" …), the name of one of the owner's own rows (matched here, never sent) or another ticker.

What may come back is checked against what was sent: an answer must cite pages it was given and quote no number absent from them;
a proposed row of Phải thu bên liên quan keeps its amount only when the figure is printed on its page, in the unit the document
states. Nothing is filled in.
"""

import json
import re
from decimal import Decimal, InvalidOperation

MAX_QUESTION = 300
CHUNK_WORDS = 600
_UNIT_AMOUNT = re.compile(r"(?i)\d[\d.,]*\s*(?:đ|đồng|nghìn|ngàn|triệu|tỷ|usd|vnd)\b")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
_PERSONAL = re.compile(r"(?i)\b(?:tôi|mình|của tôi|danh mục|đang nắm|đang giữ|giá vốn|lãi lỗ|tài khoản|sổ tiết kiệm)\b")
_TICKER = re.compile(r"\b[A-Z][A-Z0-9]{2}\b")
_STOP = {"của", "và", "là", "có", "không", "gì", "nào", "thế", "về", "trong", "các", "những", "được", "cho", "với", "này", "như"}
UNITS = {"đồng": Decimal("1e-9"), "vnd": Decimal("1e-9"), "nghìn đồng": Decimal("1e-6"), "triệu đồng": Decimal("1e-3"), "tỷ đồng": Decimal(1)}

SYSTEM_QA = ("Bạn đọc một tài liệu công khai của doanh nghiệp niêm yết. Trả lời câu hỏi chỉ dựa trên các đoạn được cung cấp, "
             "bằng tiếng Việt, ngắn gọn. Ghi số trang đã dùng. Chép số đúng như trong đoạn, không tính toán, không ước lượng, không suy ra số "
             "mới. Nếu các đoạn không trả lời được thì nói rõ là tài liệu không nêu. Không đưa khuyến nghị mua bán. "
             'Trả về JSON: {"answer": "...", "pages": [số trang]}.')
SYSTEM_RR = ("Bạn đọc thuyết minh báo cáo tài chính công khai của doanh nghiệp. Liệt kê, chỉ dựa trên các đoạn được cung cấp: các khoản phải thu "
             "từ bên liên quan (công ty liên kết, công ty cùng lãnh đạo, cá nhân liên quan…), và các nhà cung cấp được nêu tên trong thuyết minh trả "
             "trước cho người bán (kể cả khi không phải bên liên quan, khi đó related=false). Với mỗi khoản: kind là loại khoản (customer: phải thu "
             "khách hàng, prepay: trả trước cho người bán, other: phải thu khác, loan: cho vay; null nếu không rõ), tên đối tượng "
             "như trong tài liệu (hoặc tên dòng gộp như 'Bên liên quan khác'), số dư chép nguyên văn như trong tài liệu (amount_text), số trang, "
             "grouped=true nếu là dòng gộp không nêu tên, secured và interest chỉ điền true/false khi tài liệu nói rõ (không thì null), "
             "collect_within là thời hạn thu hồi nếu tài liệu nói rõ (không thì null), rate là lãi suất chép nguyên văn nếu có (không thì null), "
             "accrued_interest_text là lãi cho vay phải thu của khoản đó chép nguyên văn nếu thuyết minh nêu (không thì null). Ghi đơn vị tính tài liệu dùng (đồng, nghìn đồng, triệu đồng, "
             "tỷ đồng). Không tính toán, không ước lượng. Trả về JSON: "
             '{"unit": "...", "rows": [{"name": "...", "kind": null, "amount_text": "...", "page": 0, "related": true, "grouped": false, '
             '"secured": null, "interest": null, "collect_within": null, "rate": null, "accrued_interest_text": null}]}.')
KINDS = ("customer", "prepay", "other", "loan")


class Blocked(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class Unverified(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _digits(token: str) -> str:
    return re.sub(r"[.,]", "", token)


def screen_question(question: str, *, symbol: str, personal_names: set[str], tickers: set[str]) -> str:
    q = (question or "").strip()
    if not q:
        raise Blocked("empty")
    if len(q) > MAX_QUESTION:
        raise Blocked("too_long")
    if _UNIT_AMOUNT.search(q) or any(len(d) >= 4 and not (len(d) == 4 and 1990 <= int(d) <= 2039) for d in map(_digits, _NUMBER.findall(q))):
        raise Blocked("amount")
    if _PERSONAL.search(q):
        raise Blocked("personal")
    low = q.casefold()
    if any(len(n.strip()) >= 3 and n.strip().casefold() in low for n in personal_names):
        raise Blocked("personal_name")
    if any(t in tickers and t != symbol for t in _TICKER.findall(q)):
        raise Blocked("other_ticker")
    return q


def _terms(text: str) -> list[str]:
    return [w for w in re.findall(r"\w+", text.casefold()) if len(w) >= 2 and w not in _STOP and not w.isdigit()]


def select_passages(pages: list[str], query: str, *, max_words: int = 12000) -> list[tuple[int, str]]:
    """(1-based page, text) of the chunks most about the query, within max_words, set back in page order."""
    terms = set(_terms(query))
    chunks = []
    for n, page in enumerate(pages, start=1):
        words = page.split()
        for i in range(0, len(words), CHUNK_WORDS):
            text = " ".join(words[i:i + CHUNK_WORDS])
            low = text.casefold()
            score = sum(low.count(t) for t in terms)
            if score:
                chunks.append((score, n, i, text))
    picked, used = [], 0
    for score, n, i, text in sorted(chunks, key=lambda c: (-c[0], c[1], c[2])):
        size = len(text.split())
        if used + size > max_words:
            continue
        picked.append((n, i, text))
        used += size
    return [(n, text) for n, _, text in sorted(picked)]


def _user(payload: dict) -> dict:
    return {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}


def qa_messages(symbol: str, question: str, passages: list[tuple[int, str]]) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_QA},
            _user({"ticker": symbol, "question": question, "passages": [{"page": n, "text": t} for n, t in passages]})]


def rr_messages(symbol: str, year: str, passages: list[tuple[int, str]]) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_RR},
            _user({"ticker": symbol, "year": year, "passages": [{"page": n, "text": t} for n, t in passages]})]


def _parse(content: str | None) -> dict:
    try:
        data = json.loads(content or "")
    except (TypeError, ValueError):
        raise Unverified("not_json") from None
    if not isinstance(data, dict):
        raise Unverified("not_json")
    return data


def _numbers(text: str) -> set[str]:
    return {_digits(t) for t in _NUMBER.findall(text)}


def check_answer(content: str | None, passages: list[tuple[int, str]]) -> dict:
    data = _parse(content)
    answer, pages = data.get("answer"), data.get("pages")
    sent = {n for n, _ in passages}
    if not isinstance(answer, str) or not answer.strip() or not isinstance(pages, list) or not pages:
        raise Unverified("shape")
    if any(not isinstance(p, int) or p not in sent for p in pages):
        raise Unverified("page_not_sent")
    known = set().union(*(_numbers(t) for _, t in passages)) if passages else set()
    if any(len(d) >= 3 and d not in known for d in map(_digits, _NUMBER.findall(answer))):
        raise Unverified("number_not_in_passages")
    return {"answer": answer.strip(), "pages": sorted(set(pages))}


def _to_decimal(text: str) -> Decimal | None:
    t = text.strip().replace(" ", "")
    if re.search(r",\d{1,2}$", t):
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(".", "").replace(",", "")
    try:
        d = Decimal(t)
    except InvalidOperation:
        return None
    return d if d.is_finite() and d >= 0 else None


def check_rows(content: str | None, passages: list[tuple[int, str]], *, document_text: str) -> tuple[list[dict], list[dict]]:
    """Rows in Phải thu bên liên quan's shape, amounts in tỷ đồng, each with its page; and the rows dropped, with why."""
    data = _parse(content)
    unit = str(data.get("unit") or "").strip().casefold()
    doc = document_text.casefold()
    if unit not in UNITS or (unit not in doc and not (unit in ("đồng", "vnd") and ("vnd" in doc or "đồng" in doc))):
        raise Unverified("unit_not_stated")
    if not isinstance(data.get("rows"), list):
        raise Unverified("shape")
    by_page = {}
    for n, t in passages:
        by_page.setdefault(n, set()).update(_numbers(t))
    rows, dropped = [], []
    for r in data["rows"]:
        if not isinstance(r, dict):
            continue
        name = " ".join(str(r.get("name") or "").split())
        text, page = str(r.get("amount_text") or ""), r.get("page")
        if not name:
            dropped.append({"name": "", "reason": "no_name"})
            continue
        if not isinstance(page, int) or page not in by_page:
            dropped.append({"name": name, "reason": "page_not_sent"})
            continue
        amount = _to_decimal(text)
        if amount is None or _digits(text.strip().replace(" ", "")) not in by_page[page]:
            dropped.append({"name": name, "reason": "amount_not_on_page"})
            continue
        ty = (amount * UNITS[unit]).normalize()
        accrued_text, accrued = str(r.get("accrued_interest_text") or "").strip(), None
        if accrued_text:
            value = _to_decimal(accrued_text)
            if value is not None and _digits(accrued_text.replace(" ", "")) in by_page[page]:
                accrued = (value * UNITS[unit]).normalize()
            else:
                dropped.append({"name": name, "reason": "interest_not_on_page"})
        tri = lambda v: v if v in (True, False) else None  # noqa: E731
        rows.append({"name": name, "amount": format(ty, "f") if ty != 0 else "0", "grouped": r.get("grouped") is True,
                     "related": r.get("related") is not False, "secured": tri(r.get("secured")), "interest": tri(r.get("interest")),
                     "collect_within": (" ".join(str(r.get("collect_within")).split())[:60] or None) if r.get("collect_within") else None,
                     "kind": r.get("kind") if r.get("kind") in KINDS else None,
                     "rate": (" ".join(str(r.get("rate")).split())[:60] or None) if r.get("rate") else None,
                     "accrued_interest": (format(accrued, "f") if accrued != 0 else "0") if accrued is not None else None, "page": page})
    return rows, dropped
