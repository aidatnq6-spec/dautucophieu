"""Tổng kết năm (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md): each figure from a part the app
already has, read for one year; what is missing is named, never filled in."""

from datetime import date

from investment_agent.domain.ledger import parse_events
from investment_agent.domain.year_review import year_cashflow, year_contributions, year_flows, year_portfolio, year_tower


def ev(event_id, kind, day, **fields):
    return {"event_id": event_id, "type": kind, "effective_at": day, "sequence": 0, **fields}


def test_the_years_return_is_chained_from_its_months_and_the_values_bound_it():
    perf = {"monthly": [{"month": "2025-12", "portfolio": "0.5", "vnindex": "0.5"},
                        {"month": "2026-01", "portfolio": "0.10", "vnindex": "0.02"},
                        {"month": "2026-02", "portfolio": "-0.05", "vnindex": "0.03"}],
            "series": [{"date": "2025-12-31", "value": "1000"}, {"date": "2026-01-30", "value": "1300"}, {"date": "2026-02-27", "value": "1240"}]}
    out = year_portfolio(perf, year=2026)
    assert out["return"] == "0.0450" and out["vnindex"] == "0.0506"  # 1.10 × 0.95 − 1; 1.02 × 1.03 − 1
    assert out["start"] == {"date": "2025-12-31", "value": "1000"} and out["end"] == {"date": "2026-02-27", "value": "1240"} and out["note"] is None
    late = year_portfolio({**perf, "series": perf["series"][1:]}, year=2026)
    assert late["start"]["date"] == "2026-01-30" and late["note"] == "sổ giao dịch bắt đầu 30/01/2026: tính từ ngày đó"
    assert year_portfolio(perf, year=2027)["return"] is None


def test_the_years_flows_are_dated_in_it_and_gains_taken_are_the_ledger_at_the_end_less_the_start():
    events = parse_events([
        ev("d1", "deposit", "2025-12-01", amount="1000"), ev("b1", "buy", "2025-12-02", security_id="ent-a", quantity=10, price="50", fee="0", tax="0"),
        ev("s1", "sell", "2025-12-20", security_id="ent-a", quantity=2, price="60", fee="0", tax="0"),
        ev("d2", "deposit", "2026-03-01", amount="500"), ev("w1", "withdrawal", "2026-06-01", amount="200"),
        ev("s2", "sell", "2026-07-01", security_id="ent-a", quantity=3, price="70", fee="0", tax="0")])
    out = year_flows(events, year=2026)
    assert (out["deposits"], out["withdrawals"], out["net"]) == ("500", "200", "300")
    assert out["realized"] == "60"  # 3 × (70 − 50); the 2025 sale (20) belongs to 2025
    assert out["dividends"] == "0" and out["tax_withheld"] == "0"


def test_goc_von_deu_over_the_years_months_so_far():
    status = {"months": [{"month": "2025-12", "net": "8", "status": "met"}, {"month": "2026-01", "net": "8", "status": "met"},
                         {"month": "2026-02", "net": "3", "status": "short"}, {"month": "2026-03", "net": "0", "status": "pending"}]}
    assert year_contributions(status, amount="8", year=2026) == {"months": 2, "met": 1, "planned": "16", "put_in": "11"}
    assert year_contributions(None, amount=None, year=2026) is None


def test_thu_chi_adds_the_closed_months_and_names_the_ones_not_entered():
    stored = {"months": {"2026-01": {"income": "100", "spending": "60"}, "2026-03": {"income": "100", "spending": "80"},
                         "2026-11": {"income": "100", "spending": "10"}}}
    out = year_cashflow(stored, year=2026, today=date(2026, 4, 10))
    assert out == {"months": 2, "missing": ["2026-02"], "income": "200", "spending": "140", "saved": "60", "rate": "0.3000"}
    assert year_cashflow(None, year=2026, today=date(2026, 4, 10))["missing"] == ["2026-01", "2026-02", "2026-03"]
    assert len(year_cashflow(stored, year=2026, today=date(2027, 1, 3))["missing"]) == 9  # the whole year once it is over


def test_the_tower_says_when_the_start_of_the_year_was_never_stored():
    snaps = {"2026-11": {"taken_on": "2026-11-30", "total": "1", "layers": {}}}
    pyramid = {"layers": [{"id": "reserve", "share": None, "target_min": None, "target_max": None, "status": "fixed"},
                          {"id": "gold", "share": "0.05", "target_min": "0.1", "target_max": "0.15", "status": "short"}]}
    out = year_tower(snaps, pyramid, year=2026)
    assert out["start"] is None and out["note"] == "không có số đầu năm 2026: phần mềm bắt đầu lưu ảnh chụp cuối tháng từ 11/2026"
    assert out["end_month"] == "2026-11" and [l["id"] for l in out["now"]] == ["gold"]
    later = year_tower({**snaps, "2026-12": {"taken_on": "2026-12-31", "total": "2", "layers": {}}}, pyramid, year=2027)
    assert later["start"]["total"] == "2" and later["note"] is None


def test_the_years_return_uses_the_unrounded_levels_when_hieu_suat_gives_them():
    perf = {"monthly": [{"month": "2025-12", "portfolio": "0.1", "vnindex": "0", "level": "110.00000000", "index_level": "100.00000000"},
                        {"month": "2026-01", "portfolio": "0.0001", "vnindex": "0.0001", "level": "110.01234500", "index_level": "100.01234500"},
                        {"month": "2026-02", "portfolio": "0.0001", "vnindex": "0.0001", "level": "110.02469000", "index_level": "100.02469000"}],
            "series": [{"date": "2025-12-31", "value": "1"}, {"date": "2026-02-27", "value": "1"}]}
    out = year_portfolio(perf, year=2026)
    assert out["return"] == "0.0002" and out["vnindex"] == "0.0002"  # 110.02469 / 110 − 1 = 0.000224…, not 1.0001² − 1
    started = year_portfolio({**perf, "monthly": perf["monthly"][1:], "series": perf["series"][1:]}, year=2026)
    assert started["return"] == "0.1002"  # no month before: from the ledger's own start at 100
