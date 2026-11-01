from datetime import date, timedelta

import pytest

from investment_agent.domain.screener import ScreenError, build_rows, entered, match, validate_screen

TODAY = date(2026, 11, 2)
SESSIONS = [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(20)]
RECENT = [(TODAY - timedelta(days=20 - i)).isoformat() for i in range(20)]


def _cells(d1="up,>0", w="down,<0", rsi=45, zone="neutral", w_prev=None):
    w_cell = {"macd": w, "rsi": 50, "zone": "neutral", "macd_changed": w_prev is not None, "previous_macd": w_prev}
    return {"D1": {"macd": d1, "rsi": rsi, "zone": zone, "reason": None}, "W": w_cell}


def _rows(**over):
    base = dict(symbols=["FPT", "HPG", "VCB"],
                valuation={"FPT": {"verdict": "cheap", "quality": {"f_score": {"level": "strong"}}},
                           "HPG": {"verdict": "expensive", "quality": {"f_score": {"level": "weak"}}},
                           "VCB": {"verdict": "insufficient", "quality": {"f_score": None, "reason": "Chưa có chỉ số ngành"}}},
                trend={"FPT": _cells(w="up,>0", w_prev="down,<0"), "HPG": _cells(d1="down,<0", rsi=25, zone="oversold")},
                trend_meta={"session_date": TODAY.isoformat(), "previous_date": "2026-10-30"},
                chains={"FPT": ["tailwind"], "HPG": ["headwind", "neutral"]},
                foreign={"sessions": RECENT, "values": {"FPT": {d: "1.5" for d in RECENT}, "HPG": {d: "-2" for d in RECENT[1:]}}},
                events=[{"symbol": "HPG", "kind": "dividend_cash", "key_date": "2026-11-10"}, {"symbol": "FPT", "kind": "meeting", "key_date": "2026-12-20"}],
                events_known={"FPT", "HPG"}, held={"HPG"}, today=TODAY)
    return {r["symbol"]: r for r in build_rows(**{**base, **over})}


def test_each_ticker_gets_its_signal_values_or_none_with_a_reason():
    rows = _rows()
    fpt, hpg, vcb = rows["FPT"], rows["HPG"], rows["VCB"]
    assert fpt["values"] == {"verdict": "cheap", "quality": "strong", "macd_d": "up", "macd_w": "up", "macd_w_cross_up": "yes", "rsi_d": "neutral",
                             "chain": ["tailwind"], "foreign20": "buy", "event14": "no", "held": "no"}
    assert fpt["foreign20_bn"] == "30.00"
    assert hpg["values"]["foreign20"] is None and hpg["missing"]["foreign20"] == f"Thiếu khối ngoại phiên {RECENT[0][8:10]}/{RECENT[0][5:7]}"
    assert hpg["values"]["rsi_d"] == "oversold" and hpg["values"]["event14"] == "yes" and hpg["values"]["held"] == "yes"
    assert hpg["values"]["macd_w_cross_up"] == "no"
    assert vcb["values"]["verdict"] is None and vcb["missing"]["verdict"] == "Chưa đủ số liệu định giá"
    assert vcb["missing"]["quality"] == "Chưa có chỉ số ngành" and vcb["missing"]["macd_d"] == "Chưa có trên bảng Xu hướng"
    assert vcb["missing"]["chain"] == "Mã không thuộc chuỗi giá trị nào"
    assert vcb["values"]["event14"] is None and vcb["missing"]["event14"] == "Chưa đọc Lịch sự kiện của mã"


def test_the_weekly_cross_up_needs_the_line_to_pass_its_signal_not_zero():
    rows = _rows(trend={"FPT": _cells(w="up,>0", w_prev="up,<0")})
    assert rows["FPT"]["values"]["macd_w_cross_up"] == "no"
    first = _rows(trend_meta={"session_date": TODAY.isoformat(), "previous_date": None})
    assert first["FPT"]["values"]["macd_w_cross_up"] is None and first["FPT"]["missing"]["macd_w_cross_up"] == "Chưa có phiên trước để so"


def test_a_stale_trend_board_or_foreign_record_is_missing_not_current():
    rows = _rows(trend_meta={"session_date": "2026-10-01", "previous_date": "2026-09-30"},
                 foreign={"sessions": SESSIONS, "values": {"FPT": {d: "1" for d in SESSIONS}}})
    assert rows["FPT"]["values"]["macd_d"] is None and rows["FPT"]["missing"]["macd_d"] == "Bảng Xu hướng chỉ tới 01/10/2026"
    assert rows["FPT"]["missing"]["foreign20"] == "Khối ngoại đã lưu chỉ tới 20/09/2026"
    few = _rows(foreign={"sessions": RECENT[:5], "values": {}})
    assert few["FPT"]["missing"]["foreign20"] == "Chưa đủ 20 phiên khối ngoại (5)"


def test_a_cells_own_reason_is_kept():
    rows = _rows(trend={"FPT": {"D1": {"macd": None, "rsi": None, "zone": None, "reason": "Lỗi nguồn"}, "W": {"macd": None, "reason": "Lỗi nguồn"}}})
    assert rows["FPT"]["missing"]["macd_d"] == "Lỗi nguồn"


def test_values_inside_a_criterion_are_or_and_criteria_are_and_missing_data_never_matches():
    rows = _rows()
    assert match({"verdict": ["cheap", "fair"], "macd_w_cross_up": ["yes"]}, rows["FPT"]) == (True, [])
    assert match({"verdict": ["cheap"], "quality": ["weak"]}, rows["FPT"]) == (False, [])
    assert match({"chain": ["neutral"]}, rows["HPG"]) == (True, [])  # one of its chains
    assert match({"verdict": ["cheap"]}, rows["VCB"]) == (False, ["verdict"])
    assert match({}, rows["VCB"]) == (True, [])


def test_screens_are_checked_before_saving():
    ok = validate_screen({"name": " Rẻ và mạnh ", "criteria": {"verdict": ["cheap"], "quality": ["strong"]}, "notify": True})
    assert ok["name"] == "Rẻ và mạnh" and ok["criteria"] == {"verdict": ["cheap"], "quality": ["strong"]} and ok["id"]
    for bad, code in (({"name": "", "criteria": {"verdict": ["cheap"]}}, "name_required"),
                      ({"name": "x", "criteria": {}}, "criteria_required"),
                      ({"name": "x", "criteria": {"verdict": ["cheapest"]}}, "invalid_criteria"),
                      ({"name": "x", "criteria": {"moon": ["yes"]}}, "invalid_criteria")):
        with pytest.raises(ScreenError) as err:
            validate_screen(bad)
        assert err.value.code == code


def test_only_tickers_new_to_a_screen_are_reported_and_the_first_run_is_a_baseline():
    assert entered({}, {"s1": ["FPT"]}) == {}
    assert entered({"s1": ["FPT"]}, {"s1": ["FPT", "HPG"], "s2": ["VCB"]}) == {"s1": ["HPG"]}
    assert entered({"s1": ["FPT", "HPG"]}, {"s1": ["FPT"]}) == {}
