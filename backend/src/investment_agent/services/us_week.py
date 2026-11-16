"""Chuỗi liên thị trường trong tuần from stored figures (domain.us_chain), for Vĩ mô and Bản tin tuần: US CPI and core CPI, EFFR, the
10-year yield, DXY, USD/VND (Vietcombank), and gold — the world price (XAU/USD) once a week of it is kept, Phú Quý's SJC price before —
with SJC's selling price against the world price in đồng a chỉ. Public figures only."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.us_chain import WEEK, gold_premium, us_chain
from investment_agent.market.gold_price import gold_history, gold_prices
from investment_agent.market.leading import MacroStore

GOLD_KIND = "Vàng miếng SJC"


def us_week(data_dir: Path, *, today: date) -> dict:
    store = MacroStore(Path(data_dir))
    series = {i: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(i)]
              for i in ("us_cpi_yoy", "us_core_cpi_yoy", "fed_effr", "us10y", "dxy", "usd_vnd_vcb", "xau_usd")}
    world = series.pop("xau_usd")
    if world and any(d <= world[-1][0] - WEEK for d, _ in world):
        series["gold"], label, unit = world, "Giá vàng thế giới XAU/USD (gold-api.com)", "USD/oz"
    else:
        kept = gold_history(Path(data_dir)).get(GOLD_KIND) or {}
        series["gold"] = sorted((date.fromisoformat(d), Decimal(v)) for d, v in kept.items())
        label, unit = f"{GOLD_KIND} (giá mua vào của Phú Quý)", "đ/chỉ"
    out = us_chain(series, today=today)
    prices = gold_prices(Path(data_dir))
    sell = ((prices.get("kinds") or {}).get(GOLD_KIND) or {}).get("sell")
    fx = series.get("usd_vnd_vcb") or []
    for n in out["nodes"]:
        if n["id"] == "gold":
            n["label"], n["unit"] = label, unit
            n["premium"] = (gold_premium(xau=world[-1], usd_vnd=fx[-1], sjc_sell=Decimal(sell), sjc_as_of=prices.get("as_of"))
                            if world and fx and sell else None)
    return out
