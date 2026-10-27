"""Kế hoạch sụt giảm: deepest falls over the full stored history for VN-Index and held tickers, and a one-time Telegram reminder
when a held ticker falls past the owner's threshold below its average cost. Personal data; never sent to a model."""

from decimal import Decimal
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


def drawdown_run(repo, owner, data_dir: Path, *, fetch, send, request_id: str, backfill_limit: int = BACKFILL_PER_RUN) -> dict:
    """fetch(symbol, start, end) -> daily closes. Fills full history (once per series, a few series per run: indices and holdings
    first, then watched tickers), then reminds once per crossing."""
    series_root = Path(data_dir) / "trend-sources"
    series = SeriesStore(series_root)
    costs = held_costs(repo, owner)
    order = [*INDICES, *sorted(costs), *watched(data_dir, costs)]
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
        reasons = {e.symbol: e.reason for e in entries if e.reason}  # the latest entry per ticker wins
        sent = bool(send(render_alerts(alerts, threshold=settings.drawdown_threshold, reasons=reasons)))
        if not sent:
            alerted -= {a["symbol"] for a in alerts}  # not delivered: try again next run
    if alerted != before:
        repo.write(owner, *ALERTS, {"alerted": sorted(alerted)}, expected_version=record.version if record else 0, request_id=request_id)
    return {"alerts": len(alerts), "sent": sent, "history": history}
