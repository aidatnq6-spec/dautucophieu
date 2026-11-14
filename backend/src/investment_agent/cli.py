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
    bs = commands.add_parser("beta-sync", help="beta of every watched ticker (VNDirect, one call) into data/beta.json for the CAPM hint")
    bs.add_argument("--data-dir", type=Path, required=True)
    es = commands.add_parser("erp-sync", help="Damodaran's equity risk premium for Vietnam into data/erp.json, at most weekly")
    es.add_argument("--data-dir", type=Path, required=True)
    fn = commands.add_parser("fund-nav-sync", help="NAV/đơn vị of every open-ended fund from Fmarket into data/fund-nav.json, one call")
    fn.add_argument("--data-dir", type=Path, required=True)
    fh = commands.add_parser("fund-holdings-sync", help="every open-ended fund's published top holdings from Fmarket into data/fund-holdings.json, "
                             "a fund read again only when its month changes")
    fh.add_argument("--data-dir", type=Path, required=True)
    ic = commands.add_parser("index-closes-rebuild", help="rebuild VN-Index and VN30 daily closes in points (VNDirect from 08/2017, CafeF before), "
                             "after a backup into backups/; run once")
    ic.add_argument("--data-dir", type=Path, required=True)
    gp = commands.add_parser("gold-price-sync", help="Phú Quý's gold buying and selling prices per chỉ into data/gold-price.json, one page")
    gp.add_argument("--data-dir", type=Path, required=True)
    wb = commands.add_parser("weekly-brief", help="Bản tin tuần over Telegram on the weekend, once per week")
    wb.add_argument("--data-dir", type=Path, required=True)
    wb.add_argument("--calendar", type=Path, required=True)
    ia = commands.add_parser("insider-alerts", help="Telegram note for new insider or major-shareholder notices of held tickers")
    ia.add_argument("--data-dir", type=Path, required=True)
    pa = commands.add_parser("price-alerts", help="during the session, Telegram note for the owner's price levels crossed")
    pa.add_argument("--data-dir", type=Path, required=True)
    sc = commands.add_parser("screen-check", help="Bộ lọc tín hiệu: Telegram note for tickers new to a saved screen, after the close")
    sc.add_argument("--data-dir", type=Path, required=True)
    sc.add_argument("--calendar", type=Path, required=True)
    tc = commands.add_parser("thesis-check", help="Luận điểm đầu tư: check the owner's conditions and send a Telegram note for those broken")
    tc.add_argument("--data-dir", type=Path, required=True)
    tc.add_argument("--calendar", type=Path, required=True)
    tc.add_argument("--scope", choices=("price", "data"), required=True)
    lc = commands.add_parser("lights-check", help="Telegram when a colour on Bảng đèn chỉ báo sớm changes")
    lc.add_argument("--data-dir", type=Path, required=True)
    hc = commands.add_parser("health-check", help="Telegram once for each new problem with the unattended work, and when it recovers")
    hc.add_argument("--data-dir", type=Path, required=True)
    bd = commands.add_parser("backup-drill", help="restore the newest backup into a temporary folder, once a week")
    bd.add_argument("--data-dir", type=Path, required=True)
    bd.add_argument("--force", action="store_true", help="run now even if the last drill is under a week old")
    qa = commands.add_parser("quarter-alerts", help="Telegram note when a watched ticker's new quarter first appears in the statements")
    qa.add_argument("--data-dir", type=Path, required=True)
    frs = commands.add_parser("financial-ratios-sync", help="quarterly bank, securities and insurance ratios (VNDirect) into data/financial-ratios")
    frs.add_argument("--data-dir", type=Path, required=True)
    bns = commands.add_parser("bank-notes-sync", help="loans by group and deposits by kind of watched banks (Vietcap notes, 10 s apart, weekly) into data/bank-notes")
    bns.add_argument("--data-dir", type=Path, required=True)
    bns.add_argument("--force", action="store_true", help="refresh every watched bank now, however recent its record")
    vcs = commands.add_parser("valuation-check-sync", help="VNDirect's market value, P/E and P/B of each watched ticker, to compare with Bảng số tài chính")
    vcs.add_argument("--data-dir", type=Path, required=True)
    ivs = commands.add_parser("index-valuation-sync", help="fetch daily P/E and P/B of VNINDEX and VN30 (VNDirect) into data/index-valuation")
    ivs.add_argument("--data-dir", type=Path, required=True)
    ihist = commands.add_parser("index-history", help="work out VN-Index P/E and P/B before VNDirect's series from today's HOSE tickers (one-off, ~15 min)")
    ihist.add_argument("--data-dir", type=Path, required=True)
    psync = commands.add_parser("plans-sync", help="business plans of watched tickers from CafeF (current year) into data/annual-plans-cafef")
    psync.add_argument("--data-dir", type=Path, required=True)
    ssync = commands.add_parser("statements-sync", help="full statements of watched tickers (VNDirect) for Bảng số tài chính; banks, securities firms and insurers apart")
    ssync.add_argument("--data-dir", type=Path, required=True)
    ssync.add_argument("--limit", type=int, default=8)
    ssync.add_argument("--all", action="store_true", help="every watched ticker, for the first load")
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
    deposits = commands.add_parser("deposit-alerts", help="Sổ tiết kiệm: Telegram once per sổ from the day before it matures")
    deposits.add_argument("--data-dir", type=Path, required=True)
    loans = commands.add_parser("loan-alerts", help="Khoản vay and bảo hiểm: Telegram once per loan 90 days before its promotion ends, and per premium 30 days before it is due")
    loans.add_argument("--data-dir", type=Path, required=True)
    contrib = commands.add_parser("contribution-remind", help="Góp vốn đều: Telegram once a month from the contribution day until it is met")
    contrib.add_argument("--data-dir", type=Path, required=True)
    accumulation = commands.add_parser("accumulation-remind", help="Kế hoạch tích sản: Telegram once per plan and month from its day until it is met")
    accumulation.add_argument("--data-dir", type=Path, required=True)
    drawdown = commands.add_parser("drawdown-check", help="full price history for drawdowns; Telegram when a holding falls past the threshold")
    drawdown.add_argument("--data-dir", type=Path, required=True)
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
    if args.command == "index-history":
        return index_history_cli(args.data_dir)
    if args.command == "plans-sync":
        return plans_sync(args.data_dir)
    if args.command == "statements-sync":
        return statements_sync(args.data_dir, limit=None if args.all else args.limit)
    if args.command == "fundamentals-sync":
        return fundamentals_sync(args.data_dir, limit=None if args.all or args.symbols else args.limit,
                                 symbols=_symbols(args.symbols) if args.symbols else None)
    if args.command == "trend-run":
        return trend_run(args.data_dir, args.calendar)
    if args.command == "macro-sync":
        return macro_sync(args.data_dir)
    if args.command == "index-valuation-sync":
        return index_valuation_sync(args.data_dir)
    if args.command == "beta-sync":
        return beta_sync(args.data_dir)
    if args.command == "erp-sync":
        return erp_sync_cli(args.data_dir)
    if args.command == "fund-nav-sync":
        return fund_nav_sync_cli(args.data_dir)
    if args.command == "fund-holdings-sync":
        return fund_holdings_sync_cli(args.data_dir)
    if args.command == "gold-price-sync":
        return gold_price_sync_cli(args.data_dir)
    if args.command == "index-closes-rebuild":
        return index_closes_cli(args.data_dir)
    if args.command == "lights-check":
        return lights_check_cli(args.data_dir)
    if args.command == "health-check":
        return health_check_cli(args.data_dir)
    if args.command == "backup-drill":
        return backup_drill_cli(args.data_dir, force=args.force)
    if args.command == "quarter-alerts":
        return quarter_alerts_cli(args.data_dir)
    if args.command == "weekly-brief":
        return weekly_brief_cli(args.data_dir, args.calendar)
    if args.command == "insider-alerts":
        return insider_alerts_cli(args.data_dir)
    if args.command == "price-alerts":
        return price_alerts_cli(args.data_dir)
    if args.command == "screen-check":
        return screen_check_cli(args.data_dir, args.calendar)
    if args.command == "thesis-check":
        return thesis_check_cli(args.data_dir, args.calendar, args.scope)
    if args.command == "financial-ratios-sync":
        return financial_ratios_sync(args.data_dir)
    if args.command == "valuation-check-sync":
        return valuation_check_sync(args.data_dir)
    if args.command == "bank-notes-sync":
        return bank_notes_sync(args.data_dir, force=args.force)
    if args.command == "industries":
        return industries(_symbols(args.symbols), args.output)
    if args.command == "backup":
        return run_backup(args.data_dir, args.backup_dir, args.kind)
    if args.command == "scheduled-run":
        return scheduled_run(args.calendar, args.data_dir)
    if args.command == "deposit-alerts":
        return deposit_alerts_cli(args.data_dir)
    if args.command == "loan-alerts":
        return loan_alerts_cli(args.data_dir)
    if args.command == "contribution-remind":
        return contribution_cli(args.data_dir)
    if args.command == "accumulation-remind":
        return accumulation_cli(args.data_dir)
    if args.command == "drawdown-check":
        return drawdown_cli(args.data_dir)
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


def _read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def index_groups(groups: list[str], output: Path, provider=None, today=None, get=None) -> int:
    """VN30 from VNDirect (its listing marks VN30 members only); the other groups have no public source since Vnstock 6.0.0, so their
    saved members are kept with the day they were taken ("kept"), never worked out."""
    from datetime import date
    if provider is None:
        from investment_agent.market.providers import vndirect_data as vd
        today = today or date.today()
        saved = _read_json(output)
        members, kept = {}, {}
        for g in groups:
            fresh = vd.index_members(g, get=get or vd.default_get)
            if fresh:
                members[g] = fresh
            elif g in saved.get("groups", {}):
                members[g] = saved["groups"][g]
                kept[g] = (saved.get("kept") or {}).get(g) or saved.get("as_of")
        payload = {"as_of": today.isoformat(), "source": "vndirect:finfo", "groups": members, "kept": kept}
        # VN30 changing is HOSE's review of its baskets: VN100, which has no public source, may have changed the same day.
        before = saved.get("groups", {}).get("VN30")
        if "VN30" in members and before is not None and sorted(before) != sorted(members["VN30"]):
            payload["vn30_changed_on"] = today.isoformat()
        elif saved.get("vn30_changed_on"):
            payload["vn30_changed_on"] = saved["vn30_changed_on"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "groups": {g: len(m) for g, m in members.items()}, "kept": kept}))
        return 0
    from investment_agent.market.providers.vnstock_adapter import SOURCE, ProviderUnavailable
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


# Months with quarterly or annual report deadlines: 17 tickers older than 3 days a night covers the 50 watched in 3 days.
REPORTING_MONTHS = (1, 2, 4, 5, 7, 8, 10, 11)


def index_history_cli(data_dir: Path, *, get=None, now=None, sleep=None) -> int:
    """Fetch what is missing, work the series out, compare it with VNDirect month by month and keep the days before VNDirect's first."""
    import time
    from datetime import datetime, timezone
    from investment_agent.market.index_history import IndexHistoryStore, build_history, compare, compute_index, top_members
    from investment_agent.market.series import SeriesStore
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    symbols = json.loads((data_dir / "hose-listing.json").read_text(encoding="utf-8"))["listing"]["symbols"]
    store = IndexHistoryStore(data_dir / "index-history")
    built = build_history(store, symbols, get=get, now=now or datetime.now(timezone.utc), sleep=sleep or time.sleep)
    records = {s: rec for s in symbols if (rec := store.read(s))}
    multiples = SeriesStore(data_dir / "index-valuation")
    checks = {}
    # VN-Index: every ticker; VN30: an estimated basket, the thirty largest by capitalisation each half-year.
    for index, basket, members in (("VNINDEX", "all", None), ("VN30", "top30", top_members(records, size=30))):
        calc = compute_index(records, members=members)
        vnd = {k: multiples.read(f"{index}-{k}-1d") for k in ("pe", "pb")}
        first = min((p[0][0].date() for p in vnd.values() if p), default=None)
        check = {**compare(calc, vnd), "tickers": len(records), "basket": basket, "vndirect_from": first.isoformat() if first else None}
        for k in ("pe", "pb"):
            multiples.upsert(f"{index}-{k}-calc-1d", [(datetime.combine(d, datetime.min.time()), format(v[k], "f")) for d, v in sorted(calc.items())
                                                     if first is None or d < first])
        (data_dir / "index-valuation" / f"{index}-calc-check.json").write_text(json.dumps(check, ensure_ascii=False), encoding="utf-8")
        checks[index] = check
    failed = {k: v for k, v in built.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "built": built, "compare": checks["VNINDEX"], "vn30": checks["VN30"]},
                     ensure_ascii=False))
    return 0 if not failed else 1


def plans_sync(data_dir: Path, *, get=None, now=None, sleep=None) -> int:
    """Exit 0 unless a ticker failed to load; a ticker whose plan has no figures (banks write theirs in words) is not a failure."""
    import time
    from datetime import datetime, timezone
    from investment_agent.market.plans_cafef import PlanStore, sync_plans
    from investment_agent.market.watchlist import load_watchlist
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    results = sync_plans(PlanStore(data_dir / "annual-plans-cafef"), list(load_watchlist(data_dir).symbols), get=get,
                         now=now or datetime.now(timezone.utc), sleep=sleep or time.sleep)
    failed = {k: v for k, v in results.items() if v.startswith("error:")}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}, ensure_ascii=False))
    return 0 if not failed else 1


def statements_sync(data_dir: Path, *, limit: int | None, get=None, now=None, sleep=None) -> int:
    """Exit 0 when every ticker due was refreshed, 1 when some failed (each is reported)."""
    import time
    from datetime import datetime, timezone
    from investment_agent.market.sectors import load_sectors
    from investment_agent.market.statements import StatementStore, sync_statements
    from investment_agent.market.watchlist import load_watchlist
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    sectors = load_sectors(data_dir)[0]
    watched = {s: sectors.get(s) for s in load_watchlist(data_dir).symbols}
    now = now or datetime.now(timezone.utc)
    results = sync_statements(StatementStore(data_dir / "statements"), watched, get=get, now=now, limit=limit, sleep=sleep or time.sleep)
    results |= sync_statements(StatementStore(data_dir / "statements-financial"), watched, get=get, now=now, limit=limit, sleep=sleep or time.sleep,
                               kinds=("bank", "securities", "insurance"))  # their own layouts, apart from the statements other features read
    failed = {k: v for k, v in results.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}, ensure_ascii=False))
    return 0 if not failed else 1


def fundamentals_sync(data_dir: Path, *, limit: int | None, symbols: list[str] | None = None, provider=None, now=None, sleep=None) -> int:
    import time
    from datetime import datetime, timezone
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.fundamentals_vndirect import VndirectFundamentals
    from investment_agent.market.providers.vnstock_adapter import VnstockProvider
    from investment_agent.market.series import SeriesStore
    from investment_agent.market.watchlist import load_watchlist
    now = now or datetime.now(timezone.utc)
    # Named tickers are refreshed now (max age 0); otherwise the stalest watched tickers, more often in the months reports are due.
    max_age, limit = (0, limit) if symbols else (3, max(limit or 0, 17)) if now.month in REPORTING_MONTHS else (7, limit)
    out = sync_fundamentals(FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources"),
                            symbols or list(load_watchlist(data_dir).symbols), provider=provider or VndirectFundamentals(data_dir, prices=VnstockProvider()),
                            now=now, limit=limit, max_age_days=max_age, sleep=sleep or time.sleep)
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


MACRO_TIMEOUTS = ("error:ReadTimeout", "error:ConnectTimeout", "error:WriteTimeout", "error:PoolTimeout")
MACRO_SLOW_PAUSE = 30  # seconds before asking a slow source again
MACRO_SLOW_TIMEOUT = 90


def macro_sync(data_dir: Path, get=None, slow_get=None, sleep=None) -> int:
    """Exit 0 when every automatic indicator updated, 1 when some failed (each is reported). Indicators whose source timed out are
    asked once more after a pause, with a longer wait (stockbiz is often slow)."""
    import time
    from investment_agent.market.leading import MacroStore, fetch_auto, fetch_commodities, fetch_factors, load_indicators

    def fetcher(timeout):
        import httpx

        def fetch(url):
            response = httpx.get(url, timeout=timeout, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
        return fetch
    get, slow_get, sleep = get or fetcher(30), slow_get or fetcher(MACRO_SLOW_TIMEOUT), sleep or time.sleep
    indicators = load_indicators()
    results = fetch_auto(indicators, MacroStore(data_dir), get=get, sleep=sleep)
    results.update(fetch_factors(MacroStore(data_dir), get=get, sleep=sleep))  # long oil and US dollar history for the sensitivity reading
    results.update(fetch_commodities(MacroStore(data_dir), get=get, sleep=sleep))  # monthly world prices for Chuỗi giá trị
    slow = [i for i in indicators if results.get(i["id"]) in MACRO_TIMEOUTS]
    if slow:
        sleep(MACRO_SLOW_PAUSE)
        results.update(fetch_auto(slow, MacroStore(data_dir), get=slow_get, sleep=sleep))
    failed = {k: v for k, v in results.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}))
    return 0 if not failed else 1


def financial_ratios_sync(data_dir: Path, get=None, today=None) -> int:
    """Exit 0 when every watched financial ticker updated, 1 when some failed (each is reported)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from investment_agent.market.financial_ratios import FinancialRatioStore, fetch_financial_ratios
    from investment_agent.market.sectors import load_sectors
    from investment_agent.market.watchlist import load_watchlist
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    sectors = load_sectors(data_dir)[0]
    watched = {s: sectors.get(s) for s in load_watchlist(data_dir).symbols}
    results = fetch_financial_ratios(FinancialRatioStore(data_dir / "financial-ratios"), watched, get=get,
                                     today=today or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date())
    failed = {k: v for k, v in results.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}))
    return 0 if not failed else 1


def valuation_check_sync(data_dir: Path, get=None, today=None) -> int:
    """Exit 0 when every watched ticker was read, 1 when some failed (each is reported)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from investment_agent.market.valuation_check import ValuationCheckStore, fetch_checks
    from investment_agent.market.watchlist import load_watchlist
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    results = fetch_checks(ValuationCheckStore(data_dir / "valuation-check"), list(load_watchlist(data_dir).symbols), get=get,
                           today=today or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date())
    failed = {k: v for k, v in results.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "read": len(results) - len(failed), "failed": failed}))
    return 0 if not failed else 1


def bank_notes_sync(data_dir: Path, get=None, sleep=None, force: bool = False) -> int:
    """Exit 0 when every due watched bank updated (or none was due), 1 when some failed (each is reported)."""
    import time

    from investment_agent.market.bank_notes import BankNoteStore, sync_bank_notes
    from investment_agent.market.sectors import load_sectors
    from investment_agent.market.watchlist import load_watchlist
    if get is None:
        import httpx

        def get(url):
            # This application's own name; no browser headers. Vietcap answers 418 to callers faster than its Crawl-delay.
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    sectors = load_sectors(data_dir)[0]
    watched = {s: sectors.get(s) for s in load_watchlist(data_dir).symbols}
    results = sync_bank_notes(BankNoteStore(data_dir / "bank-notes"), watched, get=get, sleep=sleep or time.sleep, force=force)
    failed = {k: v for k, v in results.items() if v.startswith("error")}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}))
    return 0 if not failed else 1


def index_valuation_sync(data_dir: Path, get=None, today=None) -> int:
    """Exit 0 when the four index series updated, 1 when some failed (each is reported)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from investment_agent.market.index_valuation import fetch_index_valuation
    from investment_agent.market.series import SeriesStore
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    today = today or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    results = fetch_index_valuation(SeriesStore(data_dir / "index-valuation"), get=get, today=today)
    failed = {k: v for k, v in results.items() if v != "ok"}
    print(json.dumps({"status": "ok" if not failed else "partial", "results": results}))
    return 0 if not failed else 1


def industries(symbols: list[str], output: Path, provider=None, today=None, get=None) -> int:
    """ICB level-2 sectors of the watched tickers. Without a provider: VNDirect's classification, named as the application names
    sectors (the names in hose-listing.json, which decide banks, securities firms and insurers). A ticker already classified keeps
    its sector; where VNDirect classifies it differently, the difference is reported for the owner, not applied."""
    from datetime import date
    if provider is None:
        from investment_agent.market.providers import vndirect_data as vd
        today = today or date.today()
        saved = _read_json(output).get("sectors", {})
        names = (_read_json(Path(output).parent / "hose-listing.json").get("listing") or {}).get("icb_names", {})
        found = vd.sector_codes(get=get or vd.default_get)
        mapped = {s: names.get(code, vnd_name) for s, (code, vnd_name) in found.items()}
        sectors, added, differ = {}, [], []
        for s in symbols:
            if s in saved:
                sectors[s] = saved[s]
                if s in mapped and mapped[s] != saved[s]:
                    differ.append({"symbol": s, "kept": saved[s], "vndirect": mapped[s]})
            elif s in mapped:
                sectors[s] = mapped[s]
                added.append(s)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"as_of": today.isoformat(), "source": "vndirect:finfo", "level": 2, "sectors": dict(sorted(sectors.items()))},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "classified": len(sectors), "added": sorted(added), "unclassified": sorted(set(symbols) - set(sectors)),
                          "differ": differ}, ensure_ascii=False))
        return 0
    from investment_agent.market.providers.vnstock_adapter import ProviderUnavailable
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


MINUTE_LIMIT_WAIT = 60  # Vnstock Cộng đồng: 60 calls a minute; a ticker refused for it is tried once more after the minute has passed


def market_sync(symbols: list[str], data_dir: Path, calendar_path: Path, days: int, provider=None, today=None, index: bool = False,
                sleep=None) -> int:
    import time
    from datetime import date, timedelta, timezone
    from investment_agent.market.prices import PriceStore, ingest
    from investment_agent.market.providers.vnstock_adapter import ProviderUnavailable, VnstockProvider
    provider = provider or VnstockProvider()
    today = today or date.today()
    cal = load_calendar(calendar_path)
    store = PriceStore(data_dir)
    start = max(today - timedelta(days=days), cal.first)
    loaded, failed = 0, []
    sleep = sleep or time.sleep

    def one(symbol: str) -> int:
        fetch = provider.fetch_index if index else provider.fetch_prices
        bars = [b for b in fetch(symbol, start, today) if cal.first <= b.session_date <= cal.last and cal.is_session(b.session_date)]
        if not bars:
            return 0
        # The scheduler syncs several times a day: unchanged prices add nothing, restated ones
        # become a new revision named by observation time rather than colliding with today's.
        stored = store.latest(bars[0].entity_id)
        if all(b.session_date in stored and _same_bar(b, stored[b.session_date][0]) for b in bars):
            return 0
        observed = bars[0].observed_at.astimezone(timezone.utc)
        ingest(store, cal, bars, revision_id=f"vnstock-{observed:%Y%m%dT%H%M%S}-{start:%Y%m%d}")
        return len(bars)

    for attempt in (1, 2):
        retry = []
        for symbol in symbols:
            try:
                loaded += one(symbol)
            except ProviderUnavailable as exc:
                print(json.dumps({"status": "not_configured", "reason": str(exc)}, ensure_ascii=False))
                return 2
            except Exception as exc:  # one failing symbol does not stop the others
                code = getattr(exc, "code", type(exc).__name__)
                if attempt == 1 and "MINUTE_LIMIT" in str(code):
                    retry.append(symbol)
                else:
                    failed.append({"symbol": symbol, "error": code})
        if not retry:
            break
        sleep(MINUTE_LIMIT_WAIT)
        symbols = retry
    print(json.dumps({"status": "ok" if not failed else "partial", "bars": loaded, "failed": failed}))
    return 0 if not failed else 1


def run_backup(data_dir: Path, backup_dir: Path, kind: str) -> int:
    import os
    from datetime import datetime, timezone

    from investment_agent.api.auth import OwnerContext
    from investment_agent.operations.backup import BackupError, backup_key_from_env, create_backup, due_backup_kind, export_personal, prune_backups
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable

    now = datetime.now(timezone.utc)
    if kind == "auto":
        kind = due_backup_kind(backup_dir, now)
        if kind is None:
            print(json.dumps({"status": "skipped", "reason": "not_due"}))
            return 0
    try:  # backups get copied off this machine: without a usable key, none is written
        key = backup_key_from_env()
    except BackupError:
        key = None
    if key is None:
        print(json.dumps({"status": "not_configured", "reason": "backup_key_missing"}))
        return 2
    try:
        repo = personal_repository_from_env()
        export = export_personal(repo, OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "backup"), now=now)
    except (RepositoryUnavailable, KeyError):
        # A local-only copy is not a full backup: the personal source of truth is Firestore.
        print(json.dumps({"status": "not_configured", "reason": "personal_export_unavailable"}))
        return 2
    manifest = create_backup(data_dir, backup_dir, personal_export=export, now=now, kind=kind, encryption_key=key)
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


def accumulation_cli(data_dir: Path) -> int:
    """Remind once per plan and month, from the plan's day, while the month's purchases are below the plan."""
    import os
    import uuid
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.services.accumulation import remind_run
    from investment_agent.services.records import notification_settings
    from investment_agent.settings import Settings

    settings = Settings.from_env()
    repo = personal_repository_from_env()
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    chosen, _ = notification_settings(repo, owner)

    def send(text):
        if not (settings.telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
            return False
        sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
        return _part_sender(sender, chosen.chat_id, data_dir)(text)
    out = remind_run(repo, owner, today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date(), send=send, request_id=f"accumulation-{uuid.uuid4().hex[:16]}")
    print(json.dumps(out))
    return 0


def contribution_cli(data_dir: Path) -> int:
    """Remind once a month, from the plan's day, while this month's deposits are below the planned contribution."""
    import os
    import uuid
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.services.contributions import remind_run
    from investment_agent.services.records import notification_settings
    from investment_agent.settings import Settings

    settings = Settings.from_env()
    repo = personal_repository_from_env()
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    chosen, _ = notification_settings(repo, owner)

    def send(text):
        if not (settings.telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
            return False
        sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
        return _part_sender(sender, chosen.chat_id, data_dir)(text)
    out = remind_run(repo, owner, today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date(), send=send,
                     request_id=f"contribution-{uuid.uuid4().hex[:16]}")
    print(json.dumps(out))
    return 0


def drawdown_cli(data_dir: Path) -> int:
    """Fill full daily history for VN-Index and held tickers (once each, paced for Vnstock), then remind once per threshold crossing."""
    import os
    import time
    import uuid

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.services.drawdown import drawdown_run
    from investment_agent.services.records import notification_settings
    from investment_agent.settings import Settings

    from investment_agent.market.providers.vnstock_adapter import VnstockProvider
    settings = Settings.from_env()
    repo = personal_repository_from_env()
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    chosen, _ = notification_settings(repo, owner)
    provider = VnstockProvider()  # daily closes from VNDirect since Vnstock 6.0.0 (thousand đồng, adjusted, as before)

    def fetch(symbol, start, end):
        time.sleep(0.3)
        return provider.fetch_closes(symbol, start, end, interval="1D", index=False)

    def send(text):
        if not (settings.telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
            return False
        sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
        return _part_sender(sender, chosen.chat_id, data_dir)(text)
    out = drawdown_run(repo, owner, data_dir, fetch=fetch, send=send, request_id=f"drawdown-{uuid.uuid4().hex[:16]}")
    print(json.dumps(out))
    return 0


def beta_sync(data_dir: Path, get=None) -> int:
    """Exit 0 when the call succeeded (tickers without a beta are listed), 1 when it failed."""
    from investment_agent.market.beta import BetaStore, fetch_betas
    from investment_agent.market.watchlist import load_watchlist
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    try:
        out = fetch_betas(BetaStore(data_dir), list(load_watchlist(data_dir).symbols), get=get)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": type(exc).__name__}))
        return 1
    print(json.dumps(out))
    return 0


def erp_sync_cli(data_dir: Path, get=None) -> int:
    """Exit 0 when the premium is stored or still fresh, 1 when the book could not be read (the old value stays)."""
    from datetime import datetime, timezone

    from investment_agent.market.erp import ErpStore, erp_sync
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.content, response.headers.get("last-modified")
    out = erp_sync(ErpStore(data_dir), get=get, now=datetime.now(timezone.utc))
    print(json.dumps(out))
    return 1 if out["status"] == "error" else 0


def fund_nav_sync_cli(data_dir: Path, *, post=None) -> int:
    """Public fund NAVs for Sổ tài sản's fund rows; the request names no fund, so nothing about the owner is sent."""
    from datetime import datetime, timezone

    from investment_agent.market.fund_nav import FundNavStore, fund_nav_sync
    if post is None:
        import httpx

        def post(url, body):
            response = httpx.post(url, json=body, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.json()
    out = fund_nav_sync(FundNavStore(data_dir), post=post, now=datetime.now(timezone.utc))
    print(json.dumps(out))
    return 1 if out["status"] == "error" else 0


def index_closes_cli(data_dir: Path, *, get=None, today=None, sleep=None) -> int:
    """Rebuilds VNINDEX-1d and VN30-1d in points; the files held before are copied into backups/index-closes-<date>/ first."""
    import shutil
    import time
    from datetime import date

    from investment_agent.market.index_closes import rebuild_index_history
    from investment_agent.market.series import SeriesStore
    if get is None:
        import httpx

        def get(url: str) -> str:
            response = httpx.get(url, timeout=60, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    today = today or date.today()
    store = SeriesStore(Path(data_dir) / "trend-sources")
    backup = Path(data_dir).parent / "backups" / f"index-closes-{today.isoformat()}"
    results = []
    for index in ("VNINDEX", "VN30"):
        held = store.root / f"{index}-1d.json"
        if held.is_file():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(held, backup / held.name)
        try:
            results.append(rebuild_index_history(store, index, get=get, today=today, sleep=sleep or time.sleep))
        except Exception as exc:  # noqa: BLE001 - a source down leaves the series as it was
            results.append({"status": "error", "reason": type(exc).__name__, "index": index})
    print(json.dumps({"results": results, "backup": str(backup)}, ensure_ascii=False))
    return 0 if all(r["status"] == "ok" for r in results) else 1


def fund_holdings_sync_cli(data_dir: Path, *, post=None, get=None) -> int:
    """Every fund's published holdings (Fmarket); every fund is read, so nothing tells which ones the owner holds."""
    from datetime import datetime, timezone

    import httpx

    from investment_agent.market.fund_holdings import FundHoldingsStore, fund_holdings_sync
    headers = {"User-Agent": "investment-agent/0.1 (personal use)"}
    if post is None:
        def post(url, body):
            response = httpx.post(url, json=body, timeout=30, follow_redirects=False, headers=headers)
            response.raise_for_status()
            return response.json()
    if get is None:
        def get(url):
            response = httpx.get(url, timeout=30, follow_redirects=False, headers=headers)
            response.raise_for_status()
            return response.text
    out = fund_holdings_sync(FundHoldingsStore(data_dir), post=post, get=get, now=datetime.now(timezone.utc))
    print(json.dumps(out))
    return 1 if out["status"] == "error" else 0


def gold_price_sync_cli(data_dir: Path, *, get=None) -> int:
    """Phú Quý's public gold price table for Sổ tài sản's gold rows; the request names nothing about the owner."""
    from datetime import datetime, timezone

    from investment_agent.market.gold_price import GoldPriceStore, gold_price_sync
    if get is None:
        import httpx

        def get(url):
            response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
            response.raise_for_status()
            return response.text
    out = gold_price_sync(GoldPriceStore(data_dir), get=get, now=datetime.now(timezone.utc))
    print(json.dumps(out))
    return 1 if out["status"] == "error" else 0


def quarter_alerts_cli(data_dir: Path) -> int:
    """Báo cáo quý mới over Telegram; skipped entirely while scheduled delivery is off, so turning it on starts from a baseline."""
    import os

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.services.quarter_alerts import quarter_alerts_run
    from investment_agent.services.records import notification_settings
    from investment_agent.settings import Settings

    settings = Settings.from_env()
    repo = personal_repository_from_env()
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    chosen, _ = notification_settings(repo, owner)
    if not (settings.telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
    out = quarter_alerts_run(data_dir, send=_part_sender(sender, chosen.chat_id, data_dir), repo=repo, owner=owner)
    print(json.dumps(out))
    return 0


def _part_sender(sender, chat_id: str, data_dir: Path):
    """Send a note in parts that are never sent twice: parts left after a failure go out first next time (see PartSender)."""
    from investment_agent.notifications.part_sender import PartSender
    return PartSender(lambda part: sender.send(chat_id, part).status == "sent", Path(data_dir) / "alerts" / "telegram_pending.json")


def lights_check_cli(data_dir: Path) -> int:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from investment_agent.services.early_lights import lights_check
    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    send, repo, owner = telegram
    print(json.dumps(lights_check(repo, owner, data_dir, send=send, today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date())))
    return 0


def health_check_cli(data_dir: Path, telegram=None) -> int:
    """Compares the report with what was announced; Firestore and Telegram are touched only when something changed. Exit 0 either way:
    a problem found is the check working."""
    from datetime import datetime, timezone

    from investment_agent.domain.pinned import CONFIG_DIR
    from investment_agent.services.system_health import alert_changes, health_report, render_changes
    now = datetime.now(timezone.utc)
    try:  # the brief check needs this year's trading calendar; without it the other checks still run
        calendar = load_calendar(CONFIG_DIR / f"trading-calendar-hose-{now.year}.json")
    except (OSError, ValueError, KeyError):
        calendar = None
    report = health_report(data_dir, now=now, calendar=calendar)
    new, recovered = alert_changes(report["problems"], data_dir, save=False)
    if not new and not recovered:
        print(json.dumps({"status": "ok", "problems": len(report["problems"]), "sent": False}))
        return 0
    chosen = telegram(data_dir) if telegram else _scheduled_telegram(data_dir)
    if chosen is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off", "problems": len(report["problems"])}))
        return 0
    sent = bool(chosen[0](render_changes(new, recovered)))
    if sent:
        alert_changes(report["problems"], data_dir, save=True)
    print(json.dumps({"status": "ok", "problems": len(report["problems"]), "new": len(new), "recovered": len(recovered), "sent": sent}))
    return 0


def backup_drill_cli(data_dir: Path, *, force: bool = False) -> int:
    from datetime import datetime, timezone
    import os

    from investment_agent.api.auth import OwnerContext
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable
    from investment_agent.services.system_health import backup_drill
    try:
        repo, owner = personal_repository_from_env(), OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    except (RepositoryUnavailable, KeyError):
        repo, owner = None, None
    out = backup_drill(Path(data_dir).parent / "backups", data_dir, now=datetime.now(timezone.utc), repo=repo, owner=owner, force=force)
    print(json.dumps({k: out[k] for k in ("status", "ok", "files", "error", "personal") if k in out}))  # counts only
    return 0 if out.get("ok", True) else 1


def _scheduled_telegram(data_dir: Path):
    """(send, repo, owner) when scheduled Telegram delivery is on, else None (nothing is read or sent)."""
    import os

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.services.records import notification_settings
    from investment_agent.settings import Settings

    settings = Settings.from_env()
    repo = personal_repository_from_env()
    owner = OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    chosen, _ = notification_settings(repo, owner)
    if not (settings.telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id):
        return None
    sender = TelegramSender(settings.telegram_bot_token, client=httpx.Client())
    return _part_sender(sender, chosen.chat_id, data_dir), repo, owner


def _http_text(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
    response.raise_for_status()
    return response.text


def deposit_alerts_cli(data_dir: Path) -> int:
    """Nhắc sổ tiết kiệm đáo hạn over Telegram; skipped (the book is not read) while scheduled delivery is off."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from investment_agent.services.deposit_alerts import deposit_alerts_run
    from investment_agent.services.deposit_book import read_book

    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    send, repo, owner = telegram
    book, _ = read_book(repo, owner)
    out = deposit_alerts_run(data_dir, book=book, send=send, today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date())
    print(json.dumps(out))  # counts only, never the book
    return 0


def loan_alerts_cli(data_dir: Path) -> int:
    """Nhắc hết lãi ưu đãi over Telegram; skipped (the book is not read) while scheduled delivery is off."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from investment_agent.services.insurance_alerts import insurance_alerts_run
    from investment_agent.services.rental_alerts import read_rental_book, rental_alerts_run
    from investment_agent.services.loan_alerts import loan_alerts_run, read_property_book

    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    send, repo, owner = telegram
    book, today = read_property_book(repo, owner), datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    out = {**loan_alerts_run(data_dir, book=book, send=send, today=today), "insurance": insurance_alerts_run(data_dir, book=book, send=send, today=today),
           "rental": rental_alerts_run(data_dir, book=read_rental_book(repo, owner), send=send, today=today)}
    print(json.dumps(out))  # counts only, never the book
    return 0


def insider_alerts_cli(data_dir: Path) -> int:
    """Giao dịch nội bộ mới for held tickers over Telegram; skipped while scheduled delivery is off."""
    from datetime import datetime, timezone

    from investment_agent.services.holdings_view import held_from_repo
    from investment_agent.services.insider_alerts import insider_alerts_run

    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    send, repo, owner = telegram
    out = insider_alerts_run(data_dir, held=held_from_repo(repo, owner), get=_http_text, send=send, now=datetime.now(timezone.utc))
    print(json.dumps(out))
    return 0


def weekly_inputs(data_dir: Path, *, ledger_events: list, held: set[str], alerts: list[dict], insider, today) -> dict:
    """What Bản tin tuần reads: stored session snapshots, closes, corporate events and the owner's records; insider(symbol) lists
    a held ticker's notices (VNDirect, cached a day)."""
    from datetime import timedelta

    from investment_agent.domain.time_weighted import performance
    from investment_agent.market.corporate_events import EventStore
    from investment_agent.market.series import SeriesStore
    from investment_agent.market.watchlist import load_watchlist

    store = SeriesStore(Path(data_dir) / "trend-sources")
    briefs = {}
    for path in sorted((Path(data_dir) / "brief").glob("*.json")):
        if (today - timedelta(days=21)).isoformat() <= path.stem <= today.isoformat():
            try:
                briefs[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    closes = {s: [(t.date(), v) for t, v in store.read(f"{s}-1d")] for s in held}
    symbols = {e.security_id for e in ledger_events if getattr(e, "security_id", None)}
    priced = {s: {t.date(): v * 1000 for t, v in store.read(f"{s}-1d")} for s in symbols}  # thousand đồng to đồng, as Hiệu quả does
    series = performance(ledger_events, closes=priced, index={t.date(): v for t, v in store.read("VNINDEX-1d")}, today=today)["series"]
    watched = set(load_watchlist(Path(data_dir)).symbols) | held
    return {"series": series, "index": [(t.date(), v) for t, v in store.read("VNINDEX-1d")], "briefs": briefs, "closes": closes, "insider": {s: insider(s) for s in sorted(held)},
            "events": EventStore(Path(data_dir)).events(sorted(watched)), "alerts": alerts, "held": held, "watched": watched}


def weekly_brief_cli(data_dir: Path, calendar_path: Path) -> int:
    """Bản tin tuần on Saturday (or the first weekend run after), once per week; skipped while scheduled delivery is off."""
    from datetime import datetime, timezone

    from investment_agent.market.insider_deals import InsiderStore, insider_deals
    from investment_agent.services.holdings_view import held_from_repo
    from investment_agent.services.price_alerts import read_alerts
    from investment_agent.services.records import LedgerBook, read_version
    from investment_agent.services.drawdown import held_costs
    from investment_agent.services.theses import position_shares, read_theses
    from investment_agent.services.attention import attention_items
    from investment_agent.services.weekly_brief import VN, week_of, weekly_brief_run

    now = datetime.now(timezone.utc)
    if now.astimezone(VN).weekday() < 5:
        print(json.dumps({"status": "skipped", "reason": "weekday"}))
        return 0
    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    send, repo, owner = telegram
    today = now.astimezone(VN).date()
    start, end = week_of(today)
    try:
        sessions = list(load_calendar(calendar_path).sessions(start, end))
    except Exception:
        sessions = None  # no calendar for these dates: every weekday counts

    def inputs():
        events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
        store = InsiderStore(Path(data_dir))

        def insider(symbol):
            return insider_deals(store, symbol, get=_http_text, now=now)["deals"]
        got = weekly_inputs(data_dir, ledger_events=events, held=held_from_repo(repo, owner), alerts=read_alerts(repo, owner)[0],
                            insider=insider, today=today)
        return {**got, "sessions": sessions, "theses": read_theses(repo, owner)[0], "costs": held_costs(repo, owner),
                "shares": position_shares(repo, owner), "todo": [i["text"] for i in attention_items(repo, owner, Path(data_dir), now=now)]}
    print(json.dumps(weekly_brief_run(data_dir, inputs=inputs, send=send, now=now)))
    return 0


def price_alerts_cli(data_dir: Path, now=None) -> int:
    """Cảnh báo giá during the session (every few minutes from the Windows schedule): one board read for the symbols with an armed
    alert, then one Telegram note for the levels crossed. Outside the session, or with nothing armed, no source is called."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal

    from investment_agent.market.live_board import INDICES, build_board, in_session
    from investment_agent.services.price_alerts import check_alerts, read_alerts

    now = now or datetime.now(timezone.utc)
    if not in_session(now):
        print(json.dumps({"status": "skipped", "reason": "outside_session"}))
        return 0
    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        print(json.dumps({"status": "skipped", "reason": "scheduled_delivery_off"}))
        return 0
    send, repo, owner = telegram
    wanted = {a["symbol"] for a in read_alerts(repo, owner)[0] if a["triggered_at"] is None}
    if not wanted:
        print(json.dumps({"status": "ok", "triggered": 0, "sent": False, "armed": 0}))
        return 0
    from investment_agent.api.routes.trend import _source
    source = _source()
    stocks = sorted(wanted - set(INDICES))
    board = build_board(stocks, board=source.board if stocks else (lambda s: []),
                        index_minutes=lambda i: source.index_minutes(i) if i in wanted else [], now=now)
    prices = {r["symbol"]: Decimal(r["price"]) for r in board["rows"] if r["price"] is not None}
    out = check_alerts(repo, owner, prices=prices, send=send, now=now, request_id=f"price-alerts-{uuid.uuid4().hex[:16]}")
    print(json.dumps({**out, "armed": len(wanted), "errors": board["errors"]}, ensure_ascii=False))
    return 0


def screen_check_cli(data_dir: Path, calendar_path: Path, now=None) -> int:
    """Bộ lọc tín hiệu after the close: one Telegram note for tickers new to the owner's notifying screens. With scheduled delivery
    off, or no screen set to notify, the matches are still recorded (no note), so turning either on later starts from them."""
    from datetime import datetime, timezone

    from investment_agent.market.prices import PriceStore
    from investment_agent.market.view import EmptyMarket, StoreMarket
    from investment_agent.services.holdings_view import held_from_repo
    from investment_agent.services.screener import gather_rows, read_screens, screen_check_run
    from investment_agent.services.weekly_brief import VN

    now = now or datetime.now(timezone.utc)
    telegram = _scheduled_telegram(data_dir)
    if telegram is None:
        import os

        from investment_agent.api.auth import OwnerContext
        from investment_agent.repositories.firestore import personal_repository_from_env
        send, repo, owner = None, personal_repository_from_env(), OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    else:
        send, repo, owner = telegram
    if not any(s.get("notify") for s in read_screens(repo, owner)[0]):  # nothing to read: clear the record so a later switch-on is a baseline
        print(json.dumps(screen_check_run(repo, owner, data_dir, rows=[], send=None, now=now)))
        return 0
    today = now.astimezone(VN).date()
    market = StoreMarket(PriceStore(data_dir), load_calendar(calendar_path), today=lambda: today) if (data_dir / "prices").exists() else EmptyMarket()
    rows = gather_rows(data_dir, repo, owner, held=held_from_repo(repo, owner), today=today, market=market)
    print(json.dumps(screen_check_run(repo, owner, data_dir, rows=rows, send=send, now=now)))
    return 0


def thesis_check_cli(data_dir: Path, calendar_path: Path, scope: str, now=None) -> int:
    """Luận điểm đầu tư: "price" every few minutes in the session (loss against cost, one board read for those tickers), "data" after
    the close (every condition, on stored data). With scheduled Telegram delivery off it records states and closes theses without
    sending."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal

    from investment_agent.domain.thesis import KINDS
    from investment_agent.market.live_board import build_board, in_session
    from investment_agent.services.holdings_view import held_from_repo
    from investment_agent.services.theses import gather, position_shares, read_theses, thesis_check_run
    from investment_agent.services.weekly_brief import VN

    now = now or datetime.now(timezone.utc)
    if scope == "price" and not in_session(now):
        print(json.dumps({"status": "skipped", "reason": "outside_session"}))
        return 0
    telegram = _scheduled_telegram(data_dir)
    if telegram is None:  # still record states and close sold tickers' theses; nothing is sent, so notes stay due for later
        import os

        from investment_agent.api.auth import OwnerContext
        from investment_agent.repositories.firestore import personal_repository_from_env
        send, repo, owner = None, personal_repository_from_env(), OwnerContext(os.environ["FIREBASE_OWNER_UID"], "owner", "scheduler")
    else:
        send, repo, owner = telegram
    today = now.astimezone(VN).date()
    held = held_from_repo(repo, owner)
    open_ = [t for t in read_theses(repo, owner)[0] if t["closed_on"] is None]
    symbols = sorted({t["symbol"] for t in open_ if t["symbol"] in held and (scope == "data" or any(KINDS[c["kind"]][2] == "price" for c in t["conditions"]))})
    live, errors, market, insider = {}, [], None, None
    if symbols and scope == "price":
        from investment_agent.api.routes.trend import _source
        board = build_board(symbols, board=_source().board, index_minutes=lambda i: [], now=now)
        live = {r["symbol"]: Decimal(r["price"]) * 1000 for r in board["rows"] if r["price"] is not None and r["kind"] == "stock"}
        errors = board["errors"]
    if symbols and scope == "data":
        from investment_agent.market.insider_deals import InsiderStore, insider_deals
        from investment_agent.market.prices import PriceStore
        from investment_agent.market.view import EmptyMarket, StoreMarket
        market = StoreMarket(PriceStore(data_dir), load_calendar(calendar_path), today=lambda: today) if (data_dir / "prices").exists() else EmptyMarket()
        wanted = {t["symbol"] for t in open_ if any(c["kind"] == "insider_sell" for c in t["conditions"])}
        store = InsiderStore(Path(data_dir))
        insider = lambda s: insider_deals(store, s, get=_http_text, now=now) if s in wanted else None  # noqa: E731
    facts = gather(data_dir, repo, owner, symbols, scope=scope, today=today, market=market, live=live, insider=insider)
    own = None
    if symbols and send is not None:  # the owner's own record of holding on, shown only from five past times
        from investment_agent.domain.hindsight import lesson
        from investment_agent.services.hindsight import hindsight_for
        try:
            own = lesson(hindsight_for(repo, owner, data_dir, today=today)["breaks"])
        except Exception:  # an optional line: whatever fails here must not stop the check or its notes
            own = None
    out = thesis_check_run(repo, owner, data_dir, scope=scope, facts=facts, shares=position_shares(repo, owner), held=held, send=send, now=now,
                           today=today, request_id=f"thesis-check-{uuid.uuid4().hex[:16]}", lesson=(lambda t, c: own) if own else None)
    print(json.dumps({**out, "errors": errors}, ensure_ascii=False))
    return 0


def journal_cli(data_dir: Path) -> int:
    """Remind the owner of what they wrote when a journalled ticker moved another threshold step (default 15%) from the recorded price."""
    import os
    import uuid
    from decimal import Decimal

    import httpx

    from investment_agent.api.auth import OwnerContext
    from investment_agent.market.series import SeriesStore
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
                     send=_part_sender(sender, chosen.chat_id, data_dir),
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
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.settings import Settings

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
        return _part_sender(sender, chosen.chat_id, data_dir)(text)

    from investment_agent.market.providers.vndirect_data import events as vndirect_events
    out = events_run(data_dir, fetch=lambda symbol: vndirect_events(symbol, today=now.date()), notify=notify, now=now)
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

        from investment_agent.market.providers import vndirect_data as vd
        client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(30, connect=10), headers={"User-Agent": USER_AGENT})

        def fetch(url: str) -> str:
            response = client.get(url)
            response.raise_for_status()
            return response.text
        cache_path = data_dir / "hose-listing.json"

        def vndirect_listing():  # sector names the brief already shows are kept
            try:
                known = json.loads(cache_path.read_text(encoding="utf-8"))["listing"]["icb_names"]
            except (OSError, ValueError, KeyError, TypeError):
                known = {}
            return vd.hose_listing(known_names=known)
        listing = listing or vndirect_listing
        board = board or (lambda symbols: vd.price_board(symbols, today=session))
        http_get = http_get or fetch
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
    earlier = list(cal.sessions(max(cal.first, session - timedelta(days=120)), session - timedelta(days=1)))[-60:]

    def index_bars():  # VN-Index daily bars from the price store (market-sync --index, KBS); public data
        from investment_agent.market.prices import PriceStore
        return {day: {"high": bar.high, "low": bar.low, "close": bar.close, "volume": bar.volume}
                for day, (bar, _) in PriceStore(data_dir).latest("VNINDEX").items()}
    snap = build_snapshot(session_date=session, previous_session=_previous_session(cal, session), now=now, listing=cached_listing,
                          board=board, series=lambda index_id: series.read(f"{index_id}-1d"), hose_get=http_get, rss_get=http_get,
                          store=BriefStore(data_dir), earlier=earlier, index_bars=index_bars)
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
