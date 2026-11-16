"""Nhắc lỗi nguồn: after each macro update, the sources that failed three runs in a row are told once over Telegram, grouped by source,
and told again when they come back. The run's results come from data/macro/_last_run.json (written by macro-sync); the counts are kept
in data/alerts/sources.json, so a step run twice on the same macro run counts nothing. Public source names only."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

STATE = "sources.json"
THRESHOLD = 3
VN = ZoneInfo("Asia/Ho_Chi_Minh")
ERRORS = {"ConnectError": "lỗi kết nối", "ConnectTimeout": "hết thời gian kết nối", "ReadTimeout": "hết thời gian chờ",
          "HTTPStatusError": "trang trả lỗi", "MacroError": "không đọc được nội dung"}


def _read(path: Path, empty: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _when(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(VN).strftime("%H:%M %d/%m/%Y")


def _error(code: str) -> str:
    return f"{ERRORS.get(code, 'lỗi')} ({code})"


def _label(labels: dict, key: str) -> tuple[str, str]:
    return labels.get(key, ("Khác", key))


def check_sources(data_dir: Path, *, send, labels: dict[str, tuple[str, str]], threshold: int = THRESHOLD) -> dict:
    data_dir = Path(data_dir)
    run = _read(data_dir / "macro" / "_last_run.json", {})
    path = data_dir / "alerts" / STATE
    state = _read(path, {"last_run": None, "keys": {}})
    if not run or run.get("at") == state.get("last_run"):
        return {"status": "ok", "new": 0, "recovered": 0, "sent": False}
    keys, down, back = state["keys"], [], []
    for key, result in run["results"].items():
        if result == "ok" or not str(result).startswith("error"):
            if keys.get(key, {}).get("alerted"):
                back.append(key)
            keys.pop(key, None)
            continue
        entry = keys.setdefault(key, {"fails": 0, "since": run["at"], "error": None, "alerted": False})
        entry["fails"] += 1
        entry["error"] = str(result).partition(":")[2] or "lỗi"
        if entry["fails"] >= threshold and not entry["alerted"]:
            down.append(key)
    parts = []
    if down:
        groups: dict[str, list[str]] = {}
        for k in down:
            groups.setdefault(_label(labels, k)[0], []).append(k)
        lines = [f"• {src}: {', '.join(_label(labels, k)[1] for k in ks)} — {_error(keys[ks[0]]['error'])} từ {_when(min(keys[k]['since'] for k in ks))}"
                 for src, ks in groups.items()]
        parts.append(f"⚠️ Nguồn số liệu lỗi từ {threshold} lượt liên tiếp\n" + "\n".join(lines) + "\nSố đã lưu vẫn giữ; phần mềm tự thử lại ở các lượt sau.")
    if back:
        groups = {}
        for k in back:
            groups.setdefault(_label(labels, k)[0], []).append(_label(labels, k)[1])
        parts.append("✅ Nguồn số liệu đã lấy được trở lại\n" + "\n".join(f"• {src}: {', '.join(names)}" for src, names in groups.items()))
    sent = bool(parts) and bool(send("\n\n".join(parts)))
    if sent:
        for k in down:
            keys[k]["alerted"] = True
    _write(path, {"last_run": run["at"], "keys": keys})
    return {"status": "ok", "new": len(down), "recovered": len(back), "sent": sent}


def source_view(data_dir: Path, *, labels: dict[str, tuple[str, str]]) -> dict:
    """For Cài đặt: the last macro run and the sources failing since, with their run count."""
    data_dir = Path(data_dir)
    run = _read(data_dir / "macro" / "_last_run.json", {})
    keys = _read(data_dir / "alerts" / STATE, {"keys": {}})["keys"]
    failing = [{"key": k, "source": _label(labels, k)[0], "label": _label(labels, k)[1], **v} for k, v in sorted(keys.items())]
    return {"last_run": run.get("at"), "checked": len(run.get("results", {})), "failing": failing}


SOURCES = {"sbv_m2": "NHNN (sbv.gov.vn)", "nso_report": "Cục Thống kê (nso.gov.vn)", "nso_cpi": "Cục Thống kê (nso.gov.vn)", "sbv_central": "NHNN (sbv.gov.vn)",
           "sbv_interbank": "NHNN (sbv.gov.vn)", "fred": "FRED", "oilprice": "OilPrice", "topi": "Topi", "vcb": "Vietcombank", "hose": "HOSE",
           "stockbiz": "Stockbiz", "treasury": "Bộ Tài chính Mỹ", "ecb_dxy": "ECB", "cafef_pmi": "CafeF", "news_pmi": "Tin RSS", "news_cpi": "Tin RSS"}


def macro_labels() -> dict[str, tuple[str, str]]:
    """(source, item) names for every key a macro run reports."""
    from investment_agent.market.leading import load_indicators
    from investment_agent.market.value_chains import COMMODITY_LABELS
    out = {i["id"]: (SOURCES.get(i["source"]["kind"], i["source"]["kind"]), i["label"]) for i in load_indicators()}
    for k, name in COMMODITY_LABELS.items():
        out[k] = ({"com_urea": "World Bank", "port_container_yoy": "Hiệp hội Cảng biển (VPA)", "vn_pangasius_export_yoy": "VASEP"}.get(k, "FRED"), name)
    out["omo"] = ("NHNN (sbv.gov.vn)", "Nghiệp vụ thị trường mở")
    out["factor_oil"], out["factor_usd"] = ("FRED", "Chuỗi dầu dài hạn"), ("FRED", "Chuỗi USD dài hạn")
    return out
