"""Small local command surface for source audits."""

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
    args = parser.parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
