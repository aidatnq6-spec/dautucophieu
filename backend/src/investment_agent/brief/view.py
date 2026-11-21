"""Brief market section as shown: the public snapshot plus local, personal ordering (held tickers first, news picked on this
machine). Runs on the owner's machine only; nothing here is sent to a model."""

from decimal import Decimal

from pathlib import Path

from investment_agent.market.watchlist import load_watchlist

from .news import pick_news
from .recovery import recovery_checks
from .snapshot import BriefStore

NEWS_LIMIT = 8


def market_view(snapshot: dict | None, *, watched: list[str], held: set[str], news_limit: int = NEWS_LIMIT) -> dict | None:
    if not snapshot:
        return None
    board = snapshot.get("board") or {}
    symbols = board.get("symbols") or {}
    priced = board.get("status") == "ok"

    def row(s):
        r = symbols.get(s) or {}
        state = "no_price" if not priced or s not in symbols else "no_trade" if r.get("pct") is None else "ok"
        return {"symbol": s, **{k: r.get(k) for k in ("price", "change", "pct")}, "held": s in held, "sector": r.get("sector"), "state": state}
    first = [row(s) for s in sorted(held)]
    others = [row(s) for s in watched if s not in held]
    others.sort(key=lambda r: -abs(Decimal(r["pct"])) if r["pct"] is not None else 1)
    sector_names = {r["sector"] for r in first + others if r["sector"] and r["sector"] != "Khác"}
    news = snapshot.get("news") or {"status": "missing", "reason": "Chưa có tin"}
    if news.get("status") == "ok":
        news = {"status": "ok", "items": pick_news(news["items"], watched=watched, held=held, sector_names=sector_names, limit=news_limit)}
    view = {k: snapshot.get(k) for k in ("session_date", "updated_at", "indices", "hose", "proprietary")}
    view["board"] = {k: v for k, v in board.items() if k != "symbols"}
    for name in ("index_session", "hose_liquidity", "signals", "asia", "us", "shocks"):  # snapshots stored before 06/11/2026 (signals: 16/11, us and shocks: 21/11) lack them
        view[name] = snapshot.get(name) or {"status": "missing", "reason": "Ảnh chụp phiên này chưa có mục này"}
    view["recovery"] = recovery_checks(snapshot.get("index_session"), board)  # Bảng kiểm "Thị trường phục hồi"
    from investment_agent.notifications.render import signal_lines
    view["signal_lines"] = signal_lines(snapshot.get("signals"))
    from investment_agent.market.asia_indices import asia_line
    view["asia_line"] = asia_line(snapshot.get("asia"))  # Tín hiệu phiên, the same lines as the Telegram brief
    from investment_agent.market.us_indices import us_line
    view["us_line"] = us_line(snapshot.get("us"))  # Chứng khoán Mỹ (FRED), stored with the snapshot from 21/11/2026
    from investment_agent.domain.history_stats import shock_line
    view["shock_line"] = shock_line(snapshot.get("shocks"))  # Cú sốc hôm nay, stored with the snapshot from 21/11/2026
    view["impact"] = _impact((snapshot.get("signals") or {}).get("pull") or {}, held)
    view["heatmap"] = _heatmap(symbols, held) if priced else {"status": "missing", "reason": board.get("reason") or "Chưa có bảng giá cả sàn"}
    return {**view, "tickers": first + others, "news": news}


def _impact(pull: dict, held: set[str]) -> dict:
    """Tác động lên VN-Index (21/11/2026): the stocks' points as Tín hiệu phiên worked them out, held ones marked; only when the sum
    matched VN-Index's move."""
    if pull.get("status") != "ok":
        return {"status": "missing", "reason": pull.get("reason") or "Chưa tính được điểm kéo chỉ số cho phiên này"}
    mark = lambda rows: [{**r, "held": r["symbol"] in held} for r in rows]  # noqa: E731
    return {"status": "ok", "computed": pull["computed"], "actual": pull["actual"], "up": mark(pull["up"]), "down": mark(pull["down"])}


def _heatmap(symbols: dict, held: set[str]) -> dict:
    """Bản đồ nhiệt phiên (21/11/2026): every traded stock with its sector, change and matched value, held ones marked."""
    rows = [{"symbol": s, "sector": r.get("sector"), "pct": r["pct"], "value_mn": r["value_mn"], "held": s in held}
            for s, r in symbols.items() if r.get("pct") is not None and r.get("value_mn") and Decimal(r["value_mn"]) > 0]
    if not rows:
        return {"status": "missing", "reason": "Ảnh chụp phiên này chưa có giá trị giao dịch từng mã (lưu từ 21/11/2026)"}
    rows.sort(key=lambda r: -Decimal(r["value_mn"]))
    return {"status": "ok", "rows": rows}


RECENT = 5


def _signal_row(snapshot: dict) -> dict:
    """One session of the "5 phiên gần nhất" table: VN-Index's move and that session's signals (None where the snapshot had none)."""
    vn = next((r for r in (snapshot.get("indices") or {}).get("rows", []) if r.get("id") == "VNINDEX" and r.get("status") == "ok"), {})
    s = snapshot.get("signals") or {}
    known = s.get("status") == "ok"
    asia, liq, pull = s.get("asia"), s.get("liquidity") or {}, s.get("pull") or {}
    way = None
    if asia:
        same, other = (asia["up"], asia["down"]) if asia["index"] == "up" else (asia["down"], asia["up"])
        way = "with" if same > other else "against" if other > same else "split"
    top = None
    if pull.get("status") == "ok":
        lead = pull["up"] if Decimal(pull["actual"]) >= 0 else pull["down"]
        top = lead[0] if lead else None
    return {"date": snapshot["session_date"], "change": vn.get("change"), "pct": vn.get("pct"), "known": known,
            "breadth": (s.get("breadth_gap") or {}).get("kind") if known else None, "low_liquidity": liq.get("low") if known and liq else None,
            "ratio20": liq.get("ratio20") if known and liq else None, "asia": way, "asia_counted": asia["counted"] if asia else None, "top": top}


def recent_signals(data_dir: Path, session, n: int = RECENT) -> list[dict]:
    """The session and the ones stored before it, newest first, n of them."""
    store = BriefStore(Path(data_dir))
    days = sorted((p.stem for p in store.root.glob("*.json") if p.stem <= str(session)), reverse=True)[:n]
    return [_signal_row(snap) for d in days if (snap := store.read(d))]


def market_for_session(data_dir: Path | None, held: set[str]):
    """session date (ISO) -> market view, reading data/brief on demand; None when there is no data dir or snapshot."""
    if data_dir is None:
        return lambda session: None

    def view(session):
        # The market section is an extra: a corrupt watchlist or snapshot only drops it, never the brief or its delivery.
        try:
            watched = list(load_watchlist(Path(data_dir)).symbols)
            out = market_view(BriefStore(Path(data_dir)).read(session), watched=watched, held=held) if session else None
            if out is not None:
                out["recent_signals"] = recent_signals(Path(data_dir), session)  # 5 phiên gần nhất, for runs of days
            return out
        except Exception:
            return None
    return view
