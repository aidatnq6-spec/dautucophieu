import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from investment_agent.market.series import SeriesStore
from investment_agent.services.flow_board import chain_board, flow_board

LAST = date(2026, 11, 20)


def store_closes(data, symbol, values, end=LAST):
    days = [end - timedelta(days=len(values) - 1 - i) for i in range(len(values))]
    SeriesStore(data / "trend-sources").upsert(f"{symbol}-1d", [(datetime.combine(d, datetime.min.time()), v) for d, v in zip(days, values)])


def snapshot(data, day, symbols):
    (data / "brief").mkdir(exist_ok=True)
    (data / "brief" / f"{day.isoformat()}.json").write_text(json.dumps({"session_date": day.isoformat(), "board": {"symbols": {
        s: {"foreign_net_bn": v} for s, v in symbols.items()}}}), encoding="utf-8")


def test_the_board_reads_closes_bars_and_the_foreign_net_of_the_session_snapshots(tmp_path):
    store_closes(tmp_path, "AAA", ["10"] * 399 + ["11"])
    store_closes(tmp_path, "BBB", ["10"] * 400)
    for i in range(6):
        snapshot(tmp_path, LAST - timedelta(days=5 - i), {"AAA": "1.5", "BBB": "-0.2"})
    bars = {"AAA": [(LAST - timedelta(days=20 - i), Decimal(11000), Decimal(9000), Decimal(10500), 1000 if i < 20 else 3000) for i in range(21)]}
    out = flow_board(tmp_path, ["AAA", "BBB", "CCC"], held={"BBB"}, bars_for=lambda s: bars.get(s, []))
    rows = {r["symbol"]: r for r in out["rows"]}
    assert rows["AAA"]["volume_ratio"] == "3.00" and rows["AAA"]["foreign_run"] == 6 and "foreign_buy_5" in rows["AAA"]["flags"]
    assert rows["BBB"]["held"] is True and rows["BBB"]["foreign_run"] == -6 and rows["CCC"]["missing"] == ["closes"]
    assert out["date"] == "2026-11-20" and out["counts"]["foreign_buy_5"] == 1 and out["counts"]["foreign_sell_5"] == 1
    assert [r["symbol"] for r in out["rows"]][0] == "BBB"  # held first


def test_the_chain_board_reads_each_members_closes(tmp_path):
    store_closes(tmp_path, "AAA", [str(100 + i) for i in range(400)])
    chains = [{"id": "x", "name": "X", "symbols": ["AAA", "ZZZ"]}]
    (row,) = chain_board(tmp_path, chains, today=LAST)
    assert row["priced"] == 1 and row["no_data"] == ["ZZZ"] and row["periods"]["w1"]["n"] == 1
