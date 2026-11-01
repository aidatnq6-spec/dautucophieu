from datetime import date

import pytest

from investment_agent.domain.screener import ScreenError, build_rows, entered, match, validate_screen

TODAY = date(2026, 11, 2)


def _cells(d1="up,>0", w="down,<0", rsi=45, zone="neutral", w_changed=False):
    return {"D1": {"macd": d1, "rsi": rsi, "zone": zone}, "W": {"macd": w, "rsi": 50, "zone": "neutral", "macd_changed": w_changed}}


def _rows(**over):
    base = dict(symbols=["FPT", "HPG", "VCB"],
                valuation={"FPT": {"verdict": "cheap", "quality": {"f_score": {"level": "strong"}}},
                           "HPG": {"verdict": "expensive", "quality": {"f_score": {"level": "weak"}}},
                           "VCB": {"verdict": "insufficient", "quality": {"f_score": None, "reason": "Chưa có chỉ số ngành"}}},
                trend={"FPT": _cells(w="up,>0", w_changed=True), "HPG": _cells(d1="down,<0", rsi=25, zone="oversold")},
                chains={"FPT": ["tailwind"], "HPG": ["headwind", "neutral"]},
                foreign={"FPT": ["1.5"] * 20, "HPG": ["-2"] * 19},
                events=[{"symbol": "HPG", "kind": "dividend_cash", "key_date": "2026-11-10"}, {"symbol": "FPT", "kind": "meeting", "key_date": "2026-12-20"}],
                held={"HPG"}, today=TODAY)
    return {r["symbol"]: r for r in build_rows(**{**base, **over})}


def test_each_ticker_gets_its_signal_values_or_none_with_a_reason():
    rows = _rows()
    fpt, hpg, vcb = rows["FPT"], rows["HPG"], rows["VCB"]
    assert fpt["values"] == {"verdict": "cheap", "quality": "strong", "macd_d": "up", "macd_w": "up", "macd_w_cross_up": "yes", "rsi_d": "neutral",
                             "chain": ["tailwind"], "foreign20": "buy", "event14": "no", "held": "no"}
    assert fpt["foreign20_bn"] == "30.00"
    assert hpg["values"]["foreign20"] is None and hpg["missing"]["foreign20"] == "Chưa đủ 20 phiên khối ngoại (19)"
    assert hpg["values"]["rsi_d"] == "oversold" and hpg["values"]["event14"] == "yes" and hpg["values"]["held"] == "yes"
    assert hpg["values"]["macd_w_cross_up"] == "no"
    assert vcb["values"]["verdict"] is None and vcb["missing"]["verdict"] == "Chưa đủ số liệu định giá"
    assert vcb["missing"]["quality"] == "Chưa có chỉ số ngành" and vcb["missing"]["macd_d"] == "Chưa có trên bảng Xu hướng"
    assert vcb["missing"]["chain"] == "Mã không thuộc chuỗi giá trị nào"


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
