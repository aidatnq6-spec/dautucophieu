"""Kế hoạch sụt giảm: deepest falls over the full stored history for VN-Index and held tickers, and a one-time Telegram reminder
when a held ticker falls past the owner's threshold below its average cost. Personal data; never sent to a model."""

from decimal import Decimal
from pathlib import Path

from investment_agent.domain.drawdown import current_drawdown, max_drawdown, threshold_alerts
from investment_agent.domain.ledger import replay
from investment_agent.market.history import backfill_history
from investment_agent.market.series import SeriesStore
from investment_agent.notifications.render import _num, vnd
from investment_agent.services.journal import read_journal
from investment_agent.services.records import LedgerBook, portfolio_settings, read_version

INDEX = "VNINDEX"
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


def drawdown_rows(data_dir: Path, costs: dict[str, str], prices: dict[str, str | None], threshold: Decimal) -> list[dict]:
    series = SeriesStore(Path(data_dir) / "trend-sources")
    rows = []
    for symbol in [INDEX, *sorted(costs)]:
        points = series.read(f"{symbol}-1d")
        cost, price = costs.get(symbol), prices.get(symbol)
        vs_cost = (Decimal(price) / Decimal(cost) - 1).quantize(Decimal("0.0001")) if cost and price and Decimal(cost) > 0 else None
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


def drawdown_run(repo, owner, data_dir: Path, *, fetch, send, request_id: str) -> dict:
    """fetch(symbol, start, end) -> daily closes. Fills full history (once per series), then reminds once per crossing."""
    series_root = Path(data_dir) / "trend-sources"
    series = SeriesStore(series_root)
    costs = held_costs(repo, owner)
    history = {}
    for symbol in [INDEX, *sorted(costs)]:
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
