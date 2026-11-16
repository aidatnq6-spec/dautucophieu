"""Sổ phải thu bên liên quan: what the owner copies from a company's notes each year (who owes it, how much, related or not,
secured, interest-bearing, the term promised for collection), set side by side so that what a later year stops naming shows.

Findings, year against the year entered before it: a related party named one year and no longer named the next ("vanished", with the
largest related group line at least half its size, where it may now sit); a balance promised within a term and at least half of it
still owed a year on ("not_collected"); and, in the latest year, related balances neither secured nor bearing interest
("unsecured_free"). Amounts in tỷ đồng as typed from the notes; nothing is filled in. Public company figures the owner entered."""

from decimal import Decimal, InvalidOperation

MAX_ROWS, NAME_MAX, TERM_MAX, SOURCE_MAX = 40, 120, 60, 300
# which receivable a row is: phải thu khách hàng, trả trước cho người bán, phải thu khác, cho vay; None for rows saved before kinds
KINDS = ("customer", "prepay", "other", "loan")


class RelatedError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _key(name: str) -> str:
    return " ".join(name.split()).casefold()


def _amount(raw) -> str | None:
    text = str(raw or "").strip().replace(" ", "").replace(".", "").replace(",", ".")
    try:
        d = Decimal(text)
    except InvalidOperation:
        return None
    return format(d.normalize(), "f") if d.is_finite() and d >= 0 else None


def validate_year(source: str, rows: list[dict]) -> dict:
    source = (source or "").strip()
    if len(source) < 3 or len(source) > SOURCE_MAX:
        raise RelatedError("invalid_source", "Ghi nguồn của năm này (ví dụ: BCTC hợp nhất 2020, thuyết minh 38, kèm link nếu có).")
    if not rows:
        raise RelatedError("no_rows", "Nhập ít nhất một khoản phải thu.")
    if len(rows) > MAX_ROWS:
        raise RelatedError("too_many_rows", f"Tối đa {MAX_ROWS} dòng mỗi năm.")
    out, seen = [], set()
    for i, r in enumerate(rows, start=1):
        name, amount = " ".join(str(r.get("name") or "").split()), _amount(r.get("amount"))
        term = " ".join(str(r.get("collect_within") or "").split()) or None
        flags = [r.get(k) for k in ("secured", "interest")]
        kind = r.get("kind") or None
        if not name or len(name) > NAME_MAX or amount is None or (term and len(term) > TERM_MAX) or kind not in (None, *KINDS) \
                or not isinstance(r.get("grouped"), bool) or not isinstance(r.get("related"), bool) or any(f not in (True, False, None) for f in flags):
            raise RelatedError("invalid_row", f"Dòng {i}: cần tên đối tượng và số dư (tỷ đồng, không âm).")
        if _key(name) in seen:
            raise RelatedError("duplicate_name", f"Dòng {i}: {name} đã có trong năm này.")
        seen.add(_key(name))
        out.append({"name": name, "amount": amount, "grouped": r["grouped"], "related": r["related"], "secured": flags[0], "interest": flags[1],
                    "collect_within": term, "kind": kind})
    return {"source": source, "rows": out}


def _s(d: Decimal) -> str:
    return format(d.normalize(), "f") if d != 0 else "0"


def review(years: dict[str, dict]) -> dict:
    order = sorted(years)
    findings = []
    for before_y, y in zip(order, order[1:]):
        before, now = years[before_y]["rows"], years[y]["rows"]
        named_now = {_key(r["name"]): r for r in now}
        groups = sorted((r for r in now if r["grouped"]), key=lambda r: -Decimal(r["amount"]))
        for r in before:
            amount, key, kind = Decimal(r["amount"]), _key(r["name"]), r.get("kind")
            # a related party, or a supplier named in the notes because it holds 10% or more of the prepayments
            if (r["related"] or kind == "prepay") and not r["grouped"] and amount > 0 and key not in named_now:
                fits = [g for g in groups if (r["related"] and g["related"]) or (kind and g.get("kind") == kind)]
                group = next((g for g in fits if Decimal(g["amount"]) * 2 >= amount), None)
                findings.append({"kind": "vanished", "year": y, "from_year": before_y, "name": r["name"].strip(), "amount": r["amount"],
                                 "row_kind": kind, "group": {"name": group["name"], "amount": group["amount"]} if group else None})
            if r["collect_within"] and key in named_now and amount > 0 and Decimal(named_now[key]["amount"]) * 2 >= amount:
                findings.append({"kind": "not_collected", "year": y, "name": r["name"].strip(), "before": r["amount"], "now": named_now[key]["amount"],
                                 "promised": r["collect_within"]})
    if order:
        latest = order[-1]
        findings += [{"kind": "unsecured_free", "year": latest, "name": r["name"].strip(), "amount": r["amount"]}
                     for r in years[latest]["rows"] if r["related"] and r["secured"] is False and r["interest"] is False]
    view = []
    for y in reversed(order):
        rows = years[y]["rows"]
        related = [Decimal(r["amount"]) for r in rows if r["related"]]
        named = [Decimal(r["amount"]) for r in rows if r["related"] and not r["grouped"]]
        view.append({"year": y, "source": years[y]["source"], "rows": rows, "related_total": _s(sum(related, Decimal(0))),
                     "named_related": _s(sum(named, Decimal(0)))})
    return {"years": view, "findings": findings}
