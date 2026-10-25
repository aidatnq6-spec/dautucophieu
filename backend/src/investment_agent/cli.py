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
    trend = commands.add_parser("trend-run", help="build the Xu hướng board after 15:30 on trading days")
    trend.add_argument("--data-dir", type=Path, required=True)
    trend.add_argument("--calendar", type=Path, required=True)
    sectors = commands.add_parser("industries", help="save ICB level-2 sectors of the synced tickers for the market page")
    sectors.add_argument("--symbols", required=True, help="comma-separated tickers, or @file with one ticker per line")
    sectors.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "vnstock-audit":
        return vnstock_audit(_symbols(args.symbols), args.output_dir)
    if args.command == "index-groups":
        return index_groups([g.strip().upper() for g in args.groups.split(",") if g.strip()], args.output)
    if args.command == "market-sync":
        return market_sync(_symbols(args.symbols), args.data_dir, args.calendar, args.days, index=args.index)
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
        result = scheduled_tick(repo=repo, owner=owner, market=market, jobs=JobStore(data_dir / "jobs.sqlite"),
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


if __name__ == "__main__":
    raise SystemExit(main())
