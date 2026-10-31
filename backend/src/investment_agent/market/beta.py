"""Beta of each watched ticker from VNDirect's public ratios API (latest value of code BETA), the whole watchlist in one
call per scheduler run, kept in data/beta.json for the CAPM hint. robots.txt of api-finfo.vndirect.com.vn allows all user
agents (use=reference). Rows for tickers not asked for, or without a numeric value, are dropped.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

URL = "https://api-finfo.vndirect.com.vn/v4/ratios/latest?filter=ratioCode:BETA&where=code:{codes}&order=reportDate&fields=code,value,reportDate"


class BetaStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "beta.json"

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {"values": {}}

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, self.path)


def fetch_betas(store: BetaStore, symbols: list[str], *, get: Callable[[str], str]) -> dict:
    wanted = {s.upper() for s in symbols}
    values = {}
    for row in json.loads(get(URL.format(codes=",".join(symbols)))).get("data") or []:
        code = str(row.get("code") or "").upper()
        try:
            beta = Decimal(str(row.get("value")))
        except InvalidOperation:
            continue
        if code in wanted and beta.is_finite():
            values[code] = {"beta": str(row["value"]), "date": str(row.get("reportDate"))[:10]}
    store.save({"fetched_at": datetime.now(timezone.utc).isoformat(), "source": "vndirect:finfo", "values": values})
    return {"status": "ok", "betas": len(values), "missing": sorted(wanted - set(values))}
