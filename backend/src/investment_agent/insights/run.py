"""One insights-run: SSI titles (side signal), new ACBS/World Bank reports through the model, then Telegram.

The run status and SSI titles are written under data/insights so the page can show why nothing new appeared.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from investment_agent.market.sectors import load_sectors

from . import sources
from .pipeline import run_insights
from .sources import ssi_titles
from .store import InsightStore

# ICB level-2 names as Vnstock spells them (data/industries.json); the model must pick from this closed list.
ICB_LEVEL2 = ("Bán lẻ", "Bảo hiểm", "Bất động sản", "Công nghệ Thông tin", "Dầu khí", "Dịch vụ tài chính", "Du lịch và Giải trí",
              "Hàng & Dịch vụ Công nghiệp", "Hàng cá nhân & Gia dụng", "Hóa chất", "Ngân hàng", "Ô tô và phụ tùng", "Thực phẩm và đồ uống",
              "Tài nguyên Cơ bản", "Truyền thông", "Viễn thông", "Xây dựng và Vật liệu", "Y tế", "Điện, nước & xăng dầu khí đốt")


def allowed_sectors(data_dir: Path) -> list[str]:
    local = sorted(set(load_sectors(data_dir)[0].values()) - set(ICB_LEVEL2))
    return list(ICB_LEVEL2) + local


def discover_sources(get, store, *, since, errors: dict) -> list:
    """ACBS then World Bank; a failing source is recorded in errors (source -> exception name) instead of vanishing."""
    def known(ref_id: str) -> bool:
        try:
            return store.read("acbs", ref_id) is not None
        except ValueError:
            return False
    refs = []
    for name, find in (("acbs", lambda: sources.discover_acbs(get, since=since, known=known)),
                       ("worldbank", lambda: sources.discover_worldbank(get, since=since))):
        try:
            refs += find()
        except Exception as exc:
            errors[name] = type(exc).__name__
    return refs


def due(data_dir: Path, *, now, min_hours: float) -> bool:
    """False when the previous run finished less than min_hours ago (the scheduler wakes several times a day)."""
    path = Path(data_dir) / "insights" / "status.json"
    try:
        last = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["at"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return True
    return now - last >= timedelta(hours=min_hours)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def record_status(data_dir: Path, *, now, out: dict) -> None:
    """Last run result for the page (why nothing new appeared)."""
    _write(Path(data_dir) / "insights" / "status.json", {"at": now.isoformat(), **out})


def insights_run(data_dir: Path, *, ssi_get, discover, download, pages, gateway, notify, now, sleep) -> dict:
    """gateway None means no OpenRouter key; notify(store) -> {"sent", "failed"} or None when Telegram is off."""
    root = Path(data_dir) / "insights"
    try:
        _write(root / "ssi.json", {"at": now.isoformat(), "titles": ssi_titles(ssi_get, limit=10)})
    except Exception:  # side signal only; keep the previous titles
        pass
    store = InsightStore(root)
    if gateway is None:
        out = {"status": "not_configured", "reason": "key_missing", "processed": []}
    else:
        out = run_insights(store=store, discover=discover, download=download, pages=pages, gateway=gateway,
                           sectors=allowed_sectors(data_dir), now=now, sleep=sleep)
    if notify is not None:
        out["telegram"] = notify(store)
    record_status(data_dir, now=now, out=out)
    return out
