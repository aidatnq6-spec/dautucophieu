"""Kế hoạch giải ngân: the owner's tranches in the personal store (settings/buy_plans), the public inputs their conditions read, and
the after-close check that marks the newly met ones — only once the Telegram note went out, as Cảnh báo giá does."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.buy_plan import MAX_TRANCHES, PlanError, evaluate, render, validate
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.services.records import read_version

RECORD = ("settings", "buy_plans")


def read_plan(repo, owner) -> tuple[list[dict], int]:
    record = read_version(repo, owner, *RECORD, None)
    return (list(record.payload.get("tranches", [])), record.version) if record else ([], 0)


def public_inputs(data_dir: Path | None, symbols: set[str]) -> tuple[dict, dict]:
    """(latest stored daily close per symbol, thousand đồng, with its day; published quarters per symbol)."""
    if data_dir is None:
        return {}, {}
    series = SeriesStore(Path(data_dir) / "trend-sources")
    closes, quarters = {}, {}
    for s in symbols:
        points = series.points(f"{s}-1d")
        if points:
            closes[s] = (date.fromisoformat(points[-1][0][:10]), Decimal(points[-1][1]))
        found = set()
        for folder in ("statements", "statements-financial"):
            found |= set(((StatementStore(Path(data_dir) / folder).read(s) or {}).get("quarters") or {}))
        quarters[s] = found
    return closes, quarters


def merge(stored: list[dict], sent: list[dict]) -> list[dict]:
    """The tranches to keep, as sent: a new one waits; the owner may set an existing one to done, dropped or waiting again (which
    clears when it was met); a met one stays met until then."""
    if len(sent) > MAX_TRANCHES:
        raise PlanError("too_many", f"Tối đa {MAX_TRANCHES} đợt.")
    before = {t["id"]: t for t in stored}
    out, ids = [], set()
    for raw in sent:
        t = validate(raw)
        if t["id"] in ids:
            raise PlanError("duplicate", "Hai đợt trùng mã số.")
        ids.add(t["id"])
        old = before.get(t["id"])
        wanted = raw.get("status")
        status, met_on, met_value = ("waiting", None, None) if old is None else (old["status"], old["met_on"], old["met_value"])
        changed = old is not None and (old["kind"], old["value"], old["symbol"]) != (t["kind"], t["value"], t["symbol"])
        if wanted in ("done", "dropped") and old is not None:
            status = wanted
        elif (wanted == "waiting" and old is not None) or changed:
            status, met_on, met_value = "waiting", None, None
        out.append({**t, "status": status, "met_on": met_on, "met_value": met_value})
    return out


def check_plan(repo, owner, data_dir, *, send, today: date, request_id: str) -> dict:
    tranches, version = read_plan(repo, owner)
    waiting = {t["symbol"] for t in tranches if t["status"] == "waiting"}
    if not waiting:
        return {"status": "ok", "met": 0, "sent": False, "waiting": 0}
    closes, quarters = public_inputs(data_dir, waiting)
    updated, met = evaluate(tranches, closes=closes, quarters=quarters, today=today)
    if not met:
        return {"status": "ok", "met": 0, "sent": False, "waiting": len(waiting)}
    if not send(render(met)):
        return {"status": "ok", "met": len(met), "sent": False, "waiting": len(waiting)}
    repo.write(owner, *RECORD, {"tranches": updated}, expected_version=version, request_id=request_id)
    return {"status": "ok", "met": len(met), "sent": True, "waiting": len(waiting)}
