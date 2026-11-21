"""scheduler.log moves to scheduler-YYYY-MM.log once its first line is from an earlier month (owner, 21/11/2026), and logs older than
six months are removed. The new file begins with the old one's last lines, so Tình trạng hệ thống still finds the last finished run and
how many times in a row a step failed. Run at the start of the after-close wake-up:
`python -m investment_agent.jobs.log_rotate <path to scheduler.log>`; prints one JSON line. The logs stay on this computer."""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

KEEP_MONTHS = 6
CARRY = 200


def _month_index(ym: str) -> int:
    return int(ym[:4]) * 12 + int(ym[5:7]) - 1


def rotate(log: Path, *, today: date, keep_months: int = KEEP_MONTHS, carry: int = CARRY) -> dict:
    log = Path(log)
    out = {"rotated": None, "removed": []}
    text = log.read_text(encoding="utf-8-sig") if log.is_file() else ""
    lines = text.splitlines()
    first = lines[0][:7] if lines else ""
    if len(first) == 7 and first[4] == "-" and first != f"{today.year}-{today.month:02d}":
        archive = log.with_name(f"{log.stem}-{first}{log.suffix}")
        if archive.exists():  # a second rotation in the same month adds to it
            archive.write_text(archive.read_text(encoding="utf-8-sig") + text, encoding="utf-8")
        else:
            archive.write_text(text, encoding="utf-8")
        tmp = log.with_suffix(".tmp")
        tmp.write_text("﻿" + "".join(line + "\n" for line in lines[-carry:]), encoding="utf-8")
        os.replace(tmp, log)
        out["rotated"] = archive.name
    oldest = today.year * 12 + today.month - 1 - keep_months
    for old in sorted(log.parent.glob(f"{log.stem}-????-??{log.suffix}")):
        if _month_index(old.stem[len(log.stem) + 1:]) < oldest:
            old.unlink()
            out["removed"].append(old.name)
    return out


def main(argv: list[str]) -> int:
    from zoneinfo import ZoneInfo
    from datetime import datetime
    print(json.dumps(rotate(Path(argv[0]), today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
