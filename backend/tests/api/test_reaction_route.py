import json
from datetime import datetime, timedelta

from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore

from signed_client import call
from test_passive_income_route import client as base_client


def test_a_watched_ticker_shows_the_price_after_each_report(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("KDH\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2, "sectors": {"KDH": "Bất động sản"}}), encoding="utf-8")
    StatementStore(tmp_path / "statements").save({"symbol": "KDH", "years": {}, "quarters": {"2025-Q3": {"npat_parent": "100"}, "2026-Q3": {"npat_parent": "50"}},
                                                  "quarters_created": {"2025-Q3": "2025-10-29", "2026-Q3": "2026-10-30"}})
    days = [datetime(2026, 10, 1) + timedelta(days=i) for i in range(60)]
    SeriesStore(tmp_path / "trend-sources").upsert("KDH-1d", [(d, str(20 + i * 0.1)) for i, d in enumerate(days)])
    SeriesStore(tmp_path / "trend-sources").upsert("VNINDEX-1d", [(d, "1000") for d in days])
    c, clock = base_client(tmp_path)
    body = call(c, clock, "GET", "/internal/stock/KDH/reaction").json()
    last = body["rows"][-1]
    assert last["quarter"] == "2026-Q3" and last["profit_yoy"] == "-0.5000" and last["after_20"] is not None and last["index_20"] == "0.0000"
    assert body["summary"]["bad_bought"] == 1
    assert call(c, clock, "GET", "/internal/stock/HPG/reaction").status_code == 404
