"""Atomic, content-addressed Parquet storage for one immutable observation per file."""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from investment_agent.domain.models import Observation


class ParquetStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if not path.is_relative_to(self.root) or path.suffix != ".parquet":
            raise ValueError("invalid observation path")
        return path

    def write_observation(self, observation: Observation) -> Path:
        payload = observation.model_dump(mode="json")
        # IDs supplied by providers never become paths. The digest is only a
        # storage address; the catalog owns logical identity and revisions.
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        name = hashlib.sha256(canonical.encode("utf-8")).hexdigest() + ".parquet"
        target = self.resolve(name)
        if target.exists():
            try:
                if self.read_observation(name).model_dump(mode="json") != payload:
                    raise ValueError("content mismatch")
            except Exception as exc:
                raise ValueError("existing observation file is invalid") from exc
            return target
        temporary = self.root / f".{uuid4().hex}.tmp"
        try:
            # All domain values are JSON scalars. Monetary values remain
            # decimal strings; absent values remain Arrow nulls.
            table = pa.Table.from_pylist([payload])
            pq.write_table(table, temporary)
            with temporary.open("r+b") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def read_observation(self, relative_path: str) -> Observation:
        path = self.resolve(relative_path)
        table = pq.read_table(path)
        if table.num_rows != 1:
            raise ValueError("invalid observation file")
        return Observation.model_validate(table.to_pylist()[0])

    @staticmethod
    def checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
