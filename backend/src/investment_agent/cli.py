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
    backup.add_argument("--kind", choices=["daily", "weekly", "manual"], default="daily")
    args = parser.parse_args()
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


def run_backup(data_dir: Path, backup_dir: Path, kind: str) -> int:
    import os
    from datetime import datetime, timezone

    from investment_agent.api.auth import OwnerContext
    from investment_agent.operations.backup import create_backup, export_personal, prune_backups
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable

    now = datetime.now(timezone.utc)
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
    from investment_agent.market.view import EmptyMarket
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
        result = scheduled_tick(repo=repo, owner=owner, market=EmptyMarket(), jobs=JobStore(data_dir / "jobs.sqlite"),
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
