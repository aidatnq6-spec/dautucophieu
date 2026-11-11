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
from investment_agent.services.earnings_season import review_lines
from investment_agent.services.accumulation import due_lines
from investment_agent.services.insurance_alerts import due_items as payment_items
from investment_agent.services.loan_alerts import promo_lines, read_property_book
from investment_agent.domain.rental_book import due_items as rental_items
from investment_agent.services.rental_alerts import read_rental_book
from investment_agent.services.records import portfolio_settings
from investment_agent.services.system_health import health_report
from investment_agent.services.theses import read_theses

NEW_QUARTER_DAYS = 7
EARLY_EXIT_DAYS = 30  # an early exit stays in Việc cần xem for a month after the thesis closed
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
            e = t.get("exit") or {}
            if e.get("early") and t["closed_on"] >= (now.date() - timedelta(days=EARLY_EXIT_DAYS)).isoformat():
                items.append({"level": "low", "kind": "early_exit", "symbol": t["symbol"], "href": "/journal",
                              "text": f"{t['symbol']}: đã bán sau {e['days']} ngày với lãi {_pct(e['return'])}, trong khi mục tiêu bạn đặt là {e['target']}% "
                                      f"trong {e['months']} tháng. Ghi lại vì sao bán sớm vào Nhật ký."})
            continue
        for c in t["conditions"]:
            if c.get("status") == "broken" and not c.get("hold"):
                label = KINDS[c["kind"]][0] if c["kind"] in KINDS else c["kind"]
                items.append({"level": "high", "kind": "thesis", "symbol": t["symbol"], "text": f"{t['symbol']}: điều kiện luận điểm bị phá ({label})", "href": "/portfolio"})
    series = SeriesStore(data_dir / "trend-sources")
    costs = held_costs(repo, owner)
    alerts, _ = threshold_alerts({s: {"price": last_close(series, s), "cost": c} for s, c in costs.items()}, threshold=str(portfolio_settings(repo, owner)[0].drawdown_threshold), alerted=set())
    items += [{"level": "high", "kind": "drawdown", "symbol": a["symbol"], "text": f"{a['symbol']}: đang {_pct(a['change'])} so với giá vốn, quá ngưỡng sụt giảm", "href": "/portfolio"} for a in alerts]
    property_book, vn_today = read_property_book(repo, owner), now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    items += [{"level": "high", "kind": "loan_promo", "symbol": None, "text": line, "href": "/profile?tab=tai-san"} for line in promo_lines(property_book, vn_today)]
    items += [{"level": "high", "kind": kind, "symbol": None, "text": line, "href": "/profile?tab=tai-san"} for kind, line in payment_items(property_book, vn_today)]
    items += [{"level": "high", "kind": kind, "symbol": None, "text": line, "href": "/profile?tab=tai-san"} for kind, _, line in rental_items(read_rental_book(repo, owner), vn_today)]
    items += [{"level": "low", "kind": "accumulation", "symbol": None, "text": line, "href": "/profile?tab=ke-hoach"}
              for line in due_lines(repo, owner, today=now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date())]
    items += [{"level": "high", "kind": "thesis_review", "symbol": s, "text": line, "href": "/earnings#ra-soat"} for s, line in review_lines(repo, owner, data_dir)]
    since = (now.date() - timedelta(days=NEW_QUARTER_DAYS)).isoformat()
    store = FundamentalsStore(data_dir / "fundamentals")
    for symbol in load_watchlist(data_dir).symbols:
        seen = (store.read(symbol) or {}).get("latest_quarter_seen")
        if seen and seen["on"] >= since:
            q = seen["quarter"]
            items.append({"level": "low", "kind": "quarter", "symbol": symbol, "text": f"{symbol}: có báo cáo Q{q[-1]}/{q[:4]}", "href": f"/research/{symbol}"})
    return sorted(items, key=lambda i: _ORDER[i["level"]])
