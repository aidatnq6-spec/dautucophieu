from investment_agent.brief.recovery import recovery_checks

SHAPE = {"status": "ok", "ma20": {"status": "ok", "value": "1712.40", "above": True},
         "volume": {"status": "ok", "today": 984184812, "avg20": 578505165, "ratio20": "1.70", "previous": 1, "change_pct": "0"}}
BOARD = {"status": "ok", "breadth": {"up": 120, "down": 210, "flat": 40, "no_trade": 30},
         "spread": {"count": 368, "mean_pct": "-0.0042", "median_pct": "-0.0025"}}


def test_four_conditions_each_with_its_figure_and_the_count_met():
    out = recovery_checks(SHAPE, BOARD)
    assert out == {"status": "ok", "met": 2, "known": 4, "total": 4, "checks": [
        {"id": "ma20", "met": True, "label": "VN-Index trên MA20", "figure": "MA20 1.712,40"},
        {"id": "volume", "met": True, "label": "Khối lượng khớp lệnh ≥ trung bình 20 phiên", "figure": "1,70 lần"},
        {"id": "breadth", "met": False, "label": "Số mã tăng > số mã giảm", "figure": "120 tăng · 210 giảm"},
        {"id": "spread", "met": False, "label": "Trung bình cộng các mã tăng", "figure": "−0,42%"}]}


def test_a_condition_without_figures_is_named_unknown_and_not_counted_either_way():
    shape = {**SHAPE, "ma20": {"status": "missing", "reason": "Thiếu nến 1 trong 20 phiên"}}
    out = recovery_checks(shape, {"status": "missing", "reason": "Không tải được bảng giá cả sàn"})
    assert (out["met"], out["known"]) == (1, 1)  # only the volume has figures
    assert out["checks"][0] == {"id": "ma20", "met": None, "label": "VN-Index trên MA20", "figure": "chưa có số (Thiếu nến 1 trong 20 phiên)"}
    assert out["checks"][2]["met"] is None and out["checks"][3]["met"] is None
    assert recovery_checks(None, None)["status"] == "missing"


def test_ties_do_not_count_as_met():
    shape = {**SHAPE, "volume": {**SHAPE["volume"], "ratio20": "1.00"}}
    board = {**BOARD, "breadth": {**BOARD["breadth"], "up": 210}, "spread": {**BOARD["spread"], "mean_pct": "0.0000"}}
    checks = {c["id"]: c["met"] for c in recovery_checks(shape, board)["checks"]}
    assert checks == {"ma20": True, "volume": True, "breadth": False, "spread": False}  # ≥ for volume as labelled; > for the rest


def test_a_snapshot_stored_before_ma20_or_lan_toa_names_them_unknown():
    old_shape = {k: v for k, v in SHAPE.items() if k != "ma20"}
    old_board = {k: v for k, v in BOARD.items() if k != "spread"}
    checks = {c["id"]: c for c in recovery_checks(old_shape, old_board)["checks"]}
    assert checks["ma20"]["met"] is None and checks["spread"]["met"] is None
    assert checks["ma20"]["figure"] == "chưa có số (ảnh chụp phiên này chưa có mục này)"
    assert checks["volume"]["met"] is True and checks["breadth"]["met"] is False
