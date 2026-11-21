"""Lịch sử vĩ mô dài for Thống kê lịch sử (owner, 21/11/2026).

- Vietnam, monthly, 2010 on, from the World Bank's Global Economic Monitor (source 15; open API, no key; robots.txt answers 404, so
  nothing is disallowed; checked 21/11/2026): CPI % y-o-y, industrial production (constant US$, seasonally adjusted), USD/VND
  (period average) and merchandise exports (US$ millions, seasonally adjusted). The figures run about four months behind.
- The US 10-year Treasury yield, daily since 1962, from FRED (DGS10), beside the recent series the light reads.

Domestic interest rates have no public history source (the State Bank refused, IMF answered 502 when checked), so none is stored.
Read once a week (the series move monthly); a month or day without a figure stays out, never filled."""

from __future__ import annotations

import json
import os
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .leading import FRED_CSV, MacroStore, _get_with_retry, error_name, parse_fred_csv

GEM_URL = ("https://api.worldbank.org/v2/country/VNM/indicator/{code}?source=15&format=json&frequency=M&per_page=1000"
           "&date=2010M01:{year}M12")
GEM_SERIES = (("wb_vn_cpi_yoy", "CPTOTSAXNZGY", "CPI Việt Nam so cùng kỳ (%)"),
              ("wb_vn_iip", "IPTOTSAKD", "Sản xuất công nghiệp Việt Nam (điều chỉnh mùa vụ)"),
              ("wb_vn_usdvnd", "DPANUSSPB", "Tỷ giá USD/VND bình quân tháng"),
              ("wb_vn_exports", "DXGSRMRCHSACD", "Xuất khẩu hàng hóa Việt Nam (triệu USD, điều chỉnh mùa vụ)"))
LONG_FRED = (("us10y_long", "DGS10"),)
EVERY = timedelta(days=7)
STATE = "_history_series.json"
MAX_AGE_DAYS = {**{k: 200 for k, _, _ in GEM_SERIES}, "us10y_long": 10}  # macro-sync's late/stale rule


def parse_gem(text: str) -> list[tuple[date, str]]:
    page = json.loads(text)
    rows = page[1] if isinstance(page, list) and len(page) > 1 and page[1] else []
    out = []
    for r in rows:
        if r.get("value") is None or "M" not in str(r.get("date", "")):
            continue
        year, month = (int(x) for x in str(r["date"]).split("M"))
        out.append((date(year, month, monthrange(year, month)[1]), format(Decimal(str(r["value"])), "f")))  # the figure as the source wrote it
    return sorted(out)


def fetch_history_series(store: MacroStore, data_dir: Path, *, get: Callable[[str], str], sleep, today: date) -> dict[str, str]:
    """{} when read in the last seven days; else each series' result. A failure does not move the weekly mark."""
    path = Path(data_dir) / "macro" / STATE
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if state.get("read_on") and today - date.fromisoformat(state["read_on"]) < EVERY:
        return {}
    results = {}
    for key, code, _ in GEM_SERIES:
        url = GEM_URL.format(code=code, year=today.year)
        try:
            points = parse_gem(_get_with_retry(get, url, sleep))
            if not points:
                raise ValueError("no_observations")
            store.upsert(key, points, entry="auto", source_url=url, replace=True)
            results[key] = "ok"
        except Exception as exc:
            results[key] = f"error:{error_name(exc)}"
    for key, series in LONG_FRED:
        url = FRED_CSV.format(series=series)
        try:
            points = parse_fred_csv(_get_with_retry(get, url, sleep))
            if not points:
                raise ValueError("no_observations")
            store.upsert(key, points, entry="auto", source_url=url, replace=True)
            results[key] = "ok"
        except Exception as exc:
            results[key] = f"error:{error_name(exc)}"
    if all(v == "ok" for v in results.values()):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"read_on": today.isoformat()}), encoding="utf-8")
        os.replace(tmp, path)
    return results
