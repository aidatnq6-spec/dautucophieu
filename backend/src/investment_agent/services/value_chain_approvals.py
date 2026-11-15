"""Duyệt chuỗi giá trị trong ứng dụng: the owner's approval of each chain, kept in data/value-chain-approvals.json with the fingerprint of
the content approved (market.value_chains.fingerprint). A chain whose content has changed since reads as not approved."""

import json
import os
from datetime import date
from pathlib import Path

FILE = "value-chain-approvals.json"
NOTE_MAX = 500


def read_approvals(data_dir: Path) -> dict[str, dict]:
    path = Path(data_dir) / FILE
    return json.loads(path.read_text(encoding="utf-8")).get("chains", {}) if path.is_file() else {}


def _write(data_dir: Path, chains: dict[str, dict]) -> None:
    path = Path(data_dir) / FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"chains": chains}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def approve(data_dir: Path, chain_id: str, *, fingerprint: str, note: str | None, on: date) -> None:
    chains = read_approvals(data_dir)
    chains[chain_id] = {"fingerprint": fingerprint, "on": on.isoformat(), "note": note}
    _write(data_dir, chains)


def withdraw(data_dir: Path, chain_id: str) -> None:
    chains = read_approvals(data_dir)
    if chains.pop(chain_id, None) is not None:
        _write(data_dir, chains)
