"""Leading macro indicators: free official feeds where they exist, owner entries for the rest.

Automatic sources (checked 2026-10-25): FRED public CSV downloads (WTI, US CPI,
EFFR, US 10-year yield, broad dollar index) and the Vietcombank exchange-rate
XML. Everything else in the owner's sheet (free-market and SBV USD/VND, M2,
PMIs, deposit and interbank rates, VN 10-year yield, foreign flows, VN-Index
turnover) has no free licensed feed and is entered by the owner with a source
link. Values are stored as decimal strings under data/macro/; nothing is
estimated when a value is missing. This is a display dashboard: analysis
evidence keeps using the vintaged series in macro.py, which these values do
not feed.
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from investment_agent.domain.pinned import CONFIG_DIR

INDICATORS_PATH = CONFIG_DIR / "macro-indicators.json"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
VCB_XML = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
_ID = re.compile(r"^[a-z0-9_]{1,40}$")


class MacroError(ValueError):
    pass


def load_indicators(path: Path = INDICATORS_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["indicators"]


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def parse_fred_csv(text: str, *, transform: str | None = None) -> list[tuple[date, str]]:
    points = []
    for line in text.strip().splitlines()[1:]:
        day, _, raw = line.partition(",")
        try:
            points.append((date.fromisoformat(day.strip()), Decimal(raw.strip())))
        except (ValueError, InvalidOperation):
            continue  # FRED marks holidays with "."
    if transform == "yoy":
        by_month = {(d.year, d.month): v for d, v in points}
        return [(d, str(((v / by_month[(d.year - 1, d.month)] - 1) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)))
                for d, v in points if (d.year - 1, d.month) in by_month]
    return [(d, _plain(v)) for d, v in points]


def parse_vcb_xml(text: str, *, currency: str, field: str) -> tuple[date, str]:
    try:
        root = ET.fromstring(text)
        stamp = datetime.strptime(root.findtext("DateTime", "").strip(), "%m/%d/%Y %I:%M:%S %p").date()
        node = next(e for e in root.iter("Exrate") if e.get("CurrencyCode") == currency)
        return stamp, _plain(Decimal(node.get(field, "").replace(",", "")))
    except (ET.ParseError, ValueError, StopIteration, InvalidOperation) as exc:
        raise MacroError(f"vcb_unreadable:{type(exc).__name__}") from None


def evaluate(rule: str, values: list[str]) -> tuple[str | None, str | None]:
    """(trend, assessment) from the last two values, oldest first, by the owner's rules."""
    latest = Decimal(values[-1]) if values else None
    trend = None
    if len(values) >= 2:
        prev = Decimal(values[-2])
        trend = "Tăng" if latest > prev else "Giảm" if latest < prev else "Đi ngang"
    if rule == "sign" and latest is not None:
        return trend, "Tốt" if latest > 0 else "Xấu" if latest < 0 else "Trung tính"
    if trend is None:
        return None, None
    if rule == "pmi":
        return trend, "Tốt" if latest > 50 and trend != "Giảm" else "Xấu"
    if trend == "Đi ngang":
        return trend, "Trung tính"
    worse = "Tăng" if rule == "up" else "Giảm"
    return trend, "Xấu" if trend == worse else "Tốt"


class MacroStore:
    """One JSON file per indicator under data/macro/, observations sorted by date, one per date."""

    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "macro"

    def _path(self, indicator: str) -> Path:
        if not _ID.fullmatch(indicator):
            raise MacroError("invalid_indicator")
        return self.root / f"{indicator}.json"

    def read(self, indicator: str) -> list[dict]:
        path = self._path(indicator)
        return json.loads(path.read_text(encoding="utf-8"))["observations"] if path.is_file() else []

    def upsert(self, indicator: str, points: list[tuple[date, str]], *, entry: str, source_url: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        by_date = {o["date"]: o for o in self.read(indicator)}
        for day, value in points:
            by_date[day.isoformat()] = {"date": day.isoformat(), "value": value, "entry": entry, "source_url": source_url, "recorded_at": now}
        self.root.mkdir(parents=True, exist_ok=True)
        path, tmp = self._path(indicator), self._path(indicator).with_suffix(".tmp")
        tmp.write_text(json.dumps({"indicator": indicator, "observations": [by_date[k] for k in sorted(by_date)]}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path)


def fetch_auto(indicators: list[dict], store: MacroStore, *, get: Callable[[str], str]) -> dict[str, str]:
    """Fetch every automatic indicator; one failing source never stops the others."""
    results = {}
    for ind in indicators:
        src = ind["source"]
        try:
            if src["kind"] == "fred":
                points = parse_fred_csv(get(FRED_CSV.format(series=src["series"])), transform=src.get("transform"))
            elif src["kind"] == "vcb":
                points = [parse_vcb_xml(get(VCB_XML), currency=src["currency"], field=src["field"])]
            else:
                continue
            if not points:
                raise MacroError("no_observations")
            store.upsert(ind["id"], points[-400:], entry="auto")
            results[ind["id"]] = "ok"
        except Exception as exc:  # network, parse or source change: reported per indicator
            results[ind["id"]] = f"error:{type(exc).__name__}"
    return results


def macro_rows(indicators: list[dict], store: MacroStore, *, today: date) -> list[dict]:
    rows = []
    for ind in indicators:
        obs = store.read(ind["id"])
        last = obs[-1] if obs else None
        trend, assessment = evaluate(ind["rule"], [o["value"] for o in obs[-2:]])
        rows.append({"id": ind["id"], "label": ind["label"], "unit": ind["unit"], "auto": ind["source"]["kind"] != "manual",
                     "value": last["value"] if last else None, "date": last["date"] if last else None,
                     "previous": obs[-2]["value"] if len(obs) >= 2 else None, "trend": trend, "assessment": assessment,
                     "stale": last is not None and (today - date.fromisoformat(last["date"])).days > ind["max_age_days"],
                     "source_url": (last or {}).get("source_url") or ind["url"], "note": ind.get("note")})
    return rows
