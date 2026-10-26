from datetime import date

from investment_agent.domain.ledger import parse_events
from investment_agent.domain.time_weighted import performance

D1, D2, D3, D4 = date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28), date(2026, 11, 2)


def events(*extra):
    return parse_events([
        {"event_id": "d1", "type": "deposit", "effective_at": "2026-10-26", "sequence": 0, "amount": "1000000"},
        {"event_id": "b1", "type": "buy", "effective_at": "2026-10-26", "sequence": 1, "security_id": "FPT", "quantity": 10,
         "price": "50000", "fee": "0", "tax": "0"}, *extra])


CLOSES = {"FPT": {D1: 50000, D2: 55000, D3: 55000, D4: 60000}}
INDEX = {D1: 1000.0, D2: 1010.0, D3: 1020.0, D4: 1030.0}


def test_time_weighted_return_ignores_deposits_and_compares_with_vnindex():
    extra = {"event_id": "d2", "type": "deposit", "effective_at": "2026-10-28", "sequence": 0, "amount": "1000000"}
    out = performance(events(extra), closes=CLOSES, index=INDEX, today=D4)
    days = {p["date"]: p for p in out["series"]}
    assert days["2026-10-26"]["portfolio"] == "100.00" and days["2026-10-26"]["vnindex"] == "100.00"
    # 26/10: 500k cash + 500k FPT = 1.0M; 27/10: FPT 550k -> 1.05M (+5%); 28/10: +1M deposit, no market move -> still 105.00
    assert days["2026-10-27"]["portfolio"] == "105.00" and days["2026-10-28"]["portfolio"] == "105.00"
    # 02/11: FPT 600k -> 2.1M vs 2.05M: +2.439% -> 107.56
    assert days["2026-11-02"]["portfolio"] == "107.56" and days["2026-11-02"]["vnindex"] == "103.00"
    assert days["2026-11-02"]["value"] == "2100000"
    assert out["total"] == {"portfolio": "0.0756", "vnindex": "0.0300", "since": "2026-10-26", "days": 4}


def test_monthly_returns_chain_within_each_month():
    out = performance(events(), closes=CLOSES, index=INDEX, today=D4)
    assert out["monthly"] == [{"month": "2026-10", "portfolio": "0.0500", "vnindex": "0.0200"},
                              {"month": "2026-11", "portfolio": "0.0476", "vnindex": "0.0098"}]


def test_a_day_without_a_price_is_skipped_not_guessed():
    closes = {"FPT": {D1: 50000, D3: 55000}}
    out = performance(events(), closes=closes, index=INDEX, today=D3)
    assert [p["date"] for p in out["series"]] == ["2026-10-26", "2026-10-28"] and out["skipped_days"] == ["2026-10-27"]


def test_no_events_means_no_series():
    out = performance([], closes={}, index=INDEX, today=D4)
    assert out["series"] == [] and out["total"] is None
