"""Mục tiêu dòng tiền thụ động on Hồ sơ & rủi ro: the goal (`settings/passive_income`), the capital from Tháp tài sản, the monthly
contribution from Góp vốn đều, and an assumed yearly rate (the 12-month deposit rate unless the owner sets one)."""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.deposit_book import bond_income, deposit_income
from investment_agent.domain.models import ContractModel
from investment_agent.domain.ledger import replay
from investment_agent.domain.passive_income import _month_after, freedom_levels, income_by_layer, passive_income
from investment_agent.domain.property_book import PropertyBook, rent_now
from investment_agent.market.corporate_events import EventStore
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.cashflow import RECORD as CASHFLOW, closed_months, passive_actual
from investment_agent.services.contributions import PLAN as CONTRIBUTION_PLAN
from investment_agent.services.deposit_book import book_quotes, read_book
from investment_agent.services.equity_budget import budget_view
from investment_agent.services.property_book import RECORD as PROPERTY_BOOK
from investment_agent.services.records import LedgerBook, read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
RECORD = ("settings", "passive_income")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
WEALTH_CHECK = ("settings", "wealth_check")
BOND_RATE = "7"  # the owner's bonds pay 7%/năm (owner, 27/10/2026); editable with the goal


class GoalRequest(ContractModel):
    target: str = Field(max_length=24)
    rate: str | None = Field(default=None, max_length=8)  # percent per year; None = the 12-month deposit rate
    bond_rate: str | None = Field(default=None, max_length=8)  # coupon of the bonds held, percent per year; None = 7
    stock_rate: str | None = Field(default=None, max_length=8)  # yearly yield the owner expects from stocks; None = last year's cash dividends
    independent: str | None = Field(default=None, max_length=24)  # monthly spending for the two higher levels of Ba mức tự do tài chính
    freedom: str | None = Field(default=None, max_length=24)
    inflation: str | None = Field(default=None, max_length=8)  # percent per year; None = Vietnam's latest CPI on the year (owner, 22/11/2026)
    margin: str | None = Field(default=None, max_length=8)  # safety margin on the real target, percent; None = 0
    by_year: int | None = Field(default=None, strict=True)  # the year the owner wants to reach the target by (Lợi suất cần có)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def dividends_last_year(data_dir, repo, owner, today) -> Decimal:
    """Cash dividends per share with an ex-date in the last 12 months, times the shares held now (an estimate of what they paid)."""
    if data_dir is None:
        return Decimal(0)
    state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    shares = {p.security_id: p.quantity + p.pending_quantity for p in state.positions if p.quantity + p.pending_quantity > 0}
    since = (today - timedelta(days=365)).isoformat()
    total = Decimal(0)
    for e in EventStore(Path(data_dir)).events(sorted(shares)):
        if e.get("kind") == "dividend_cash" and e.get("value_per_share") and e.get("exright") and since <= e["exright"] <= today.isoformat():
            total += Decimal(str(e["value_per_share"])) * shares[e["symbol"]]
    return total


def _levels(repo, owner, income: dict, goal: dict, today) -> dict:
    """Mức an toàn is the spending entered at Sức khỏe tài chính; the other two are the owner's own."""
    wealth = read_version(repo, owner, *WEALTH_CHECK, None)
    stored = read_version(repo, owner, *PROPERTY_BOOK, None)
    rent, missing = rent_now(PropertyBook.model_validate(stored.payload) if stored else PropertyBook())
    amount = lambda key: Decimal(goal[key]) if goal.get(key) else None  # noqa: E731
    imported = read_version(repo, owner, *CASHFLOW, None)
    actual = passive_actual(imported.payload if imported else None, today=today)  # paid regularly, as written in Thu chi hằng tháng
    return {**freedom_levels(income=Decimal(income["total"]), rent=rent, safe=Decimal(wealth.payload["expenses"]) if wealth else None,
                             independent=amount("independent"), freedom=amount("freedom"), actual=Decimal(actual) if actual else None), "rent_missing": missing,
            "actual": actual, "actual_months": closed_months(imported.payload, today) if imported and actual else []}


def _view(request: Request, repo, owner) -> dict:
    data_dir = request.app.state.data_dir
    deposits = MacroStore(Path(data_dir)).read("deposit_12m") if data_dir is not None else []
    default_rate = deposits[-1]["value"] if deposits else None
    record = read_version(repo, owner, *RECORD, None)
    budget, _ = budget_view(repo, owner, quotes=book_quotes(request.app.state.data_dir, request.app.state.market))
    capital = Decimal(budget["base"]) if budget.get("status") == "ok" else None
    plan = read_version(repo, owner, *CONTRIBUTION_PLAN, None)
    contribution = Decimal(plan.payload["amount"]) if plan else Decimal(0)
    today = now(request).astimezone(VN).date()
    income = None
    pyramid = budget.get("pyramid") if budget.get("status") == "ok" else None
    if pyramid and default_rate is not None:
        layers = {l["id"]: Decimal(l["amount"]) for l in pyramid["layers"]}
        from_book = None
        if budget.get("deposit_source") == "book":  # each sổ at its own rate; the market rate only for a sổ without one, counted
            from_book = deposit_income(read_book(repo, owner)[0], market_rate=Decimal(default_rate))
        bond_rate = (record.payload.get("bond_rate") if record else None) or BOND_RATE
        bonds = None
        if (budget.get("layer_sources") or {}).get("bond") == "book":  # each row at its own rate; the owner's bond rate for the rest, counted
            bonds = bond_income(read_book(repo, owner)[0], default_rate=Decimal(bond_rate), navs=book_quotes(request.app.state.data_dir, request.app.state.market)["funds"])
        income = income_by_layer(deposit=layers.get("deposit", Decimal(0)), deposit_rate=Decimal(default_rate), bond=layers.get("bond", Decimal(0)),
                                 bond_rate=Decimal(bond_rate), dividends_12m=dividends_last_year(data_dir, repo, owner, today),
                                 stocks=layers.get("stocks", Decimal(0)),
                                 stock_rate=Decimal(record.payload["stock_rate"]) if record and record.payload.get("stock_rate") else None,
                                 deposit_monthly=from_book["monthly"] if from_book else None, bond_monthly=bonds["monthly"] if bonds else None)
        if from_book:
            income["deposit_market_rate_count"] = from_book["market_rate_count"]
        if bonds:
            income["bond_default_rate_count"] = bonds["default_rate_count"]
    result = None
    if record is not None:
        rate = record.payload.get("rate") or default_rate
        if rate is not None:
            result = {**passive_income(target=Decimal(record.payload["target"]), rate=Decimal(rate), capital=capital, contribution=contribution,
                                       today=today, income_now=Decimal(income["total"]) if income else None), "rate": rate,
                      **_real(data_dir, record.payload, rate=Decimal(rate), capital=capital, contribution=contribution, today=today)}
            result["needed"] = _needed(data_dir, repo, owner, record.payload, result, deposit=default_rate, capital=capital,
                                       contribution=contribution, today=today)
    goal = {**record.payload, "bond_rate": record.payload.get("bond_rate") or BOND_RATE} if record else None
    return {"version": record.version if record else 0, "goal": goal, "default_rate": default_rate, "default_bond_rate": BOND_RATE,
            "income": income, "levels": _levels(repo, owner, income, record.payload if record else {}, today) if income else None, "result": result, "capital": format(capital, "f") if capital is not None else None, "contribution": format(contribution, "f")}


def _real(data_dir, goal: dict, *, rate: Decimal, capital, contribution: Decimal, today) -> dict:
    """Mốc theo lợi suất thực and the 4% rule beside it (owner, 22/11/2026): the owner's inflation, else Vietnam's latest CPI on the year."""
    from investment_agent.domain.passive_income import real_target, rule_of_four
    store = MacroStore(Path(data_dir)) if data_dir is not None else None
    latest = lambda key: (store.read(key) or [None])[-1] if store else None  # noqa: E731
    inflation, source = goal.get("inflation"), None
    if inflation is None:
        cpi = latest("vn_cpi_yoy")
        inflation, source = (cpi["value"], {"source": "vn_cpi_yoy", "date": cpi["date"]}) if cpi else (None, None)
    margin = goal.get("margin") or "0"
    target = Decimal(goal["target"])
    real = None
    if inflation is not None:
        real = {**real_target(target=target, rate=rate, inflation=Decimal(inflation), margin=Decimal(margin), capital=capital,
                              contribution=contribution, today=today), "inflation": inflation, "inflation_from": source, "margin": margin}
    fx = latest("usd_vnd_vcb")
    return {"real": real, "four": {**rule_of_four(target=target, usd_vnd=Decimal(fx["value"]) if fx else None)},
            "four_fx_date": fx["date"] if fx else None}


def _own_yearly(data_dir, repo, owner, today) -> dict:
    """The owner's own return per year from Hiệu suất (time-weighted, deposits and withdrawals taken out), once the ledger is a year old."""
    from investment_agent.domain.required_return import yearly_growth
    from investment_agent.domain.time_weighted import performance
    from investment_agent.market.series import SeriesStore
    events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
    if not events or (today - min(e.effective_at for e in events)).days < 365 or data_dir is None:
        return {"rate": None, "reason": "short" if events else "no_ledger"}
    store = SeriesStore(Path(data_dir) / "trend-sources")
    symbols = {e.security_id for e in events if getattr(e, "security_id", None)}
    closes = {sym: {t.date(): v * 1000 for t, v in store.read(f"{sym}-1d")} for sym in symbols}
    total = performance(events, closes=closes, index={t.date(): v for t, v in store.read("VNINDEX-1d")}, today=today)["total"]
    if not total:
        return {"rate": None, "reason": "no_prices"}
    since = date.fromisoformat(total["since"])
    return {"rate": yearly_growth((since, Decimal(100)), (today, Decimal(100) * (1 + Decimal(total["portfolio"])))), "reason": None, "since": total["since"]}


def _needed(data_dir, repo, owner, goal: dict, result: dict, *, deposit, capital, contribution: Decimal, today) -> dict | None:
    """Lợi suất cần có để đạt đúng hạn (owner, 22/11/2026): the rate that reaches the real target (else the plain one) by the end of the
    year chosen, beside the 12-month deposit rate, VN-Index's growth per year over its stored history and the owner's own."""
    from investment_agent.domain.required_return import contribution_for, months_at, months_until, required_return, yearly_growth
    from investment_agent.market.series import SeriesStore
    by_year = goal.get("by_year")
    if not by_year:
        return None
    real = result.get("real") or {}
    target, source = (Decimal(real["required"]), "real") if real.get("required") else (Decimal(result["required"]), "nominal")
    months = months_until(date(by_year, 1, 1), today)
    out = {"by_year": by_year, "goal": format(target, "f"), "goal_from": source, "capital": format(capital, "f") if capital is not None else None,
           **required_return(capital=capital or Decimal(0), contribution=contribution, goal=target, months=months), "deposit": deposit}
    points = SeriesStore(Path(data_dir) / "trend-sources").read("VNINDEX-1d") if data_dir is not None else []
    vn = None
    if len(points) >= 2:
        first, last = points[0], points[-1]
        vn = {"rate": yearly_growth((first[0].date(), Decimal(str(first[1]))), (last[0].date(), Decimal(str(last[1])))),
              "from": first[0].date().isoformat(), "to": last[0].date().isoformat()}
    out["vnindex"] = vn
    out["own"] = _own_yearly(data_dir, repo, owner, today)
    at = None
    if vn and vn["rate"] is not None:
        rate = Decimal(vn["rate"])
        m = months_at(capital=capital or Decimal(0), contribution=contribution, goal=target, yearly_pct=rate)
        extra = contribution_for(capital=capital or Decimal(0), goal=target, yearly_pct=rate, months=months)
        at = {"reached_on": _month_after(today, m) if m is not None else None,
              "contribution": format(extra, "f") if extra is not None else None}
    out["at_vnindex"] = at
    return out


@router.get("/passive-income")
def get_passive_income(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/passive-income")
def put_passive_income(request: Request, body: GoalRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        target = Decimal(body.target)
        rate = Decimal(body.rate) if body.rate is not None else None
        bond_rate = Decimal(body.bond_rate) if body.bond_rate is not None else None
        stock_rate = Decimal(body.stock_rate) if body.stock_rate is not None else None
    except InvalidOperation:
        return error(422, "invalid_goal", "Mục tiêu và tỷ suất phải là số.")
    for level in (body.independent, body.freedom):
        try:
            whole = level is None or (Decimal(level).is_finite() and Decimal(level) > 0 and Decimal(level) == Decimal(level).to_integral_value())
        except InvalidOperation:
            whole = False
        if not whole:
            return error(422, "invalid_goal", "Mức chi tiêu phải là số đồng lớn hơn 0.")
    if not target.is_finite() or target <= 0 or target != target.to_integral_value():
        return error(422, "invalid_goal", "Dòng tiền mong muốn phải là số đồng lớn hơn 0.")
    if rate is not None and not (rate.is_finite() and Decimal("0.1") <= rate <= Decimal(30)):
        return error(422, "invalid_rate", "Tỷ suất giả định từ 0,1% đến 30%/năm.")
    if bond_rate is not None and not (bond_rate.is_finite() and Decimal(0) <= bond_rate <= Decimal(30)):
        return error(422, "invalid_rate", "Lãi suất trái phiếu từ 0% đến 30%/năm.")
    if stock_rate is not None and not (stock_rate.is_finite() and Decimal(0) <= stock_rate <= Decimal(50)):
        return error(422, "invalid_rate", "Lợi suất cổ phiếu từ 0% đến 50%/năm.")
    try:
        inflation = Decimal(body.inflation) if body.inflation is not None else None
        margin = Decimal(body.margin) if body.margin is not None else None
    except InvalidOperation:
        return error(422, "invalid_goal", "Lạm phát và biên an toàn phải là số.")
    if inflation is not None and not (inflation.is_finite() and Decimal(-5) <= inflation <= Decimal(30)):
        return error(422, "invalid_rate", "Lạm phát giả định từ −5% đến 30%/năm.")
    if margin is not None and not (margin.is_finite() and Decimal(0) <= margin <= Decimal(200)):
        return error(422, "invalid_rate", "Biên an toàn từ 0% đến 200%.")
    this_year = now(request).astimezone(VN).date().year
    if body.by_year is not None and not this_year <= body.by_year <= this_year + 60:
        return error(422, "invalid_year", f"Năm muốn đạt từ {this_year} đến {this_year + 60}.")
    payload = {"target": format(target, "f"), "rate": format(rate, "f") if rate is not None else None,
               "bond_rate": format(bond_rate, "f") if bond_rate is not None else None,
               "stock_rate": format(stock_rate, "f") if stock_rate is not None else None,
               "independent": format(Decimal(body.independent), "f") if body.independent is not None else None,
               "freedom": format(Decimal(body.freedom), "f") if body.freedom is not None else None,
               "inflation": format(inflation, "f") if inflation is not None else None, "margin": format(margin, "f") if margin is not None else None,
               "by_year": body.by_year}
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
