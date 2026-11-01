"""Bộ lọc tín hiệu: the watched tickers narrowed by several stored signals at once. Within a criterion the chosen values are "or",
between criteria "and"; a ticker without data for a criterion in use never matches and is counted apart with the reason. Only a
narrower list to look at, never a recommendation."""

import uuid
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

FOREIGN_SESSIONS = 20
FRESH_DAYS = 7  # stored signals older than this are no longer today's
EVENT_DAYS = 14
EVENT_KINDS = ("dividend_cash", "issue", "meeting")
MAX_SCREENS = 20
# criterion: (label, values with labels)
CRITERIA = {
    "verdict": ("Định giá", {"cheap": "Rẻ", "fair": "Hợp lý", "expensive": "Đắt"}),
    "quality": ("Chất lượng", {"strong": "Mạnh", "medium": "Trung bình", "weak": "Yếu"}),
    "macd_d": ("MACD ngày", {"up": "Trên tín hiệu", "down": "Dưới tín hiệu"}),
    "macd_w": ("MACD tuần", {"up": "Trên tín hiệu", "down": "Dưới tín hiệu"}),
    "macd_w_cross_up": ("MACD tuần vừa cắt lên", {"yes": "Có", "no": "Không"}),
    "rsi_d": ("RSI ngày", {"oversold": "Quá bán (≤30)", "neutral": "Trung tính", "overbought": "Quá mua (≥70)"}),
    "chain": ("Chuỗi giá trị", {"tailwind": "Thuận", "neutral": "Trung tính", "headwind": "Ngược"}),
    "foreign20": ("Khối ngoại 20 phiên", {"buy": "Mua ròng", "sell": "Bán ròng"}),
    "event14": ("Sự kiện 14 ngày tới", {"yes": "Có", "no": "Không"}),
    "held": ("Đang nắm", {"yes": "Có", "no": "Không"}),
}


class ScreenError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _macd(cell: dict | None) -> str | None:
    state = (cell or {}).get("macd")
    return state.split(",")[0] if state else None


def _dmy(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def build_rows(*, symbols: list[str], valuation: dict, trend: dict, trend_meta: dict, chains: dict | None, foreign: dict, events: list[dict],
               events_known: set[str], held: set[str], today: date) -> list[dict]:
    """Each ticker's value for every criterion (None with a reason when the data is missing or stale). `trend` holds the Xu hướng
    cells by frame and `trend_meta` that board's session and the one it was compared with; `foreign` the stored sessions (oldest
    first) and each ticker's net foreign value (billion đồng) per session; `events_known` the tickers whose events were read."""
    fresh = (today - timedelta(days=FRESH_DAYS)).isoformat()
    trend_date = trend_meta.get("session_date")
    trend_stale = None if trend_date and trend_date >= fresh else f"Bảng Xu hướng chỉ tới {_dmy(trend_date)}" if trend_date else None
    sessions = foreign.get("sessions", [])[-FOREIGN_SESSIONS:]
    foreign_stale = f"Khối ngoại đã lưu chỉ tới {_dmy(sessions[-1])}" if sessions and sessions[-1] < fresh else None
    soon = {e["symbol"] for e in events if e.get("kind") in EVENT_KINDS and e.get("key_date")
            and today.isoformat() <= e["key_date"] <= (today + timedelta(days=EVENT_DAYS)).isoformat()}
    rows = []
    for s in symbols:
        values, missing = {}, {}
        v = valuation.get(s) or {}
        values["verdict"] = v.get("verdict") if v.get("verdict") in CRITERIA["verdict"][1] else None
        if values["verdict"] is None:
            missing["verdict"] = "Chưa đủ số liệu định giá"
        q = (v.get("quality") or {})
        values["quality"] = ((q.get("f_score") or {}).get("level"))
        if values["quality"] is None:
            missing["quality"] = q.get("reason") or "Chưa đủ tiêu chí để xếp mức chất lượng"
        cells = None if trend_stale else trend.get(s)
        d1, w = (cells or {}).get("D1"), (cells or {}).get("W")
        values["macd_d"], values["macd_w"] = _macd(d1), _macd(w)
        # Crossed up = below its signal on the previous board, above now (a sign change of the line alone is not a cross).
        crossed = values["macd_w"] == "up" and bool(w.get("macd_changed")) and _macd({"macd": w.get("previous_macd")}) == "down"
        values["macd_w_cross_up"] = None if values["macd_w"] is None or not trend_meta.get("previous_date") else "yes" if crossed else "no"
        values["rsi_d"] = (d1 or {}).get("zone")
        for key, cell in (("macd_d", d1), ("macd_w", w), ("macd_w_cross_up", w), ("rsi_d", d1)):
            if values[key] is None:
                missing[key] = trend_stale or ("Chưa có trên bảng Xu hướng" if cells is None else (cell or {}).get("reason")
                                               or ("Chưa có phiên trước để so" if key == "macd_w_cross_up" else "Chưa đủ lịch sử giá"))
        labels = None if chains is None else chains.get(s, [])
        values["chain"] = [lab for lab in labels if lab in CRITERIA["chain"][1]] if labels else None
        if not values["chain"]:
            values["chain"] = None
            missing["chain"] = "Chưa đọc được chuỗi giá trị" if chains is None else "Mã không thuộc chuỗi giá trị nào" if not labels \
                else "Chuỗi giá trị chưa duyệt hoặc thiếu dữ liệu"
        nets = foreign.get("values", {}).get(s, {})
        gap = next((d for d in sessions if nets.get(d) is None), None)
        total, values["foreign20"] = None, None
        if len(sessions) < FOREIGN_SESSIONS:
            missing["foreign20"] = f"Chưa đủ {FOREIGN_SESSIONS} phiên khối ngoại ({len(sessions)})"
        elif foreign_stale:
            missing["foreign20"] = foreign_stale
        elif gap:
            missing["foreign20"] = f"Thiếu khối ngoại phiên {gap[8:10]}/{gap[5:7]}"
        else:
            total = sum((Decimal(nets[d]) for d in sessions), Decimal(0))
            values["foreign20"] = "buy" if total > 0 else "sell" if total < 0 else None
            if values["foreign20"] is None:
                missing["foreign20"] = "Khối ngoại 20 phiên cân bằng"
        values["event14"] = None if s not in events_known else "yes" if s in soon else "no"
        if values["event14"] is None:
            missing["event14"] = "Chưa đọc Lịch sự kiện của mã"
        values["held"] = "yes" if s in held else "no"
        rows.append({"symbol": s, "values": values, "missing": missing,
                     "foreign20_bn": None if total is None else format(total.quantize(Decimal("0.01"), ROUND_HALF_UP), "f")})
    return rows


def match(criteria: dict, row: dict) -> tuple[bool, list[str]]:
    """(matched, criteria without data). A criterion with no value for the ticker fails the match."""
    lacking, ok = [], True
    for key, wanted in criteria.items():
        value = row["values"].get(key)
        if value is None:
            lacking.append(key)
            ok = False
        elif not (set(value) & set(wanted) if isinstance(value, list) else value in wanted):
            ok = False
    return ok, lacking


def validate_screen(raw: dict) -> dict:
    name = str(raw.get("name") or "").strip()
    if not name or len(name) > 60:
        raise ScreenError("name_required", "Đặt tên bộ lọc (tối đa 60 ký tự).")
    criteria = raw.get("criteria") or {}
    if not criteria:
        raise ScreenError("criteria_required", "Chọn ít nhất một tiêu chí.")
    kept = {}
    for key, values in criteria.items():
        if key not in CRITERIA or not isinstance(values, list) or not values or any(v not in CRITERIA[key][1] for v in values):
            raise ScreenError("invalid_criteria", "Tiêu chí không hợp lệ.")
        kept[key] = [v for v in CRITERIA[key][1] if v in values]
    return {"id": str(raw.get("id") or uuid.uuid4().hex[:12])[:32], "name": name, "criteria": kept, "notify": bool(raw.get("notify"))}


def entered(previous: dict[str, list[str]], current: dict[str, list[str]]) -> dict[str, list[str]]:
    """Tickers new to each screen since the last check; a screen seen for the first time is only a baseline."""
    out = {}
    for sid, symbols in current.items():
        if sid in previous:
            new = [s for s in symbols if s not in set(previous[sid])]
            if new:
                out[sid] = new
    return out
