import random
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # FPT bought 100 × 50,000

END = date(2026, 12, 25)  # a Friday before the test clock (2027-01-15)


def levels(returns):
    level, out = 100.0, [100.0]
    for r in returns:
        level *= 1 + r
        out.append(level)
    return [(END - timedelta(weeks=len(out) - 1 - i), v) for i, v in enumerate(out)]


def client(tmp_path):
    rng = random.Random(1)
    n = 160
    index = [rng.gauss(0.002, 0.025) for _ in range(n)]
    oil = [rng.gauss(0, 0.05) for _ in range(n)]
    usd = [rng.gauss(0, 0.01) for _ in range(n)]
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("VNINDEX-1d", [(datetime.combine(d, datetime.min.time()), f"{v:.4f}") for d, v in levels(index)])
    series.upsert("FPT-1d", [(datetime.combine(d, datetime.min.time()), f"{v:.4f}")
                             for d, v in levels([i - 0.3 * o + rng.gauss(0, 0.01) for i, o in zip(index, oil)])])
    series.upsert("GAS-1d", [(datetime.combine(d, datetime.min.time()), f"{v:.4f}")
                             for d, v in levels([i + 0.25 * o + rng.gauss(0, 0.01) for i, o in zip(index, oil)])])
    series.upsert("NEW-1d", [(datetime.combine(d, datetime.min.time()), f"{v:.4f}") for d, v in levels(index[-20:])])
    store = MacroStore(tmp_path)
    store.upsert("factor_oil", [(d, f"{v:.4f}") for d, v in levels(oil)], entry="auto")
    store.upsert("factor_usd", [(d, f"{v:.4f}") for d, v in levels(usd)], entry="auto")
    (tmp_path / "market-symbols.txt").write_text("GAS\nNEW\nHPG\n", encoding="utf-8")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    setup_owner(c, clock)
    buy_fpt(c, clock)
    return c, clock


def test_held_tickers_first_then_the_watchlist_each_with_its_oil_and_dollar_reading(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/macro/sensitivity").json()
    rows = {r["symbol"]: r for r in body["rows"]}
    assert [r["symbol"] for r in body["rows"]] == ["FPT", "GAS", "NEW", "HPG"]
    assert rows["FPT"]["held"] is True and rows["FPT"]["oil"]["class"] == "hurt"
    assert rows["GAS"]["held"] is False and rows["GAS"]["oil"]["class"] == "benefit" and rows["GAS"]["weeks"] == 156
    assert rows["NEW"] == {"symbol": "NEW", "held": False, "status": "insufficient", "weeks": 20}
    assert rows["HPG"] == {"symbol": "HPG", "held": False, "status": "insufficient", "weeks": 0}  # no stored closes
    assert body["exposure"]["oil"] == {"benefit": "0", "hurt": "1"} and body["exposure"]["total"] == "5000000"
    assert body["factors"] == {"oil": END.isoformat(), "usd": END.isoformat()}


def test_without_factor_history_every_row_is_insufficient(tmp_path):
    c, clock = client(tmp_path)
    for key in ("factor_oil", "factor_usd"):
        (tmp_path / "macro" / f"{key}.json").unlink()
    body = call(c, clock, "GET", "/internal/macro/sensitivity").json()
    assert body["factors"] == {"oil": None, "usd": None} and all(r["status"] == "insufficient" for r in body["rows"])
