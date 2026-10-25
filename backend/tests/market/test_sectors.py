import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.prices import PriceBar, PriceError, PriceStore, ingest
from investment_agent.market.sectors import breadth, index_summary, load_sectors, sector_rows
from investment_agent.market.view import EmptyMarket, PricePoint, SyntheticMarket

CAL = TradingCalendar(version="t", source="test", holidays=frozenset(), first=date(2026, 1, 1), last=date(2026, 12, 31))


def row(ticker, d1, d20, held=False):
    return {"ticker": ticker, "groups": [], "held": held, "close": "1" if d1 is not None else None, "date": None,
            "change_1d": d1, "change_20d": d20, "stale": False}


def test_load_sectors_reads_the_saved_classification(tmp_path):
    assert load_sectors(tmp_path) == ({}, None)
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "vnstock:vci", "level": 2,
                                                         "sectors": {"MBB": "Ngân hàng"}}), encoding="utf-8")
    assert load_sectors(tmp_path) == ({"MBB": "Ngân hàng"}, "2026-10-25")


def test_sectors_average_changes_count_breadth_and_rank_by_twenty_sessions():
    rows = [row("MBB", "-0.0050", "-0.0050", held=True), row("VCB", "0.0100", "0.0300"), row("ACB", "0.0000", None),
            row("SSI", "-0.0099", "-0.0362", held=True), row("VND", "0.0200", "0.0100"), row("XYZ", None, None)]
    sectors = {"MBB": "Ngân hàng", "VCB": "Ngân hàng", "ACB": "Ngân hàng", "SSI": "Dịch vụ tài chính", "VND": "Dịch vụ tài chính"}
    result = sector_rows(rows, sectors)
    assert [s["sector"] for s in result] == ["Ngân hàng", "Dịch vụ tài chính", "Chưa phân ngành"]
    bank = result[0]
    assert (bank["count"], bank["avg_1d"], bank["avg_20d"], bank["up"], bank["down"], bank["flat"]) == (3, "0.0017", "0.0125", 1, 1, 1)
    assert (bank["best"], bank["worst"], bank["held"]) == ("VCB", "MBB", ["MBB"])
    assert result[1]["avg_20d"] == "-0.0131" and result[2]["avg_20d"] is None


def test_breadth_counts_session_moves():
    rows = [row("A", "0.0100", None), row("B", "-0.0100", None), row("C", "0.0000", None), row("D", None, None)]
    assert breadth(rows) == {"up": 1, "down": 1, "flat": 1, "missing": 1}


def test_index_summary_compares_with_the_twenty_session_average():
    days = list(CAL.sessions(date(2026, 9, 1), date(2026, 10, 23)))[-21:]
    closes = [PricePoint(Decimal(1700), d) for d in days[:20]] + [PricePoint(Decimal("1774.15"), days[-1])]
    s = index_summary(SyntheticMarket(history={"VNINDEX": closes}))
    assert s == {"entity_id": "VNINDEX", "close": "1774.15", "date": "2026-10-23", "change_1d": "0.0436", "change_20d": "0.0436",
                 "ma20": "1703.71", "above_ma20": True}
    assert index_summary(EmptyMarket()) is None


def test_index_bars_are_stored_in_points_but_stocks_must_be_in_dong(tmp_path):
    def bar(entity, currency):
        return PriceBar(entity_id=entity, session_date=date(2026, 10, 23), open="1761.38", high="1775.19", low="1750.83", close="1774.15",
                        volume=1, currency=currency, source_id="t", observed_at="2026-10-23T10:00:00Z", provenance_mode="latest_restated")
    ingest(PriceStore(tmp_path), CAL, [bar("VNINDEX", "POINT")], revision_id="r1")
    with pytest.raises(PriceError):
        ingest(PriceStore(tmp_path), CAL, [bar("FPT", "POINT")], revision_id="r2")
    with pytest.raises(PriceError):
        ingest(PriceStore(tmp_path), CAL, [bar("VNINDEX", "VND")], revision_id="r3")
