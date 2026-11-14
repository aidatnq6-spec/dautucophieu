"""Bản đồ danh mục: every asset the owner holds as a tile sized by its value, grouped by layer (cổ phiếu, quỹ và trái phiếu, tiền
gửi, tiền mặt, vàng, tiền số), with its gain on cost where a market price gives one (stocks at the latest close, funds at NAV, gold at
the buying price). A stock without a price is left out and named, not drawn at cost; a fund or gold row without a price is at what
it cost, as Sổ tài sản counts it, and says so. Property is not included."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .deposit_book import DepositBook, bond_values, gold_values

LAYERS = {"stocks": "Cổ phiếu", "funds": "Quỹ và trái phiếu", "deposits": "Tiền gửi", "cash": "Tiền mặt", "gold": "Vàng", "crypto": "Tiền số"}
KIND = {"STOCK": "Quỹ cổ phiếu", "BALANCED": "Quỹ cân bằng", "BOND": "Trái phiếu"}


def _s(value: Decimal) -> str:
    return format(value.normalize(), "f") if value != 0 else "0"


def _change(value: Decimal, cost: Decimal) -> str | None:
    return _s(((value - cost) / cost).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if cost > 0 else None


def bank_key(name: str) -> str:
    """The bank a sổ belongs to, from the name typed for it: "NCB ·0990" and "SHB gửi góp ·795" are NCB and SHB — the trailing
    "·number" dropped, then the leading upper-case code when there is one; a name like "Ngân hàng A" stays whole."""
    import re
    base = re.sub(r"\s*[·•.#-]?\s*\d+\s*$", "", name.strip()) or name.strip()
    code = re.match(r"^([A-ZĐ0-9]{2,10})\b", base)
    return code.group(1) if code else base


def asset_map(holdings: list[dict], *, ledger_cash: str, book: DepositBook | None, navs: dict, profiles: dict, gold: dict,
              sectors: dict[str, str], today: date) -> dict:
    book = book or DepositBook()
    groups: dict[str, list[dict]] = {k: [] for k in LAYERS}
    unpriced = []
    for h in holdings:
        if h.get("market_value") is None:
            unpriced.append(h["security_id"])
            continue
        value = Decimal(h["market_value"])
        groups["stocks"].append({"id": f"stock:{h['security_id']}", "label": h["security_id"], "note": sectors.get(h["security_id"]),
                                 "value": _s(value), "change": _change(value, Decimal(h["total_cost"]))})
    for row, b in zip(bond_values(book, navs, today=today), book.bonds):
        value = Decimal(row["value"])
        kind = KIND.get((profiles.get(b.fund) or {}).get("kind")) if b.fund else None
        note = "chưa có NAV, theo vốn" if row["source"] == "no_nav" else kind if b.fund else "theo vốn"
        groups["funds"].append({"id": f"bond:{b.id}", "label": b.fund or b.name, "note": note, "value": _s(value),
                                "change": _change(value, b.amount) if row["source"] == "nav" else None})
    banks: dict[str, list] = {}
    for d in book.deposits:  # one tile per bank: a dozen equal sổ of one bank read as one block, not a dozen
        banks.setdefault(bank_key(d.bank), []).append(d)
    for bank, ds in banks.items():
        first = min(d.matures for d in ds)
        note = f"{len(ds)} sổ · sớm nhất đến hạn {first:%d/%m/%Y}" if len(ds) > 1 else f"đến hạn {first:%d/%m/%Y}"
        groups["deposits"].append({"id": f"bank:{bank}", "label": bank, "note": note, "value": _s(sum((d.principal for d in ds), Decimal(0))), "change": None})
    if Decimal(ledger_cash) > 0:
        groups["cash"].append({"id": "cash:ledger", "label": "Tài khoản chứng khoán", "note": None, "value": _s(Decimal(ledger_cash)), "change": None})
    for a in book.accounts:
        groups["cash"].append({"id": f"account:{a.id}", "label": a.name, "note": None, "value": _s(a.amount), "change": None})
    for row, g in zip(gold_values(book, gold, today=today), book.gold):
        value = Decimal(row["value"])
        groups["gold"].append({"id": f"gold:{g.id}", "label": g.name, "note": g.kind if row["source"] == "price" else "theo vốn", "value": _s(value),
                               "change": _change(value, g.amount) if row["source"] == "price" else None})
    for c in book.crypto:
        groups["crypto"].append({"id": f"crypto:{c.id}", "label": c.name, "note": "theo số đã nhập", "value": _s(c.amount), "change": None})
    out = []
    for key, tiles in groups.items():
        tiles = [t for t in tiles if Decimal(t["value"]) > 0]
        if tiles:
            tiles.sort(key=lambda t: -Decimal(t["value"]))
            out.append({"id": key, "label": LAYERS[key], "value": _s(sum((Decimal(t["value"]) for t in tiles), Decimal(0))), "tiles": tiles})
    out.sort(key=lambda g: -Decimal(g["value"]))
    return {"groups": out, "total": _s(sum((Decimal(g["value"]) for g in out), Decimal(0))), "unpriced": sorted(unpriced)}
