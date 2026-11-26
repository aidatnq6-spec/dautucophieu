"""verify.ps1 builds the web app into its own folder, so the running app's .next is never replaced under it (26/11/2026).

That evening the build step rebuilt apps/web/.next under the running `next start`: pages hung on "Đang tải…" or failed to load.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"


def verify_lines():
    text = (ROOT / "scripts" / "windows" / "verify.ps1").read_text(encoding="utf-8-sig")
    return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


def test_the_build_step_writes_to_its_own_folder_cleared_first_and_restores_next_env():
    ls = verify_lines()
    build = next(l for l in ls if l.startswith("'web build'"))
    assert "NEXT_DIST_DIR" in build and ".next-verify" in build
    clear = next(i for i, l in enumerate(ls) if "Remove-Item" in l and ".next-verify" in l)
    assert clear < next(i for i, l in enumerate(ls) if l.startswith("'web typecheck'"))  # stale types never reach tsc
    # put back after every check (the build and the browser tests' dev server both rewrite it), even when one fails
    restore = next(i for i, l in enumerate(ls) if "checkout" in l and "next-env.d.ts" in l)
    assert ls[restore - 1] == "} finally {" and restore > next(i for i, l in enumerate(ls) if l.startswith("'browser e2e'"))


def test_next_reads_the_folder_and_the_verify_build_is_known_to_typescript_and_git():
    config = (WEB / "next.config.ts").read_text(encoding="utf-8")
    assert re.search(r"distDir:\s*process\.env\.NEXT_DIST_DIR\s*\|\|\s*\"\.next\"", config)
    include = json.loads((WEB / "tsconfig.json").read_text(encoding="utf-8"))["include"]
    # else the build rewrites tsconfig.json itself to add them
    assert {".next-verify/types/**/*.ts", ".next-verify/dev/types/**/*.ts"} <= set(include)
    assert ".next-verify/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
