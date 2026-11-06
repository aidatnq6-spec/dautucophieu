"""Bảng kiểm "Thị trường phục hồi": four conditions read from the session snapshot, each with the figure behind it, and how many
are met. A condition without figures is "chưa có số" and counts neither way. It is a count of facts, never a call to buy or sell.

1. VN-Index closes above its 20-session average close (MA20, session included).
2. Matched volume is at least the average of the 20 sessions before.
3. More stocks rose than fell on HOSE.
4. The equal-weight average change of every traded HOSE stock is positive (Lan tỏa).
"""

LABELS = {"ma20": "VN-Index trên MA20", "volume": "Khối lượng khớp lệnh ≥ trung bình 20 phiên", "breadth": "Số mã tăng > số mã giảm",
          "spread": "Trung bình cộng các mã tăng"}


def _vn(value: str, places: int = 2) -> str:
    d = float(value)
    text = f"{abs(d):,.{places}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return ("−" if d < 0 else "") + text


def _pct(value: str) -> str:
    d = float(value) * 100
    return ("+" if d > 0 else "−" if d < 0 else "") + f"{abs(d):.2f}".replace(".", ",") + "%"


def _check(key: str, met: bool | None, figure: str) -> dict:
    return {"id": key, "met": met, "label": LABELS[key], "figure": figure}


def _unknown(key: str, section: dict | None) -> dict:
    return _check(key, None, f"chưa có số ({(section or {}).get('reason') or 'chưa có ảnh chụp'})")


def recovery_checks(shape: dict | None, board: dict | None) -> dict:
    if not shape and not board:
        return {"status": "missing", "reason": "Chưa có ảnh chụp phiên"}
    shape, board = shape or {}, board or {}
    older = {"status": "missing", "reason": "ảnh chụp phiên này chưa có mục này"}
    if shape.get("status") != "ok":
        ma = vol = shape or older
    else:
        ma, vol = shape.get("ma20") or older, shape.get("volume") or older
    breadth, spread = board.get("breadth"), board.get("spread") or {}
    checks = [
        _check("ma20", ma["above"], f"MA20 {_vn(ma['value'])}") if ma.get("status") == "ok" else _unknown("ma20", ma),
        _check("volume", vol["today"] >= vol["avg20"], f"{_vn(vol['ratio20'])} lần") if vol.get("status") == "ok" else _unknown("volume", vol),
        _check("breadth", breadth["up"] > breadth["down"], f"{breadth['up']} tăng · {breadth['down']} giảm")
        if board.get("status") == "ok" and breadth else _unknown("breadth", board if board.get("status") != "ok" else older),
        _check("spread", float(spread["mean_pct"]) > 0, _pct(spread["mean_pct"]))
        if board.get("status") == "ok" and spread.get("mean_pct") is not None else _unknown("spread", board if board.get("status") != "ok" else older),
    ]
    known = [c for c in checks if c["met"] is not None]
    return {"status": "ok", "met": sum(1 for c in known if c["met"]), "known": len(known), "total": len(checks), "checks": checks}
