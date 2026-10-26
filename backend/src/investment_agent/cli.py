"""Small local command surface: source audits and the scheduled after-close run."""

import argparse
import json
from pathlib import Path

from investment_agent.market.coverage import audit_case, audit_universe, load_fixture_cases


FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "market" / "coverage_cases.json"


def main() -> int:
    parser = argparse.ArgumentParser(prog="investment_agent")
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("data-audit")
    audit.add_argument("--fixtures", action="store_true", help="use synthetic local cases")
    audit.add_argument("--output-dir", type=Path, default=Path.cwd())
    tick = commands.add_parser("scheduled-run", help="one scheduler wake-up (Windows Task Scheduler)")
    tick.add_argument("--calendar", type=Path, required=True, help="owner-verified trading calendar JSON")
    tick.add_argument("--data-dir", type=Path, required=True)
    backup = commands.add_parser("backup", help="local backup of data/ plus the personal Firestore export")
    backup.add_argument("--data-dir", type=Path, required=True)
    backup.add_argument("--backup-dir", type=Path, required=True)
    backup.add_argument("--kind", choices=["daily", "weekly", "manual", "auto"], default="daily",
                        help="auto: the scheduler's kind, or nothing when no backup is due")
    vaudit = commands.add_parser("vnstock-audit", help="depth check of Vnstock data against the 10-year requirement")
    vaudit.add_argument("--symbols", required=True, help="comma-separated tickers")
    vaudit.add_argument("--output-dir", type=Path, required=True)
    groups = commands.add_parser("index-groups", help="save current index constituents (e.g. VN30, VN100) for the watchlist")
    groups.add_argument("--groups", default="VN30,VN100")
    groups.add_argument("--output", type=Path, required=True)
    sync = commands.add_parser("market-sync", help="load recent Vnstock daily prices (adjusted) into the local store")
    sync.add_argument("--symbols", required=True, help="comma-separated tickers, or @file with one ticker per line")
    sync.add_argument("--data-dir", type=Path, required=True)
    sync.add_argument("--calendar", type=Path, required=True)
    sync.add_argument("--days", type=int, default=30)
    sync.add_argument("--index", action="store_true", help="the symbols are indices (e.g. VNINDEX), quoted in points")
    macro = commands.add_parser("macro-sync", help="fetch automatic macro indicators (FRED, Vietcombank) into data/macro")
    macro.add_argument("--data-dir", type=Path, required=True)
    fsync = commands.add_parser("fundamentals-sync", help="refresh statements for the Định giá page (paced for Vnstock's limit)")
    fsync.add_argument("--data-dir", type=Path, required=True)
    fsync.add_argument("--limit", type=int, default=8)
    fsync.add_argument("--all", action="store_true", help="every watched ticker, for the first load")
    fsync.add_argument("--symbols", help="comma-separated tickers to refresh now, however recent their data")
    trend = commands.add_parser("trend-run", help="build the Xu hướng board after 15:30 on trading days")
    trend.add_argument("--data-dir", type=Path, required=True)
    trend.add_argument("--calendar", type=Path, required=True)
    sectors = commands.add_parser("industries", help="save ICB level-2 sectors of the synced tickers for the market page")
    sectors.add_argument("--symbols", required=True, help="comma-separated tickers, or @file with one ticker per line")
    sectors.add_argument("--output", type=Path, required=True)
    journal = commands.add_parser("journal-review", help="Nhật ký: Telegram reminder when a price moved another threshold step")
    journal.add_argument("--data-dir", type=Path, required=True)
    events = commands.add_parser("events-sync", help="corporate events of watched tickers; Telegram reminder 5 days ahead")
    events.add_argument("--data-dir", type=Path, required=True)
    brief = commands.add_parser("brief-snapshot", help="public market snapshot of the latest session for the after-close brief")
    brief.add_argument("--data-dir", type=Path, required=True)
    brief.add_argument("--calendar", type=Path, required=True)
    ins = commands.add_parser("insights-run", help="read new public ACBS/World Bank reports with AI (public text only), then Telegram")
    ins.add_argument("--data-dir", type=Path, required=True)
    ins.add_argument("--calendar", type=Path, required=True)
    ins.add_argument("--min-hours", type=float, default=6, help="skip when the previous run is more recent than this")
    args = parser.parse_args()
    if args.command == "vnstock-audit":
        return vnstock_audit(_symbols(args.symbols), args.output_dir)
    if args.command == "index-groups":
        return index_groups([g.strip().upper() for g in args.groups.split(",") if g.strip()], args.output)
    if args.command == "market-sync":
        return market_sync(_symbols(args.symbols), args.data_dir, args.calendar, args.days, index=args.index)
    if args.command == "fundamentals-sync":
        return fundamentals_sync(args.data_dir, limit=None if args.all or args.symbols else args.limit,
                                 symbols=_symbols(args.symbols) if args.symbols else None)
    if args.command == "trend-run":
        return trend_run(args.data_dir, args.calendar)
    if args.command == "macro-sync":
        return macro_sync(args.data_dir)
    if args.command == "industries":
        return industries(_symbols(args.symbols), args.output)
    if args.command == "backup":
        return run_backup(args.data_dir, args.backup_dir, args.kind)
    if args.command == "scheduled-run":
        return scheduled_run(args.calendar, args.data_dir)
    if args.command == "journal-review":
        return journal_cli(args.data_dir)
    if args.command == "events-sync":
        return events_cli(args.data_dir)
    if args.command == "brief-snapshot":
        return brief_snapshot_cli(args.data_dir, args.calendar)
    if args.command == "insights-run":
        return insights_cli(args.data_dir, args.calendar, min_hours=args.min_hours)
    if not args.fixtures:
        parser.error("data-audit currently requires --fixtures; live provider audits are not configured")
    reports = [audit_case(case) for case in load_fixture_cases(FIXTURES)]
    aggregate = audit_universe(reports)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "data-audit.json"
    md_path = args.output_dir / "data-audit.md"
    json_path.write_text(json.dumps({"aggregate": aggregate.to_dict(), "issuers": [r.to_dict() for r in reports]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("# Synthetic market data audit\n\n" + aggregate.to_markdown() + "\n\n" + "\n\n".join(r.to_markdown() for r in reports) + "\n", encoding="utf-8")
    print(json_path)
    print(md_path)
    return 0


def load_calendar(path: Path):
    from datetime import date
    from investment_agent.market.calendar import TradingCalendar
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("source") in (None, "", "synthetic"):
        raise ValueError("calendar must name its official source")
    return TradingCalendar(version=data["version"], source=data["source"], holidays=frozenset(date.fromisoformat(d) for d in data["holidays"]),
                           first=date.fromisoformat(data["first"]), last=date.fromisoformat(data["last"]))


def _symbols(raw: str) -> list[str]:
    text = Path(raw[1:]).read_text(encoding="utf-8") if raw.startswith("@") else raw.replace(",", "\n")
    return [s.strip().upper() for s in text.splitlines() if s.strip() and not s.strip().startswith("#")]


def vnstock_audit(symbols: list[str], output_dir: Path, provider=None, today=None) -> int:
    from datetime import date
    from investment_agent.market.providers.vnstock_adapter import ProviderUnavailable, VnstockProvider, audit_symbol
    provider = provider or VnstockProvider()
    today = today or date.today()
    results = []
    for symbol in symbols:
        try:
            results.append(audit_symbol(provider, symbol, today=today))
        except ProviderUnavailable as exc:
            print(json.dumps({"status": "not_configured", "reason": str(exc)}, ensure_ascii=False))
            return 2
        except Exception as exc:  # one failing symbol is recorded, the audit continues
            results.append({"symbol": symbol, "error": type(exc).__name__})
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vnstock-audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = sum(1 for r in results if r.get("meets_10y_prices") and r.get("meets_40_quarters"))
    print(json.dumps({"status": "ok", "symbols": len(results), "meet_10y_and_40q": passed, "file": str(output_dir / "vnstock-audit.json")}))
    return 0


def index_groups(groups: list[str], output: Path, provider=None, today=None) -> int:
    from datetime import date
    from investment_agent.market.providers.vnstock_adapter import SOURCE, ProviderUnavailable, VnstockProvider
    provider = provider or VnstockProvider()
    try:
        members = {g: provider.index_members(g) for g in groups}
    except ProviderUnavailable as exc:
        print(json.dumps({"status": "not_configured", "reason": str(exc)}, ensure_ascii=False))
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"as_of": (today or date.today()).isoformat(), "source": f"vnstock:{SOURCE}", "groups": members}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "groups": {g: len(m) for g, m in members.items()}}))
    return 0


def _same_bar(a, b) -> bool:
    return a.model_dump(exclude={"observed_at"}) == b.model_dump(exclude={"observed_at"})


def fundamentals_sync(data_dir: Path, *, limit: int | None, symbols: list[str] | None = None, provider=None, now=None, sleep=None) -> int:
    import time
    from datetime import datetime, timezone
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.providers.vnstock_adapter import VnstockProvider
    from investment_agent.market.series import SeriesStore
    from investment_agent.market.watchlist import load_watchlist
    # Named tickers are refreshed now (max age 0); otherwise the stalest watched tickers.
    out = sync_fundamentals(FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources"),
                            symbols or list(load_watchlist(data_dir).symbols), provider=provider or VnstockProvider(),
                            now=now or datetime.now(timezone.utc), limit=limit, max_age_days=0 if symbols else 7, sleep=sleep or time.sleep)
    print(json.dumps(out, ensure_ascii=False))
    return 1 if out["errors"] else 0


def trend_run(data_dir: Path, calendar_path: Path, now=None, provider=None, get=None) -> int:
    """Exit 0 when the board was built or the run was skipped, 1 when a source failed (the board is still saved)."""
    from datetime import datetime, timezone
    from investment_agent.market.providers.vnstock_adapter import VnstockProvider
    from investment_agent.market.trend import run_trend
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    result = run_trend(data_dir, load_calendar(calendar_path), now=now or datetime.now(timezone.utc), provider=provider or VnstockProvider(),
                       get=get)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("errors") else 0


def macro_sync(data_dir: Path, get=None) -> int:
    """Exit 0 when every automatic indicator updated, 1 when some failed (each is reported)."""
    from investment_agent.market.leading import MacroStore, fetch_auto, load_indicators
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    results = fetch_auto(load_indicators(), MacroStore(data_dir), get=get)
    failed = {k: v for k, v in results.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}))
    return 0 if not failed else 1


def industries(symbols: list[str], output: Path, provider=None, today=None) -> int:
    from datetime import date
    from investment_agent.market.providers.vnstock_adapter import ProviderUnavailable, VnstockProvider
    provider = provider or VnstockProvider()
    try:
        sectors = provider.industry_map(symbols, level=2)
    except ProviderUnavailable as exc:
        print(json.dumps({"status": "not_configured", "reason": str(exc)}, ensure_ascii=False))
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"as_of": (today or date.today()).isoformat(), "source": "vnstock:vci", "level": 2, "sectors": dict(sorted(sectors.items()))}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "classified": len(sectors), "unclassified": len(set(symbols) - set(sectors))}))
    return 0


def market_sync(symbols: list[str], data_dir: Path, calendar_path: Path, days: int, provider=None, today=None, index: bool = False) -> int:
    from datetime import date, timedelta, timezone
    from investment_agent.market.prices import PriceStore, ingest
    from investment_agent.market.providers.vnstock_adapter import ProviderUnavailable, VnstockProvider
    provider = provider or VnstockProvider()
    today = today or date.today()
    cal = load_calendar(calendar_path)
    store = PriceStore(data_dir)
    start = max(today - timedelta(days=days), cal.first)
    loaded, failed = 0, []
    for symbol in symbols:
        try:
            fetch = provider.fetch_index if index else provider.fetch_prices
            bars = [b for b in fetch(symbol, start, today) if cal.first <= b.session_date <= cal.last and cal.is_session(b.session_date)]
            if not bars:
                continue
            # The scheduler syncs several times a day: unchanged prices add nothing, restated ones
            # become a new revision named by observation time rather than colliding with today's.
            stored = store.latest(bars[0].entity_id)
            if all(b.session_date in stored and _same_bar(b, stored[b.session_date][0]) for b in bars):
                continue
            observed = bars[0].observed_at.astimezone(timezone.utc)
            ingest(store, cal, bars, revision_id=f"vnstock-{observed:%Y%m%dT%H%M%S}-{start:%Y%m%d}")
            loaded += len(bars)
        except ProviderUnavailable as exc:
            print(json.dumps({"status": "not_configured", "reason": str(exc)}, ensure_ascii=False))
            return 2
        except Exception as exc:  # one failing symbol does not stop the others
            failed.append({"symbol": symbol, "error": getattr(exc, "code", type(exc).__name__)})
    print(json.dumps({"status": "ok" if not failed else "partial", "bars": loaded, "failed": failed}))
    return 0 if not failed else 1


def run_backup(data_dir: Path, backup_dir: Path, kind: str) -> int:
    import os
    from datetime import datetime, timezone

    from investment_agent.api.auth import OwnerContext
    from investment_agent.operations.backup import create_backup, due_backup_kind, export_personal, prune_backups
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable

    now = datetime.now(timezone.utc)
    if kind == "auto":
        kind = due_backup_kind(backup_dir, now)
        if kind is None:
            print(json.dumps({"status": "skipped", "reason": "not_due"}))
            return 0
    try:
        repo = personal_repository_from_env()
        export = export_personal(repo, OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "backup"), now=now)
    except (RepositoryUnavailable, KeyError):
        # A local-only copy is not a full backup: the personal source of truth is Firestore.
        print(json.dumps({"status": "not_configured", "reason": "personal_export_unavailable"}))
        return 2
    manifest = create_backup(data_dir, backup_dir, personal_export=export, now=now, kind=kind)
    removed = prune_backups(backup_dir)
    print(json.dumps({"status": "ok", "backup": manifest.path.name, "files": len(manifest.files), "pruned": len(removed)}))
    return 0


def scheduled_run(calendar_path: Path, data_dir: Path) -> int:
    """Prints a JSON summary without secrets. Exit 2 when configuration is missing; nothing runs then."""
    import os
    from datetime import datetime, timezone

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.jobs.runner import JobStore, LeaseBusy
    from investment_agent.jobs.schedule import scheduled_tick
    from zoneinfo import ZoneInfo

    from investment_agent.market.prices import PriceStore
    from investment_agent.market.view import EmptyMarket, StoreMarket
    VN = ZoneInfo("Asia/Ho_Chi_Minh")
    from investment_agent.notifications.outbox import DeliveryStore
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable
    from investment_agent.settings import Settings

    try:
        cal = load_calendar(calendar_path)
        repo = personal_repository_from_env()
    except (OSError, ValueError, KeyError, RepositoryUnavailable) as exc:
        print(json.dumps({"status": "not_configured", "reason": type(exc).__name__}))
        return 2
    settings = Settings.from_env()
    sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client()) if settings.telegram_bot_token else None
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    try:
        market = StoreMarket(PriceStore(data_dir), cal, today=lambda: datetime.now(VN).date()) if (data_dir / "prices").exists() else EmptyMarket()
        from investment_agent.market.leading import MacroStore, load_indicators, macro_reminders
        reminders = macro_reminders(load_indicators(), MacroStore(data_dir), today=datetime.now(VN).date())
        from investment_agent.brief.view import market_for_session
        from investment_agent.services.holdings_view import held_from_repo
        try:
            held = held_from_repo(repo, owner)
        except RepositoryUnavailable:
            held = set()
        result = scheduled_tick(repo=repo, owner=owner, market=market, jobs=JobStore(data_dir / "jobs.sqlite"), reminders=reminders,
                                market_for=market_for_session(data_dir, held),
                                deliveries=DeliveryStore(data_dir / "deliveries.sqlite"), sender=sender, cal=cal,
                                now=datetime.now(timezone.utc), worker_id=f"scheduler-{os.getpid()}")
    except LeaseBusy:
        print(json.dumps({"status": "busy"}))
        return 0
    except RepositoryUnavailable:
        print(json.dumps({"status": "repository_unavailable"}))
        return 1
    d = result.decision
    print(json.dumps({"status": "ok", "run": d.run, "reason": d.reason, "session": d.session_date.isoformat() if d.session_date else None,
                      "missed_sessions": d.missed_sessions, "reports": result.statuses, "delivered": len(result.delivered)}))
    return 0


def journal_cli(data_dir: Path) -> int:
    """Remind the owner of what they wrote when a journalled ticker moved another threshold step (default 15%) from the recorded price."""
    import os
    import uuid
    from decimal import Decimal

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.market.series import SeriesStore
    from investment_agent.notifications.render import split_message
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.services.journal import read_journal, review_run
    from investment_agent.services.records import notification_settings, portfolio_settings
    from investment_agent.settings import Settings

    settings = Settings.from_env()
    repo = personal_repository_from_env()
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    chosen, _ = notification_settings(repo, owner)
    if not (settings.telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    series = SeriesStore(Path(data_dir) / "trend-sources")
    prices = {}
    for symbol in {e.symbol for e in read_journal(repo, owner)[0]}:
        if closes := series.read(f"{symbol}-1d"):  # last close, thousand đồng
            prices[symbol] = Decimal(str(closes[-1][1])) * 1000
    sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
    out = review_run(repo, owner, prices=prices, threshold=portfolio_settings(repo, owner)[0].journal_review_threshold,
                     send=lambda text: all(sender.send(chosen.chat_id, part).status == "sent" for part in split_message(text)),
                     request_id=f"journal-review-{uuid.uuid4().hex[:16]}")
    print(json.dumps(out))
    return 0


def events_cli(data_dir: Path) -> int:
    """Refresh watched tickers' corporate events (paced for Vnstock) and send the 5-day reminder once per event."""
    import os
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import httpx

    from investment_agent.market.corporate_events import events_run, render_reminders
    from investment_agent.notifications.render import split_message
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.settings import Settings

    try:
        from vnstock import Company
    except ImportError:
        print(json.dumps({"status": "not_configured", "reason": "vnstock_missing"}))
        return 2
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    settings = Settings.from_env()

    def notify(due):
        if not settings.telegram_bot_token:
            return False
        from investment_agent.api.auth import OwnerContext
        from investment_agent.repositories.firestore import personal_repository_from_env
        from investment_agent.services.holdings_view import held_from_repo
        from investment_agent.services.records import notification_settings
        repo = personal_repository_from_env()
        owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
        chosen, _ = notification_settings(repo, owner)
        if not (chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
            return False
        try:
            held = held_from_repo(repo, owner)
        except Exception:
            held = set()
        sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
        text = render_reminders(due, held=held, today=now.date())
        return all(sender.send(chosen.chat_id, part).status == "sent" for part in split_message(text))

    out = events_run(data_dir, fetch=lambda symbol: Company(source="VCI", symbol=symbol).events().to_dict("records"), notify=notify, now=now)
    print(json.dumps(out, ensure_ascii=False))
    return 0


LISTING_MAX_AGE_DAYS = 7


def brief_snapshot_cli(data_dir: Path, calendar_path: Path, *, listing=None, board=None, http_get=None, now=None) -> int:
    """Builds data/brief/<latest session>.json; prints which sections are ok. Each source failing only blanks its section."""
    from datetime import datetime, timedelta, timezone

    from investment_agent.brief.snapshot import BriefStore, build_snapshot, latest_session
    from investment_agent.jobs.schedule import _previous_session
    from investment_agent.market.series import SeriesStore

    try:
        cal = load_calendar(calendar_path)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "not_configured", "reason": type(exc).__name__}))
        return 2
    now = now or datetime.now(timezone.utc)
    session = latest_session(now, cal)
    if session is None:
        print(json.dumps({"status": "no_session"}))
        return 0
    if listing is None or board is None or http_get is None:
        import httpx

        from investment_agent.market.providers import vnstock_adapter as va
        client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(30, connect=10), headers={"User-Agent": USER_AGENT})

        def fetch(url: str) -> str:
            response = client.get(url)
            response.raise_for_status()
            return response.text
        listing, board, http_get = listing or va.hose_listing, board or va.price_board, http_get or fetch
    cache = data_dir / "hose-listing.json"

    def cached_listing():
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            if now - datetime.fromisoformat(saved["at"]) < timedelta(days=LISTING_MAX_AGE_DAYS) and "icb_codes" in saved["listing"]:
                return saved["listing"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        fresh = listing()
        cache.write_text(json.dumps({"at": now.isoformat(), "listing": fresh}, ensure_ascii=False), encoding="utf-8")
        return fresh

    series = SeriesStore(data_dir / "trend-sources")
    snap = build_snapshot(session_date=session, previous_session=_previous_session(cal, session), now=now, listing=cached_listing,
                          board=board, series=lambda index_id: series.read(f"{index_id}-1d"), hose_get=http_get, rss_get=http_get,
                          store=BriefStore(data_dir))
    print(json.dumps({"status": "ok", "session": session.isoformat(),
                      "sections": {k: v["status"] for k, v in snap.items() if isinstance(v, dict) and "status" in v}}, ensure_ascii=False))
    return 0


USER_AGENT = "investment-agent/0.1 (personal use)"
MAX_PDF_BYTES = 40 * 1024 * 1024
MAX_PDF_SECONDS = 180


def _insight_notifier(data_dir: Path, calendar_path: Path, settings, client, now):
    """notify(store) for insights_run, or None when Telegram or the personal store is not configured.

    Ticker linking (watchlist, Định giá verdicts, holdings) happens here, locally, after the model call.
    """
    import os
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from investment_agent.api.auth import OwnerContext
    from investment_agent.insights.pipeline import FIRST_WINDOW_DAYS as WINDOW_DAYS
    from investment_agent.insights.summary import link, linking_sectors, summarise
    from investment_agent.insights.telegram import render_insight, send_new
    from investment_agent.market.watchlist import load_watchlist
    from investment_agent.market.prices import PriceStore
    from investment_agent.market.sectors import load_sectors
    from investment_agent.market.view import EmptyMarket, StoreMarket
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable
    from investment_agent.services.holdings_view import fair_value_board, held_from_repo
    from investment_agent.services.records import notification_settings

    if not settings.telegram_bot_token:
        return None
    try:
        repo = personal_repository_from_env()
        owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
        notify_settings, _ = notification_settings(repo, owner)
    except (OSError, ValueError, KeyError, RepositoryUnavailable):
        return None
    today = now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    try:
        market = StoreMarket(PriceStore(data_dir), load_calendar(calendar_path), today=lambda: today) if (data_dir / "prices").exists() else EmptyMarket()
        held = held_from_repo(repo, owner)
        rows = fair_value_board(data_dir, market, repo, owner, held=held, today=today)["rows"]
    except Exception:  # message still goes out, without verdicts
        held, rows = set(), []
    sectors = linking_sectors(load_sectors(data_dir)[0], watched=set(load_watchlist(data_dir).symbols), held=held)
    render = lambda record: render_insight(record, link(summarise([record]), sectors=sectors, valuation_rows=rows, held=held)["sectors"])
    sender = TelegramSender(settings.telegram_bot_token, client=client)
    since = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    return lambda store: send_new(store, sender, notify_settings, render, since=since)


def insights_cli(data_dir: Path, calendar_path: Path, *, min_hours: float = 6) -> int:
    """Prints a JSON summary without secrets or report contents."""
    import time
    from datetime import datetime, timezone

    import httpx

    from investment_agent.ai.budget import SpendLedger
    from investment_agent.ai.catalog import load_catalog
    from investment_agent.ai.openrouter import OpenRouterGateway, load_ai_policy
    from investment_agent.domain.pinned import CONFIG_DIR
    from investment_agent.insights.download import fetch_pdf
    from investment_agent.insights.pdf import extract_pages
    from investment_agent.insights.run import discover_sources, due, insights_run, record_status
    from investment_agent.insights.store import InsightStore
    from investment_agent.settings import Settings

    now = datetime.now(timezone.utc)
    if not due(data_dir, now=now, min_hours=min_hours):
        print(json.dumps({"status": "skipped", "reason": "recent_run"}))
        return 0
    client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=15), headers={"User-Agent": USER_AGENT})

    def get(url: str) -> str:
        time.sleep(1)  # polite pacing between page fetches
        response = client.get(url)
        response.raise_for_status()
        return response.text

    def download(url: str) -> bytes:
        return fetch_pdf(client, url, max_bytes=MAX_PDF_BYTES, max_seconds=MAX_PDF_SECONDS)

    store = InsightStore(data_dir / "insights")

    source_errors: dict[str, str] = {}

    def discover(since):
        return discover_sources(get, store, since=since, errors=source_errors)

    settings = Settings.from_env()
    gateway = None
    if settings.openrouter_api_key:
        try:
            catalog = load_catalog(data_dir / "ai" / "catalog.json", get, now=now)
        except Exception:
            out = {"status": "stopped:catalog_unavailable", "processed": []}
            record_status(data_dir, now=now, out=out)
            print(json.dumps(out))
            return 1
        gateway = OpenRouterGateway(settings, load_ai_policy(CONFIG_DIR / "ai-policy.json"), catalog,
                                    SpendLedger(data_dir / "ai" / "spend.sqlite"), client=httpx.Client())
    out = insights_run(data_dir, ssi_get=get, discover=discover, download=download, pages=extract_pages, gateway=gateway,
                       notify=_insight_notifier(data_dir, calendar_path, settings, httpx.Client(), now), now=now, sleep=time.sleep)
    if source_errors:
        out["source_errors"] = source_errors
        record_status(data_dir, now=now, out=out)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
