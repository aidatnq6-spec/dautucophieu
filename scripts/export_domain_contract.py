"""Export Pydantic JSON Schema and TypeScript types with the pinned npm tool.

Run: .venv/Scripts/python.exe scripts/export_domain_contract.py
Check: .venv/Scripts/python.exe scripts/export_domain_contract.py --check
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from investment_agent.domain.models import DomainContract  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schema_text = json.dumps(DomainContract.model_json_schema(), indent=2, ensure_ascii=False) + "\n"
    binary = ROOT / "apps" / "web" / "node_modules" / ".bin" / (
        "json2ts.cmd" if sys.platform == "win32" else "json2ts"
    )
    result = subprocess.run(
        [str(binary), "--no-additionalProperties"], input=schema_text,
        text=True, capture_output=True, check=True, cwd=ROOT, encoding="utf-8",
    )
    artifacts = {
        ROOT / "contracts" / "domain.schema.json": schema_text,
        ROOT / "apps" / "web" / "src" / "generated" / "domain.ts": result.stdout.removeprefix("/* eslint-disable */\n"),
    }
    stale = []
    for path, content in artifacts.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        print("Stale generated contracts: " + ", ".join(stale), file=sys.stderr)
        return 1
    print("Domain contracts are current" if args.check else "Exported domain schema and TypeScript types")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
