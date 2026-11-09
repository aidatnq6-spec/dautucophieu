"""Kế hoạch sụt giảm: deepest falls over the full stored history for VN-Index and held tickers, and a one-time Telegram reminder
when a held ticker falls past the owner's threshold below its average cost. Personal data; never sent to a model."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

from investment_agent.domain.drawdown import current_drawdown, max_drawdown, threshold_alerts
from investment_agent.domain.ledger import replay
from investment_agent.market.history import backfill_history, history_complete
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.notifications.render import _num, vnd
from investment_agent.services.journal import read_journal
from investment_agent.services.records import LedgerBook, portfolio_settings, read_version

INDEX = "VNINDEX"
INDICES = (INDEX, "VN30")
BACKFILL_PER_RUN = 15  # series per scheduler run (~2–3 Vnstock calls each); the 50 watched tickers fill in over a few runs
ALERTS = ("settings", "drawdown_alerts")
OLD_PRICES_PER_RUN = 5  # tickers per run that appear only in the imported journal
OLD_FRESH_DAYS, OLD_RETRY_DAYS, OLD_FIRST_DAYS = 7, 30, 2920  # about eight years, one Vnstock window
NO_PRICES = "_no_prices.json"


def held_costs(repo, owner) -> dict[str, str]:
    """Average cost per share (đồng) of each ticker with shares; raises RepositoryUnavailable."""
    state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    return {p.security_id: format(p.average_cost, "f") for p in state.positions if p.quantity + p.pending_quantity > 0}


def last_close(series: SeriesStore, symbol: str) -> str | None:
    """Last stored close in đồng (Vnstock stores stocks in thousand đồng); VN-Index stays in points."""
    points = series.read(f"{symbol}-1d")
    if not points:
        return None
    value = Decimal(str(points[-1][1])) * (1 if symbol == INDEX else 1000)
    return format(value.normalize(), "f")


def watched(data_dir: Path, costs: dict[str, str]) -> list[str]:
    """Watched tickers that are not held, in watchlist order."""
    return [s for s in load_watchlist(Path(data_dir)).symbols if s not in costs]


def watch_rows(data_dir: Path, symbols: list[str]) -> list[dict]:
    """Deepest and current falls for watched tickers, the deepest current fall first; tickers without stored closes last."""
    series = SeriesStore(Path(data_dir) / "trend-sources")
    rows = []
    for symbol in symbols:
        points = series.read(f"{symbol}-1d")
        rows.append({"symbol": symbol, "since": points[0][0].date().isoformat() if points else None, "max": max_drawdown(points),
                     "current": current_drawdown(points)})
    return sorted(rows, key=lambda r: Decimal(r["current"]["depth"]) if r["current"] else Decimal(1))


def drawdown_rows(data_dir: Path, costs: dict[str, str], prices: dict[str, str | None], threshold: Decimal) -> list[dict]:
    series = SeriesStore(Path(data_dir) / "trend-sources")
    rows = []
    for symbol in [*INDICES, *sorted(costs)]:
        points = series.read(f"{symbol}-1d")
        cost, price = costs.get(symbol), prices.get(symbol)
        vs_cost = (Decimal(price) / Decimal(cost) - 1).quantize(Decimal("0.0001")) if cost and price and Decimal(cost) > 0 else None
        if symbol in INDICES and symbol != INDEX and not points:
            continue  # VN30 appears once its closes are stored
        rows.append({"symbol": symbol, "since": points[0][0].date().isoformat() if points else None, "max": max_drawdown(points),
                     "current": current_drawdown(points), "price": price, "cost": cost,
                     "vs_cost": str(vs_cost) if vs_cost is not None else None, "hit": vs_cost is not None and vs_cost <= -threshold})
    return rows


def render_alerts(alerts: list[dict], *, threshold: Decimal, reasons: dict[str, str]) -> str:
    """Plain-text reminder: how far below cost, and the owner's own threshold and reason. No advice."""
    lines = [f"Kế hoạch sụt giảm — đã chạm ngưỡng bạn đặt ({_num(threshold * 100, 0)}% dưới giá vốn)"]
    for a in alerts:
        lines += ["", f"{a['symbol']}: {_num(Decimal(a['change']) * 100, 1, sign=True)}% so với giá vốn",
                  f"Giá {vnd(a['price'])} · giá vốn bình quân {vnd(a['cost'])}"]
        if reason := reasons.get(a["symbol"]):
            lines.append(f"Lý do bạn đã ghi: {reason}")
    lines += ["", "Chỉ là lời nhắc theo ngưỡng bạn tự đặt; xem lại kế hoạch của bạn."]
    return "\n".join(lines)


def _old_tickers(repo, owner) -> list[str]:
    """Share tickers bought or sold in the imported older journal, for Hậu kiểm."""
    return sorted({e.symbol for e in read_journal(repo, owner)[0] if e.imported and e.imported.get("asset") == "Cổ phiếu" and e.kind in ("buy", "sell")})


def _fill_old_tickers(symbols: list[str], series: SeriesStore, root: Path, fetch, today: date, limit: int) -> int:
    """Daily closes for tickers no other feature keeps: first the recent years, then brought up to date weekly. A ticker the source does
    not answer for (often delisted) is left for a month; one failure never stops the others. Public prices only."""
    path = root / NO_PRICES
    waiting = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    called = 0
    for symbol in symbols:
        if called >= limit:
            break
        key = f"{symbol}-1d"
        points = series.read(key)
        last = points[-1][0].date() if points else None
        if (last and (today - last).days <= OLD_FRESH_DAYS) or (symbol in waiting and (today - date.fromisoformat(waiting[symbol])).days < OLD_RETRY_DAYS):
            continue
        called += 1
        try:
            closes = [p for p in fetch(symbol, last + timedelta(days=1) if last else today - timedelta(days=OLD_FIRST_DAYS), today) if float(p[1]) > 0]
        except Exception:
            closes = []
        if closes:
            series.upsert(key, closes)
            waiting.pop(symbol, None)
        else:
            waiting[symbol] = today.isoformat()
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(waiting, sort_keys=True), encoding="utf-8")
    return called


def drawdown_run(repo, owner, data_dir: Path, *, fetch, send, request_id: str, backfill_limit: int = BACKFILL_PER_RUN, today: date | None = None,
                 old_price_limit: int = OLD_PRICES_PER_RUN) -> dict:
    """fetch(symbol, start, end) -> daily closes. Fills full history (once per series, a few series per run: indices and holdings
    first, then watched tickers), then reminds once per crossing."""
    series_root = Path(data_dir) / "trend-sources"
    series = SeriesStore(series_root)
    costs = held_costs(repo, owner)
    known = watched(data_dir, costs)
    old = [s for s in _old_tickers(repo, owner) if s not in costs and s not in known and s not in INDICES]
    old_prices = _fill_old_tickers(old, series, series_root, fetch, today or datetime.now(timezone(timedelta(hours=7))).date(), old_price_limit)
    order = [*INDICES, *sorted(costs), *known, *old]
    pending = [s for s in order if not history_complete(series_root, f"{s}-1d") and series.read(f"{s}-1d")][:backfill_limit]
    history = {}
    for symbol in pending:
        history[symbol] = backfill_history(series, f"{symbol}-1d", lambda s, e, sym=symbol: fetch(sym, s, e), root=series_root)
    settings, _ = portfolio_settings(repo, owner)
    record = read_version(repo, owner, *ALERTS, None)
    before = set(record.payload.get("alerted", [])) if record else set()
    holdings = {s: {"price": last_close(series, s), "cost": c} for s, c in costs.items()}
    alerts, alerted = threshold_alerts(holdings, threshold=str(settings.drawdown_threshold), alerted=before)
    sent = False
    if alerts:
        entries, _ = read_journal(repo, owner)
        # The latest decision per ticker wins, by its date: an older journal imported later is saved last but happened first.
        reasons = {e.symbol: e.reason for e in sorted(entries, key=lambda e: e.created_on) if e.reason}
        sent = bool(send(render_alerts(alerts, threshold=settings.drawdown_threshold, reasons=reasons)))
        if not sent:
            alerted -= {a["symbol"] for a in alerts}  # not delivered: try again next run
    if alerted != before:
        repo.write(owner, *ALERTS, {"alerted": sorted(alerted)}, expected_version=record.version if record else 0, request_id=request_id)
    return {"alerts": len(alerts), "sent": sent, "history": {s: n for s, n in history.items() if s not in old}, **({"old_prices": old_prices} if old else {})}
