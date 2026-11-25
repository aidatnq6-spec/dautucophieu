import json
from datetime import datetime, timezone

from investment_agent.market.fundamentals_vndirect import VndirectFundamentals, build_record

NOW = datetime(2026, 11, 13, 14, tzinfo=timezone.utc)
B = 10**9


def statements():
    year = {"npat_parent": str(9000 * B), "eps": "5200", "equity": str(40000 * B), "revenue": str(60000 * B), "gross_profit": str(23000 * B),
            "selling": str(2000 * B), "admin": str(3500 * B), "npat": str(10000 * B), "total_assets": str(80000 * B), "current_assets": str(50000 * B),
            "current_liabilities": str(30000 * B), "long_liabilities": str(5000 * B), "receivables": str(15000 * B), "cfo": str(11000 * B),
            "fin_income": str(1500 * B), "fin_expense": str(700 * B), "pbt": str(12000 * B), "other_receivables": str(800 * B),
            "other_receivables_lt": str(200 * B), "prepay_suppliers": str(300 * B), "st_loans_receivable": str(40 * B), "lt_loans_receivable": str(60 * B),
            "interest_received": str(900 * B)}
    return {"symbol": "FPT", "years": {"2025": year}, "quarters": {"2026-Q3": {"npat_parent": str(2600 * B), "equity": str(45000 * B)}}}


EVENTS = [{"id": "1", "code": "FPT", "type": "DIVIDEND", "dividend": 1000.0, "effectiveDate": "2026-05-28"},
          {"id": "2", "code": "FPT", "type": "STOCKDIV", "ratio": 15.0, "effectiveDate": "2026-05-25"},
          {"id": "3", "code": "FPT", "type": "KINDDIV", "ratio": 10.0, "effectiveDate": "2025-06-10"},
          {"id": "4", "code": "FPT", "type": "ISSUE", "ratio": 2.0, "effectiveDate": "2024-04-04"},
          {"id": "5", "code": "FPT", "type": "MEETING", "effectiveDate": "2026-03-26"}]


def test_the_record_has_the_shape_and_signs_the_valuation_reads():
    rec = build_record("FPT", statements(), EVENTS, shares="1885727648", now=NOW)
    assert rec["source"] == "vndirect:finfo" and rec["shares_outstanding"] == "1885727648"
    assert rec["years"]["2025"] == {"npat": str(9000 * B), "eps": "5200", "equity": str(40000 * B)}
    assert rec["quarters"]["2026-Q3"] == {"npat": str(2600 * B), "equity": str(45000 * B)}
    annual = rec["annual"]["2025"]
    assert annual["selling"] == str(-2000 * B) and annual["admin"] == str(-3500 * B)  # costs negative, as Vnstock served them
    assert annual["profit"] == str(10000 * B) and annual["receivables"] == str(15000 * B) and annual["cfo"] == str(11000 * B)
    # for Lợi nhuận phụ thuộc thu nhập tài chính: both as VNDirect gives them (the expense positive)
    assert (annual["fin_income"], annual["fin_expense"], annual["pbt"]) == (str(1500 * B), str(700 * B), str(12000 * B))
    assert (annual["other_receivables"], annual["other_receivables_lt"]) == (str(800 * B), str(200 * B))  # for Phải thu khác lớn
    assert annual["prepay_suppliers"] == str(300 * B)  # for Trả trước người bán lớn
    assert (annual["st_loans_receivable"], annual["lt_loans_receivable"]) == (str(40 * B), str(60 * B))  # cho vay, merged into other from 2026
    assert annual["interest_received"] == str(900 * B)  # for Thu nhập tài chính chưa thu được tiền
    assert rec["dividends"] == [{"date": "2026-05-28", "cash": "1000"}]
    assert rec["issues"] == [{"date": "2025-06-10", "ratio": "0.1"}, {"date": "2026-05-25", "ratio": "0.15"}]
    assert rec["share_issues"] == [{"date": "2024-04-04", "kind": "raise", "ratio": "0.02"}, {"date": "2025-06-10", "kind": "bonus", "ratio": "0.1"},
                                   {"date": "2026-05-25", "kind": "bonus", "ratio": "0.15"}]


def test_a_missing_line_is_left_out_not_filled():
    rec = build_record("FPT", {"symbol": "FPT", "years": {"2025": {"npat_parent": "1"}}, "quarters": {}}, [], shares=None, now=NOW)
    assert rec["years"]["2025"] == {"npat": "1"} and rec["annual"]["2025"] == {} and rec["shares_outstanding"] is None


def test_the_source_reads_the_stored_statements_events_and_shares(tmp_path):
    from investment_agent.market.statements import StatementStore
    StatementStore(tmp_path / "statements").save(statements())

    def get(url):
        if "events?" in url:
            return json.dumps({"data": EVENTS})
        if "ratios/latest" in url:
            return json.dumps({"data": [{"itemCode": "51004", "value": 1.885727648e9, "reportDate": "2026-12-31"}]})
        raise AssertionError(url)
    hose = lambda url: json.dumps({"data": {"list": [{"code": "FPT", "outStanding": "1,885,727,648", "listingVolume": "1,885,727,648"}]}})  # noqa: E731
    rec = VndirectFundamentals(tmp_path, get=get, hose_get=hose).record("FPT", NOW)
    assert rec["shares_outstanding"] == "1885727648" and rec["shares_hose"] == "1885727648" and rec["years"]["2025"]["eps"] == "5200"


def test_hose_outstanding_is_read_from_its_listing_api():
    from investment_agent.market.providers.hose_data import outstanding
    payload = {"data": {"list": [{"code": "SHB", "outStanding": "5,343,703,838", "listingVolume": "4,594,200,024"}]}}
    assert outstanding("SHB", get=lambda url: json.dumps(payload)) == "5343703838"
    assert outstanding("SHB", get=lambda url: json.dumps({"data": {"list": []}})) is None


def test_sync_uses_a_source_that_builds_the_record_itself(tmp_path):
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.series import SeriesStore

    class Source:
        def record(self, sym, now):
            return build_record(sym, statements(), EVENTS, shares="1885727648", now=now)

        def fetch_closes(self, sym, start, end, *, interval, index):
            return [(datetime(2026, 11, 13), "50.1")]
    store = FundamentalsStore(tmp_path / "fundamentals")
    out = sync_fundamentals(store, SeriesStore(tmp_path / "trend-sources"), ["FPT"], provider=Source(), now=NOW, limit=None, sleep=lambda s: None)
    assert out == {"updated": ["FPT"], "errors": {}} and store.read("FPT")["years"]["2025"]["eps"] == "5200"
    assert store.read("FPT")["latest_quarter_seen"]["quarter"] == "2026-Q3"


def test_a_source_paces_the_sync_with_its_own_pause(tmp_path):
    """The 15 s pause was Vnstock's rate limit; VNDirect's public API has none, so its source asks for 1 s (17 tickers: 255 s of waiting
    became 16 s, 21/11/2026). A source without its own pause keeps the old one."""
    from investment_agent.market.fundamentals import PACE_SECONDS, FundamentalsStore, sync_fundamentals
    from investment_agent.market.fundamentals_vndirect import VndirectFundamentals
    from investment_agent.market.series import SeriesStore

    class Source:
        pace_seconds = 1

        def record(self, sym, now):
            return build_record(sym, statements(), EVENTS, shares="1885727648", now=now)

        def fetch_closes(self, sym, start, end, *, interval, index):
            return [(datetime(2026, 11, 13), "50.1")]
    waits = []
    sync_fundamentals(FundamentalsStore(tmp_path / "f"), SeriesStore(tmp_path / "t"), ["FPT", "VNM", "HPG"], provider=Source(), now=NOW, limit=None,
                      sleep=waits.append)
    assert waits == [1, 1]
    old = Source()
    del Source.pace_seconds
    waits.clear()
    sync_fundamentals(FundamentalsStore(tmp_path / "g"), SeriesStore(tmp_path / "u"), ["FPT", "VNM"], provider=old, now=NOW, limit=None, sleep=waits.append)
    assert waits == [PACE_SECONDS]
    assert VndirectFundamentals.pace_seconds == 1


def test_figures_vndirect_lacks_stay_as_fetched_before(tmp_path):
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.series import SeriesStore
    store = FundamentalsStore(tmp_path / "fundamentals")
    store.save({"symbol": "ACB", "fetched_at": "2026-11-01T00:00:00+00:00", "source": "vnstock:vci", "years": {"2025": {"npat": "1", "eps": "3022"}},
                "quarters": {}, "annual": {"2025": {"cfo": "28160074000000"}}, "dividends": [], "issues": [], "share_issues": []})

    class Source:
        def record(self, sym, now):
            return build_record(sym, {"years": {"2025": {"npat_parent": "2"}}, "quarters": {}}, [], shares="1", now=now)

        def fetch_closes(self, sym, start, end, *, interval, index):
            return []
    sync_fundamentals(store, SeriesStore(tmp_path / "trend-sources"), ["ACB"], provider=Source(), now=NOW, limit=None, sleep=lambda s: None)
    rec = store.read("ACB")
    assert rec["years"]["2025"] == {"npat": "2", "eps": "3022"} and rec["annual"]["2025"] == {"cfo": "28160074000000"}  # new wins, old kept


def test_the_share_count_already_held_stays_and_vndirects_is_kept_beside_it(tmp_path):
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.series import SeriesStore
    store = FundamentalsStore(tmp_path / "fundamentals")
    store.save({"symbol": "SHB", "fetched_at": "2026-11-01T00:00:00+00:00", "source": "vnstock:vci", "years": {}, "quarters": {}, "annual": {},
                "dividends": [], "issues": [], "share_issues": [], "shares_outstanding": "5343703838"})

    class Source:
        def record(self, sym, now):
            return build_record(sym, {"years": {}, "quarters": {}}, [], shares="4884333454", now=now)

        def fetch_closes(self, sym, start, end, *, interval, index):
            return []
    sync_fundamentals(store, SeriesStore(tmp_path / "trend-sources"), ["SHB"], provider=Source(), now=NOW, limit=None, sleep=lambda s: None)
    rec = store.read("SHB")
    assert rec["shares_outstanding"] == "5343703838" and rec["shares_vndirect"] == "4884333454"


def _sync_shares(tmp_path, held, hose, vndirect):
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.series import SeriesStore
    store = FundamentalsStore(tmp_path / "fundamentals")
    if held:
        store.save({"symbol": "TCB", "fetched_at": "2026-11-01T00:00:00+00:00", "source": "vnstock:vci", "years": {}, "quarters": {}, "annual": {},
                    "dividends": [], "issues": [], "share_issues": [], "shares_outstanding": held})

    class Source:
        def record(self, sym, now):
            return {**build_record(sym, {"years": {}, "quarters": {}}, [], shares=vndirect, now=now), "shares_hose": hose}

        def fetch_closes(self, sym, start, end, *, interval, index):
            return []
    sync_fundamentals(store, SeriesStore(tmp_path / "trend-sources"), ["TCB"], provider=Source(), now=NOW, limit=None, sleep=lambda s: None)
    return store.read("TCB")


def test_a_share_count_changes_only_when_hose_and_vndirect_agree(tmp_path):
    rec = _sync_shares(tmp_path, "1460374611", "1534951081", "1534951081")
    assert rec["shares_outstanding"] == "1534951081" and rec["shares_check"]["decision"] == "both_sources"


def test_hose_matching_the_held_count_keeps_it(tmp_path):
    rec = _sync_shares(tmp_path, "5343703838", "5343703838", "4884333454")
    assert rec["shares_outstanding"] == "5343703838" and rec["shares_check"]["decision"] == "unchanged"


def test_sources_that_disagree_keep_the_held_count_and_say_so(tmp_path):
    rec = _sync_shares(tmp_path, "10629360621", "7086240414", "10629355539")
    assert rec["shares_outstanding"] == "10629360621"
    assert rec["shares_check"] == {"held": "10629360621", "hose": "7086240414", "vndirect": "10629355539", "decision": "conflict"}


def test_a_new_ticker_takes_hoses_count(tmp_path):
    rec = _sync_shares(tmp_path, None, "3000500833", None)
    assert rec["shares_outstanding"] == "3000500833" and rec["shares_check"]["decision"] == "hose"


def test_the_record_carries_the_fixed_asset_lines_of_the_construction_signs_owner_25_11_2026():
    s = statements()
    s["years"]["2025"].update({"cip": str(10721 * B), "ppe_net": str(133421 * B), "ppe_gross": str(182309 * B), "depreciation": str(8000 * B)})
    annual = build_record("FPT", s, EVENTS, shares=None, now=NOW)["annual"]["2025"]
    assert (annual["cip"], annual["ppe_net"], annual["ppe_gross"], annual["depreciation"]) == (str(10721 * B), str(133421 * B), str(182309 * B), str(8000 * B))


def test_the_record_carries_goodwill_and_equity_for_the_goodwill_sign_owner_25_11_2026():
    s = statements()
    s["years"]["2025"].update({"goodwill": str(5104 * B), "minority_equity": str(6000 * B)})
    annual = build_record("FPT", s, EVENTS, shares=None, now=NOW)["annual"]["2025"]
    assert (annual["goodwill"], annual["equity"], annual["minority_equity"]) == (str(5104 * B), str(40000 * B), str(6000 * B))


def test_the_record_carries_interest_expense_for_the_cover_sign_owner_25_11_2026():
    s = statements()
    s["years"]["2025"]["interest"] = str(2526 * B)
    assert build_record("FPT", s, EVENTS, shares=None, now=NOW)["annual"]["2025"]["interest"] == str(2526 * B)
