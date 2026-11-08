from investment_agent.valuation.peer_compare import COLUMNS, compare


def _bank(pb, npl, ldr, casa=None):
    return {"pb": pb, "BAD_LOANS_RATIO_AQ": npl, "LOANS_TO_DEPOSIT_AQ": ldr, **({"CASA": casa} if casa else {})}


PEERS = {
    "AAA": {"2026-Q2": _bank("1.10", "0.0150", "0.90"), "2026-Q3": _bank("1.20", "0.0140", "0.95", "0.30"), "2025-Q4": {"CAR": "0.1200"}},
    "BBB": {"2026-Q2": _bank("1.50", "0.0100", "1.05"), "2026-Q3": _bank("1.40", "0.0090", "1.10", "0.20"), "2025-Q4": {"CAR": "0.1450"}},
    "CCC": {"2026-Q2": _bank("0.90", "0.0300", "0.80")},  # not reported Q3 yet
    "DDD": {},  # nothing stored
}
NOW = {"AAA": {"quality": "6/9", "gap": "-0.2000"}, "BBB": {"quality": "4/7", "gap": "0.1000"}, "CCC": {"quality": None, "gap": None}, "DDD": {}}


def test_peers_are_compared_at_the_latest_quarter_all_of_them_have_unless_another_is_chosen():
    out = compare("bank", PEERS, NOW, focus="AAA")
    assert out["period"] == "2026-Q2" and out["periods"] == ["2026-Q3", "2026-Q2"]  # CCC has no Q3: the default waits for it
    rows = {r["symbol"]: r for r in out["rows"]}
    assert rows["CCC"]["values"]["pb"] == "0.90" and rows["DDD"]["reason"] == "Chưa có số liệu (đồng bộ lúc 20:00)"
    out = compare("bank", PEERS, NOW, focus="AAA", period="2026-Q3")
    rows = {r["symbol"]: r for r in out["rows"]}
    assert rows["CCC"]["values"]["pb"] is None and rows["CCC"]["reason"] == "Chưa có số Q3/2026"  # left blank, never an older quarter
    assert out["focus"] == "AAA" and [r["symbol"] for r in out["rows"]] == ["AAA", "BBB", "CCC", "DDD"]


def test_each_column_marks_its_best_and_worst_in_its_own_direction_and_gives_the_median():
    out = compare("bank", PEERS, NOW, focus="AAA", period="2026-Q2")
    assert out["best"]["pb"] == ["CCC"] and out["worst"]["pb"] == ["BBB"]  # a lower P/B is cheaper
    assert out["best"]["BAD_LOANS_RATIO_AQ"] == ["BBB"] and out["worst"]["BAD_LOANS_RATIO_AQ"] == ["CCC"]  # lower NPL is better
    assert "LOANS_TO_DEPOSIT_AQ" not in out["best"]  # LDR: neither way is plainly better, so not marked
    assert out["median"]["pb"] == "1.10" and out["median"]["BAD_LOANS_RATIO_AQ"] == "0.0150"
    assert out["best"]["quality"] == ["AAA"] and out["worst"]["quality"] == ["BBB"]  # 6/9 against 4/7, as shares of criteria met
    assert out["best"]["gap"] == ["AAA"]  # price furthest below the fair value


def test_a_ticker_counts_the_columns_where_it_is_in_the_best_third():
    out = compare("bank", PEERS, NOW, focus="AAA", period="2026-Q2")
    rows = {r["symbol"]: r for r in out["rows"]}
    # Ranked columns with values here: pb (CCC best), NPL (BBB), CAR 2025 (BBB), quality (AAA), gap (AAA); the best third of 3 or 2
    # values is one ticker.
    assert rows["AAA"]["top"] == 2 and rows["BBB"]["top"] == 2 and rows["CCC"]["top"] == 1 and rows["DDD"]["top"] == 0
    assert out["ranked"] == 5


def test_year_end_car_is_read_at_the_last_year_end_before_the_quarter():
    out = compare("bank", PEERS, NOW, focus="AAA", period="2026-Q3")
    rows = {r["symbol"]: r for r in out["rows"]}
    assert out["car_year"] == "2025" and rows["AAA"]["values"]["CAR"] == "0.1200" and out["best"]["CAR"] == ["BBB"]
    assert compare("bank", PEERS, NOW, focus="AAA", period="2025-Q4")["car_year"] == "2025"


def test_every_kind_has_its_columns_with_a_direction_or_none():
    assert [c[0] for c in COLUMNS[None]] == ["market_cap", "pe", "pb", "ev_ebitda", "roe", "gross_margin", "revenue_yoy", "npat_parent_yoy",
                                            "debt_to_equity", "quality", "gap", "pe_now", "pb_now"]
    assert {c[0] for c in COLUMNS["bank"]} >= {"GROUP2_RATIO", "CASA", "CAR", "NET_INTEREST_MARGIN_TR_AVG5Q"}
    assert all(c[3] in ("high", "low", None) for cols in COLUMNS.values() for c in cols)


def test_multiples_at_todays_price_are_marked_but_not_counted_twice_with_the_quarter_end_ones():
    now = {s: {**v, "pe_now": n, "pb_now": n} for (s, v), n in zip(NOW.items(), ("9.00", "7.00", None, None))}
    plain = compare("bank", PEERS, NOW, focus="AAA", period="2026-Q2")
    out = compare("bank", PEERS, now, focus="AAA", period="2026-Q2")
    assert out["best"]["pe_now"] == ["BBB"] and out["worst"]["pe_now"] == ["AAA"]  # the lower is the cheaper
    assert out["ranked"] == plain["ranked"] and [r["top"] for r in out["rows"]] == [r["top"] for r in plain["rows"]]
    assert {r["symbol"]: r for r in out["rows"]}["BBB"]["values"]["pb_now"] == "7.00"
