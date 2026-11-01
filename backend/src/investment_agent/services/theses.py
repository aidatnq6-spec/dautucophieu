"""Luận điểm đầu tư in the owner's personal store (`settings/theses`): saving, editing and holding on (each hold also written to the
Nhật ký), the facts each check reads from stored data, and the Telegram note when a condition breaks.

Personal data: stays on the owner's machine and in their Firestore; nothing here is ever sent to a model. The note gives the
owner's own condition and words, a scenario from the ticker's stored history (never a forecast), and never says to sell."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from investment_agent.api.routes.value_chains import chain_labels
from investment_agent.domain.journal import JournalEntry
from investment_agent.domain.ledger import replay
from investment_agent.domain.thesis import (KINDS, REASON_VI, ThesisError, advance, describe, edit_thesis, evaluate, hold_condition, mark_sent, new_thesis,
                                            scenario, similar, validate_thesis)
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.view import EmptyMarket
from investment_agent.notifications.render import _num, vnd
from investment_agent.services.drawdown import held_costs
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.services.journal import append_entry
from investment_agent.services.records import LedgerBook, read_version

COLLECTION, RECORD = "settings", "theses"  # the personal store allows a fixed set of collections; settings holds price alerts too
EMOTIONS = ("calm", "excited", "fomo", "anxious", "panic", "regret")


def read_theses(repo, owner) -> tuple[list[dict], int]:
    """Theses oldest first and the record version; raises RepositoryUnavailable."""
    record = read_version(repo, owner, COLLECTION, RECORD, None)
    return (list(record.payload.get("theses", [])), record.version) if record else ([], 0)


def _write(repo, owner, theses: list[dict], expected_version: int, request_id: str) -> int:
    return repo.write(owner, COLLECTION, RECORD, {"theses": theses}, expected_version=expected_version, request_id=request_id).version


def company_of(data_dir: Path, symbol: str) -> str | None:
    """financial (banks, securities firms, insurers), other, or None when the sector is unknown."""
    sector = load_sectors(Path(data_dir))[0].get(symbol)
    return None if sector is None else "financial" if kind_of(sector) else "other"


def facts_for(data_dir: Path, symbol: str, *, cost: Decimal | None, row: dict | None, chains: list | None, deals: list | None,
              live: Decimal | None = None) -> dict:
    """What the conditions read for one ticker, from stored data: closes (thousand đồng, given here in đồng), the reference valuation
    row, quarterly profit, chain labels and insider notices. `live` is the board's price during the session."""
    daily = SeriesStore(Path(data_dir) / "trend-sources").read(f"{symbol}-1d")
    close = Decimal(str(daily[-1][1])) * 1000 if daily else None
    quality = (row or {}).get("quality") or {}
    record = FundamentalsStore(Path(data_dir) / "fundamentals").read(symbol) or {}
    quarters = {q: Decimal(f["npat"]) for q, f in record.get("quarters", {}).items() if f.get("npat") is not None and "-Q" in q}
    return {"price": live if live is not None else close, "close": close, "cost": cost, "fair": Decimal(row["fair"]) if row and row.get("fair") else None,
            "quality": quality.get("f_score"), "quality_reason": quality.get("reason"), "quarters": quarters,
            "daily": [(t.date(), v) for t, v in daily], "points": daily, "chains": chains, "insider_deals": deals}


def position_shares(repo, owner) -> dict[str, int]:
    """Shares held per ticker (settled and pending); raises RepositoryUnavailable."""
    state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    return {p.security_id: int(p.quantity + p.pending_quantity) for p in state.positions if p.quantity + p.pending_quantity > 0}


def gather(data_dir: Path, repo, owner, symbols: list[str], *, scope: str, today: date, market=None, live: dict | None = None,
           insider=None) -> dict[str, dict]:
    """Facts for the tickers of open theses. "price" reads closes, costs and the live price only; "data" adds the reference
    valuation, chain labels and, through `insider(symbol)`, insider notices. A source that fails leaves its facts missing."""
    costs = {s: Decimal(c) for s, c in held_costs(repo, owner).items()}
    rows, chains = {}, {}
    if scope == "data":
        try:
            rows = {r["symbol"]: r for r in fair_value_board(Path(data_dir), market or EmptyMarket(), repo, owner, held=set(symbols),
                                                             today=today)["rows"]}
        except (OSError, ValueError, KeyError):
            rows = {}
        try:
            chains = chain_labels(Path(data_dir), today=today)
        except (OSError, ValueError):
            chains = None
    out = {}
    for s in symbols:
        deals = None
        if insider is not None:
            got = insider(s)
            deals = None if got is None or got.get("reason") else got.get("deals")
        out[s] = facts_for(data_dir, s, cost=costs.get(s), row=rows.get(s), chains=None if chains is None else chains.get(s, []), deals=deals,
                           live=(live or {}).get(s))
    return out


def _snapshot(facts: dict) -> dict:
    s = lambda v: None if v is None else format(v.normalize(), "f")  # noqa: E731
    return {"price": s(facts.get("price")), "cost": s(facts.get("cost")), "fair": s(facts.get("fair")),
            "f_score": (facts.get("quality") or {}).get("score")}


def _open(theses: list[dict], **match) -> dict | None:
    return next((t for t in theses if t["closed_on"] is None and all(t[k] == v for k, v in match.items())), None)


def _reasons(reasons: list[str]) -> str:
    return ", ".join(REASON_VI[r] for r in reasons)


def save(repo, owner, *, symbol: str, raw: dict, company: str | None, facts: dict, today: date, expected_version: int, request_id: str,
         held: set[str]) -> tuple[list[dict], int]:
    """A new thesis for a held ticker without an open one; the reasons and words also go to the Nhật ký as a buy entry."""
    theses, _ = read_theses(repo, owner)
    if symbol not in held:
        raise ThesisError("not_held", "Chỉ đặt luận điểm cho mã đang nắm trong sổ giao dịch.")
    if _open(theses, symbol=symbol):
        raise ThesisError("thesis_exists", "Mã này đã có luận điểm; hãy sửa luận điểm đó.")
    thesis = new_thesis(symbol, validate_thesis(raw, company=company), today=today, snapshot=_snapshot(facts))
    version = _write(repo, owner, [*theses, thesis], expected_version, request_id)
    append_entry(repo, owner, JournalEntry(entry_id=f"thesis-{thesis['id']}", symbol=symbol, kind="buy", created_on=today,
                                           reason=f"Luận điểm — lý do mua: {_reasons(thesis['reasons'])}. {thesis['note']}".strip(),
                                           emotion="fomo" if "fomo" in thesis["reasons"] else None,
                                           context={"price": thesis["snapshot"]["price"]}), request_id=f"{request_id}-journal")
    return [*theses, thesis], version


def edit(repo, owner, *, thesis_id: str, raw: dict, company: str | None, fair: str | None, today: date, expected_version: int,
         request_id: str) -> tuple[list[dict], int]:
    theses, _ = read_theses(repo, owner)
    found = _open(theses, id=thesis_id)
    if found is None:
        raise ThesisError("thesis_not_found", "Không tìm thấy luận điểm này; hãy tải lại.")
    changed = edit_thesis(found, raw, company=company, today=today, fair=fair)
    theses = [changed if t is found else t for t in theses]
    return theses, _write(repo, owner, theses, expected_version, request_id)


def hold(repo, owner, *, thesis_id: str, cond_id: str, reason: str, emotion: str | None, until: date | None, new_condition: dict | None,
         company: str | None, fair: str | None, today: date, expected_version: int, request_id: str) -> tuple[list[dict], int]:
    """Giữ tiếp, có lý do: the reason goes to the Nhật ký as a hold entry, linked from the thesis history."""
    theses, _ = read_theses(repo, owner)
    found = _open(theses, id=thesis_id)
    if found is None:
        raise ThesisError("thesis_not_found", "Không tìm thấy luận điểm này; hãy tải lại.")
    if emotion is not None and emotion not in EMOTIONS:
        raise ThesisError("invalid_emotion", "Cảm xúc không hợp lệ.")
    entry_id = f"hold-{uuid.uuid4().hex[:12]}"
    changed = hold_condition(found, cond_id, reason=reason, until=until, new_condition=new_condition, today=today, entry_id=entry_id,
                             company=company, fair=fair)
    cond = next(c for c in found["conditions"] if c["id"] == cond_id)
    theses = [changed if t is found else t for t in theses]
    version = _write(repo, owner, theses, expected_version, request_id)
    append_entry(repo, owner, JournalEntry(entry_id=entry_id, symbol=found["symbol"], kind="hold", created_on=today, emotion=emotion,
                                           reason=f"Giữ tiếp khi “{KINDS[cond['kind']][0]}” bị phá: {reason.strip()}",
                                           context={"price": cond["broken_price"]}), request_id=f"{request_id}-journal")
    return theses, version


def _title(symbol: str, cond: dict) -> str:
    return f"{symbol} — {describe(cond)}"


def _dm(iso: str) -> str:
    return "/".join(reversed(iso.split("-")))


def _first(thesis: dict, cond: dict, facts: dict, shares: int | None, lesson: str | None) -> list[str]:
    lines = [_title(thesis["symbol"], cond),
             f"• Vì sao cần xem lại: {cond['broken_reading'] or cond['current']}. Lý do mua: {_reasons(thesis['reasons'])}."]
    if thesis["note"]:
        lines.append(f"  Bạn đã viết lúc đặt ({_dm(thesis['created_on'])}): “{thesis['note']}”")
    lines.append("• Nếu giữ tiếp — kịch bản từ lịch sử, không phải dự báo:")
    points = facts.get("points") or []
    deep = scenario(points, price=facts.get("price"), shares=shares or 0)
    if deep is None:
        lines.append("  Chưa có lịch sử giá đã lưu để tính.")
    else:
        loss = f"; nếu lặp lại từ giá hiện tại, vị thế hiện tại lỗ thêm {vnd(deep['loss'])}" if deep["loss"] and shares else ""
        lines.append(f"  Đợt giảm sâu nhất từng có {_num(Decimal(deep['depth']) * 100, 1)}% ({_dm(deep['peak'])} → {_dm(deep['trough'])}){loss}.")
    seen = similar(points, cond["kind"], cond.get("params", {}))
    if seen is not None:
        lines.append(f"  Những lần trước mã này rơi vào điều kiện tương tự: " + (
            f"6 tháng sau giá thay đổi trung vị {_num(Decimal(seen['median']) * 100, 1, sign=True)}% ({seen['count']} lần)."
            if seen["median"] is not None else f"chưa đủ lần để thống kê ({seen['count']} lần)."))
    if lesson:
        lines.append(f"• Bài học của chính bạn: {lesson}")
    return lines


def _step(thesis: dict, cond: dict, facts: dict, level: int) -> list[str]:
    price = facts.get("price")
    now = f"{_num(price / 1000, 2)}" if price is not None else "—"
    return [_title(thesis["symbol"], cond),
            f"• Giá đã giảm thêm hơn {level * 5}% kể từ lần báo đầu ({_dm(cond['broken_on'])}: {_num(Decimal(cond['broken_price']) / 1000, 2)} → {now}). "
            "Điều kiện vẫn bị phá."]


def _review(thesis: dict, cond: dict) -> list[str]:
    hold = cond["hold"]
    return [_title(thesis["symbol"], cond),
            f"• Đến ngày xem lại ({_dm(hold['until'])}) bạn đặt khi giữ tiếp: “{hold['reason']}”. Điều kiện vẫn bị phá: {cond['current'] or cond['broken_reading']}."]


def render(blocks: list[list[str]], now: datetime) -> str:
    body = "\n\n".join("\n".join(b) for b in blocks)
    return (f"Luận điểm đầu tư · {now.strftime('%H:%M %d/%m')}\n{body}\n\n"
            "Quyết định giữ hay bán là của bạn; trang Danh mục có nút “Giữ tiếp, có lý do”. Giá cổ phiếu tính bằng nghìn đồng.\n"
            "Không phải khuyến nghị. Phần mềm không đặt lệnh.")


def thesis_check_run(repo, owner, data_dir: Path, *, scope: str, facts: dict[str, dict], shares: dict[str, int], held: set[str], send,
                     now: datetime, today: date, request_id: str, lesson=None) -> dict:
    """One check: close theses of tickers no longer held, evaluate the conditions of `scope` ("price": during the session; "data":
    all of them, after the close), send one note for what is due, and record it as sent only when the note went out."""
    theses, version = read_theses(repo, owner)
    closed, events_all, blocks, out = 0, [], [], []
    for t in theses:
        if t["closed_on"] is None and t["symbol"] not in held:
            t = {**t, "closed_on": today.isoformat()}
            closed += 1
        if t["closed_on"] is not None or t["symbol"] not in facts:
            out.append(t)
            continue
        f = facts[t["symbol"]]
        results = {c["id"]: evaluate(c, f) for c in t["conditions"] if scope == "data" or KINDS[c["kind"]][2] == "price"}
        t, events = advance(t, results, today=today, price=f.get("price"))
        for e in events:
            c = e["condition"]
            blocks.append(_first(t, c, f, shares.get(t["symbol"]), lesson(t, c) if lesson else None) if e["type"] == "first"
                          else _step(t, c, f, e["level"]) if e["type"] == "step" else _review(t, c))
        events_all.append((len(out), events))
        out.append(t)
    sent = bool(blocks) and send(render(blocks, now))
    if sent:
        for i, events in events_all:
            out[i] = mark_sent(out[i], events)
    if out != theses:
        _write(repo, owner, out, version, request_id)
    return {"status": "ok", "open": sum(t["closed_on"] is None for t in out), "closed": closed, "events": len(blocks), "sent": sent}
