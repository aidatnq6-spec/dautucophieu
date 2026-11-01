from investment_agent.domain.ledger import parse_events, replay, snapshots


def test_snapshots_match_a_replay_of_each_prefix():
    rows = [{"event_id": "d0", "type": "deposit", "effective_at": "2026-01-02", "sequence": 0, "amount": "10000000"},
            {"event_id": "b1", "type": "buy", "effective_at": "2026-01-05", "sequence": 0, "security_id": "FPT", "quantity": 100, "price": "50000",
             "fee": "7500", "tax": "0"},
            {"event_id": "b2", "type": "buy", "effective_at": "2026-01-06", "sequence": 0, "security_id": "FPT", "quantity": 50, "price": "40000",
             "fee": "0", "tax": "0"},
            {"event_id": "s1", "type": "sell", "effective_at": "2026-01-07", "sequence": 0, "security_id": "FPT", "quantity": 150, "price": "45000",
             "fee": "0", "tax": "6750"}]
    events = parse_events(rows)
    got = list(snapshots(events))
    for i, (event, state) in enumerate(got):
        expected = {p.security_id: (p.quantity, p.pending_quantity, p.average_cost) for p in replay(events[:i + 1]).positions}
        assert event.event_id == rows[i]["event_id"] and state == expected
