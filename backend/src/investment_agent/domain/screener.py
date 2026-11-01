"""Bộ lọc tín hiệu: the watched tickers narrowed by several stored signals at once. Within a criterion the chosen values are "or",
between criteria "and"; a ticker without data for a criterion in use never matches and is counted apart with the reason. Only a
narrower list to look at, never a recommendation."""

import uuid
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

FOREIGN_SESSIONS = 20
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


def build_rows(*, symbols: list[str], valuation: dict, trend: dict, chains: dict | None, foreign: dict, events: list[dict], held: set[str],
               today: date) -> list[dict]:
    """Each ticker's value for every criterion (None with a reason when the data is missing). `foreign` holds the ticker's net
    foreign value (billion đồng) per stored session, newest last; `trend` the Xu hướng cells by frame."""
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
        cells = trend.get(s)
        d1, w = (cells or {}).get("D1"), (cells or {}).get("W")
        values["macd_d"], values["macd_w"] = _macd(d1), _macd(w)
        values["macd_w_cross_up"] = None if values["macd_w"] is None else "yes" if w.get("macd_changed") and values["macd_w"] == "up" else "no"
        values["rsi_d"] = (d1 or {}).get("zone")
        for key in ("macd_d", "macd_w", "macd_w_cross_up", "rsi_d"):
            if values[key] is None:
                missing[key] = "Chưa có trên bảng Xu hướng" if cells is None else "Chưa đủ lịch sử giá"
        labels = None if chains is None else chains.get(s, [])
        values["chain"] = [lab for lab in labels if lab in CRITERIA["chain"][1]] if labels else None
        if not values["chain"]:
            values["chain"] = None
            missing["chain"] = "Chưa đọc được chuỗi giá trị" if chains is None else "Mã không thuộc chuỗi giá trị nào" if not labels \
                else "Chuỗi giá trị chưa duyệt hoặc thiếu dữ liệu"
        nets = foreign.get(s, [])
        total = None
        if len(nets) >= FOREIGN_SESSIONS:
            total = sum((Decimal(x) for x in nets[-FOREIGN_SESSIONS:]), Decimal(0))
            values["foreign20"] = "buy" if total > 0 else "sell" if total < 0 else None
            if values["foreign20"] is None:
                missing["foreign20"] = "Khối ngoại 20 phiên cân bằng"
        else:
            values["foreign20"] = None
            missing["foreign20"] = f"Chưa đủ {FOREIGN_SESSIONS} phiên khối ngoại ({len(nets)})"
        values["event14"] = "yes" if s in soon else "no"
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
