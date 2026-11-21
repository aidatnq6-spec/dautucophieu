"""Reads each chain member's weekly P/E and P/B the way Định giá does (valuation.sources.valuation_record for the report source, share
count and publication days; valuation.weekly for the weeks) and hands them to domain.chain_valuation. Public company data only."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from investment_agent.domain.chain_valuation import chain_valuation
from investment_agent.market.series import SeriesStore
from investment_agent.valuation.sources import valuation_record
from investment_agent.valuation.weekly import weekly_multiples


def member_weeks(data_dir: Path, symbol: str, *, today: date) -> dict:
    try:
        v = valuation_record(Path(data_dir), symbol, today=today)
    except Exception:
        return {}
    out = weekly_multiples(v.get("record"), SeriesStore(Path(data_dir) / "trend-sources").read(f"{symbol}-1d"), today=today,
                           shares=v.get("shares"), published=v.get("published"))
    return {"pe": out["pe"]["points"], "pb": out["pb"]["points"]}


def chain_valuation_board(data_dir: Path, chains: list[dict], *, today: date) -> list[dict]:
    symbols = sorted({s for c in chains for s in c["symbols"]})
    return chain_valuation(chains, {s: member_weeks(data_dir, s, today=today) for s in symbols}, today=today)
