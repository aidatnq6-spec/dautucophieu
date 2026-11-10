"""Mùa báo cáo: the season view over the watched tickers' stored statements (public), with the owner's plans, quarter forecasts and the reviews
they record after a held ticker reports (`settings/thesis_reviews`). Holdings only mark rows; nothing here is sent to a model."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.annual_plans import plan_progress
from investment_agent.domain.earnings_season import cash_rows, sector_table, season_rows, target_quarter
from investment_agent.domain.quarter_forecast import forecast_quarter
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.plans_cafef import PlanStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import prefetch
from investment_agent.services.drawdown import held_costs
from investment_agent.services.records import read_version

REVIEWS = ("settings", "thesis_reviews")
VERDICTS = {"keep": "Giữ luận điểm", "watch": "Theo dõi thêm", "revisit": "Xem lại luận điểm"}


def statement_records(data_dir: Path, symbols, sectors: dict) -> tuple[dict[str, dict], set[str]]:
    """symbol → quarters, and the symbols on the non-financial layout (which carry cash flow)."""
    records, plain = {}, set()
    for s in symbols:
        folder = "statements" if kind_of(sectors.get(s)) is None else "statements-financial"
        rec = StatementStore(Path(data_dir) / folder).read(s)
        if rec:
            records[s] = rec.get("quarters", {})
            if folder == "statements":
                plain.add(s)
    return records, plain


def read_reviews(repo, owner) -> tuple[list[dict], int]:
    stored = read_version(repo, owner, *REVIEWS, None)
    return (list(stored.payload.get("reviews", [])), stored.version) if stored else ([], 0)


def _quarter_label(q: str) -> str:
    return f"Q{q[-1]}/{q[:4]}"


def season_view(data_dir: Path, repo, owner, *, today: date) -> dict:
    data_dir = Path(data_dir)
    symbols = load_watchlist(data_dir).symbols
    sectors = load_sectors(data_dir)[0]
    records, plain = statement_records(data_dir, symbols, sectors)
    target = target_quarter(records)
    base = getattr(repo, "authoritative", repo)
    prefetch(base, owner, [REVIEWS, *(("settings", f"annual_plan_{s}") for s in records), *(("settings", f"quarter_forecast_{s}") for s in plain)])
    reviews, version = read_reviews(repo, owner)
    if target is None:
        return {"quarter": None, "version": version, "rows": [], "sectors": [], "cash": [], "reviews": reviews, "verdicts": VERDICTS, "watched": len(symbols), "reported": 0}
    held = set(held_costs(repo, owner))
    plans, forecasts, cafef = {}, {}, PlanStore(data_dir / "annual-plans-cafef")
    for s, quarters in records.items():
        own = read_version(repo, owner, "settings", f"annual_plan_{s}", None)
        for p in plan_progress((own.payload if own else {}).get("years", {}), quarters, cafef=(cafef.read(s) or {}).get("years")):
            if p["year"] == target[:4] and p["profit"] and p["profit"].get("ratio"):
                plans[s] = {"ratio": p["profit"]["ratio"], "label": p["profit_label"]}
        if s in plain and (saved := read_version(repo, owner, "settings", f"quarter_forecast_{s}", None)):
            mine = (saved.payload.get("quarters", {}).get(target) or {}).get("assumptions")
            if mine:
                value = forecast_quarter(quarters, target, mine)["values"].get("npat_parent")
                if value is not None:
                    forecasts[s] = Decimal(str(value))
    done = {r["symbol"]: r["verdict"] for r in reviews if r["quarter"] == target}
    rows = season_rows(records, sectors, target=target, held=held, plans=plans, forecasts=forecasts, reviews=done)
    for s in symbols:
        if s not in records:
            rows.append({"symbol": s, "sector": sectors.get(s), "held": s in held, "reported": False, "npat": None, "yoy": None, "qoq": None, "ytd": None, "ytd_ago": None,
                         "ytd_yoy": None, "plan_ratio": None, "plan_label": None, "forecast": None, "vs_forecast": None, "seasonal_share": None, "review": done.get(s)})
    return {"quarter": target, "label": _quarter_label(target), "version": version, "rows": sorted(rows, key=lambda r: r["symbol"]), "sectors": sector_table(rows),
            "cash": cash_rows({s: records[s] for s in plain}, target=target), "reviews": sorted(reviews, key=lambda r: r["at"], reverse=True)[:60],
            "verdicts": VERDICTS, "watched": len(symbols), "reported": sum(1 for r in rows if r["reported"])}


def review_lines(repo, owner, data_dir: Path) -> list[tuple[str, str]]:
    """(symbol, line) for each held ticker whose latest quarter is out with no review recorded after it."""
    held = held_costs(repo, owner)
    if not held:
        return []
    sectors = load_sectors(Path(data_dir))[0]
    records, _ = statement_records(Path(data_dir), sorted(held), sectors)
    reviews, _ = read_reviews(repo, owner)
    done = {(r["symbol"], r["quarter"]) for r in reviews}
    out = []
    for s, quarters in sorted(records.items()):
        latest = max((q for q, v in quarters.items() if v.get("npat_parent") is not None), default=None)
        if latest and (s, latest) not in done:
            out.append((s, f"{s}: đã có báo cáo {_quarter_label(latest)}, rà lại luận điểm"))
    return out
