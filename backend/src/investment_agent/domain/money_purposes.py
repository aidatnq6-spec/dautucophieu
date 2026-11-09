"""Mục đích từng khoản tiền: what the owner means each row of Sổ tài sản for, and what they count as already given away. Only reads the book, never changes it,
and Tháp tài sản does not see it. Personal data; never sent to a model."""

from collections import Counter
from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from .deposit_book import DepositBook, bond_values, gold_values
from .models import ContractModel

_ID = r"^[A-Za-z0-9_-]{1,64}$"


class Purpose(ContractModel):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=40, pattern=r"\S")
    given: bool  # xem như đã chi: no longer counted as the owner's own


class MoneyPurposes(ContractModel):
    purposes: tuple[Purpose, ...] = Field(default=(), max_length=20)
    tags: dict[str, str] = Field(default_factory=dict, max_length=400)  # row id of the book -> purpose id

    @model_validator(mode="after")
    def _consistent(self):
        known = {p.id for p in self.purposes}
        if any(n > 1 for n in Counter(p.id for p in self.purposes).values()):
            raise ValueError("purpose ids must be unique")
        if any(v not in known for v in self.tags.values()):
            raise ValueError("a tag must name a known purpose")
        return self


def book_rows(book: DepositBook, quotes: dict, *, today: date) -> list[dict]:
    """Every row of the book at the value the book gives it. at_cost: a bond, fund or gold row with no public price, so at what it cost."""
    rows = [{"id": a.id, "kind": "account", "name": a.name, "value": format(a.amount, "f"), "at_cost": False} for a in book.accounts]
    rows += [{"id": d.id, "kind": "deposit", "name": f"{d.bank}, đáo hạn {d.matures:%d/%m/%Y}", "value": format(d.principal, "f"), "at_cost": False} for d in book.deposits]
    bonds, gold = {x["id"]: x for x in bond_values(book, quotes.get("funds") or {}, today=today)}, {x["id"]: x for x in gold_values(book, quotes.get("gold") or {}, today=today)}
    rows += [{"id": b.id, "kind": "bond", "name": b.name, "value": bonds[b.id]["value"], "at_cost": bonds[b.id]["source"] != "nav"} for b in book.bonds]
    rows += [{"id": g.id, "kind": "gold", "name": g.name, "value": gold[g.id]["value"], "at_cost": gold[g.id]["source"] != "price"} for g in book.gold]
    rows += [{"id": c.id, "kind": "crypto", "name": c.name, "value": format(c.amount, "f"), "at_cost": False} for c in book.crypto]
    return rows


def purpose_view(rows: list[dict], data: MoneyPurposes) -> dict:
    """Per purpose and for rows with none; a tag on a row no longer in the book counts for nothing."""
    def add(chosen: list[dict]) -> tuple[Decimal, int]:
        return sum((Decimal(r["value"]) for r in chosen), Decimal(0)), len(chosen)
    purposes, given = [], Decimal(0)
    for p in data.purposes:
        amount, count = add([r for r in rows if data.tags.get(r["id"]) == p.id])
        purposes.append({"id": p.id, "name": p.name, "given": p.given, "total": format(amount, "f"), "count": count})
        given += amount if p.given else 0
    known = {p.id for p in data.purposes}
    free, free_count = add([r for r in rows if data.tags.get(r["id"]) not in known])
    total = add(rows)[0]
    return {"purposes": purposes, "unassigned": {"total": format(free, "f"), "count": free_count}, "total": format(total, "f"), "given_total": format(given, "f"), "mine_total": format(total - given, "f")}
