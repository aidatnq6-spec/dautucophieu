"""Việc cần xem: what needs a decision (a broken thesis condition, a holding past the loss threshold, something wrong with the unattended
work) and what is new (a quarterly report just out), for the overview page and the weekly note. Personal data, never sent to a model."""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from investment_agent.domain.drawdown import threshold_alerts
from investment_agent.domain.thesis import KINDS
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.drawdown import held_costs, last_close
from investment_agent.services.loan_alerts import promo_lines, read_property_book
from investment_agent.services.records import portfolio_settings
from investment_agent.services.system_health import health_report
from investment_agent.services.theses import read_theses

NEW_QUARTER_DAYS = 7
_ORDER = {"high": 0, "low": 1}


def _pct(ratio: str) -> str:
    return f"{(Decimal(ratio) * 100).quantize(Decimal('0.1'), ROUND_HALF_UP)}%".replace(".", ",")


def attention_items(repo, owner, data_dir: Path, *, now: datetime) -> list[dict]:
    """{level, kind, symbol, text, href}, what needs a decision first. A condition the owner has chosen to hold through is not repeated here."""
    data_dir = Path(data_dir)
    items = [{"level": "high", "kind": "system", "symbol": None, "text": f"Hệ thống · {p['label']}: {p['detail']}", "href": "/settings"}
             for p in health_report(data_dir, now=now)["problems"]]
    for t in read_theses(repo, owner)[0]:
        if t.get("closed_on"):
            continue
        for c in t["conditions"]:
            if c.get("status") == "broken" and not c.get("hold"):
                label = KINDS[c["kind"]][0] if c["kind"] in KINDS else c["kind"]
                items.append({"level": "high", "kind": "thesis", "symbol": t["symbol"], "text": f"{t['symbol']}: điều kiện luận điểm bị phá ({label})", "href": "/portfolio"})
    series = SeriesStore(data_dir / "trend-sources")
    costs = held_costs(repo, owner)
    alerts, _ = threshold_alerts({s: {"price": last_close(series, s), "cost": c} for s, c in costs.items()}, threshold=str(portfolio_settings(repo, owner)[0].drawdown_threshold), alerted=set())
    items += [{"level": "high", "kind": "drawdown", "symbol": a["symbol"], "text": f"{a['symbol']}: đang {_pct(a['change'])} so với giá vốn, quá ngưỡng sụt giảm", "href": "/portfolio"} for a in alerts]
    items += [{"level": "high", "kind": "loan_promo", "symbol": None, "text": line, "href": "/profile"}
              for line in promo_lines(read_property_book(repo, owner), now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date())]
    since = (now.date() - timedelta(days=NEW_QUARTER_DAYS)).isoformat()
    store = FundamentalsStore(data_dir / "fundamentals")
    for symbol in load_watchlist(data_dir).symbols:
        seen = (store.read(symbol) or {}).get("latest_quarter_seen")
        if seen and seen["on"] >= since:
            q = seen["quarter"]
            items.append({"level": "low", "kind": "quarter", "symbol": symbol, "text": f"{symbol}: có báo cáo Q{q[-1]}/{q[:4]}", "href": f"/research/{symbol}"})
    return sorted(items, key=lambda i: _ORDER[i["level"]])
