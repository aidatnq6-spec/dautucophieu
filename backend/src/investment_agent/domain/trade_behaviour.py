"""Soi hành vi giao dịch: how often, how long and at what cost the owner traded, by year, straight from TCBS statements. Figures only: it names no
behaviour and judges none. Personal data; read for the page and not kept, never sent to a model."""

from collections import Counter, defaultdict, deque
from decimal import ROUND_HALF_UP, Decimal

SHORT_DAYS, LONG_DAYS = 30, 180
_Q4, _Q1 = Decimal("0.0001"), Decimal("0.1")


def merge_files(files: list[list[dict]]) -> tuple[list[dict], int]:
    """All orders of the files, an order that appears in more than one file counted once. Equal lines inside one file are separate fills, and stay."""
    def key(o: dict) -> tuple:
        return (o["order_no"], o["date"], o["symbol"], o["type"], o["quantity"], o["price"])
    most: Counter = Counter()
    for orders in files:
        for k, n in Counter(key(o) for o in orders).items():
            most[k] = max(most[k], n)
    taken: Counter = Counter()
    merged, dropped = [], 0
    for orders in files:
        for o in orders:
            k = key(o)
            if taken[k] < most[k]:
                taken[k] += 1
                merged.append(o)
            else:
                dropped += 1
    return merged, dropped


def _ordered(orders: list[dict]) -> list[dict]:
    return sorted(orders, key=lambda o: (o["date"], o["type"] != "sell"))  # shares bought on a day cannot be sold that day (T+2)


def _held(orders: list[dict]) -> tuple[list[tuple[int, int, int]], list[str]]:
    """(sale year, days held, shares) first in first out; tickers ever sold beyond their bought shares are left out whole, for their lots cannot be followed."""
    lots: dict[str, deque] = defaultdict(deque)
    pieces: dict[str, list] = defaultdict(list)
    broken = set()
    for o in _ordered(orders):
        s = o["symbol"]
        if o["type"] == "buy":
            lots[s].append([o["date"], o["quantity"]])
            continue
        left = o["quantity"]
        while left and lots[s]:
            take = min(left, lots[s][0][1])
            pieces[s].append((o["date"].year, (o["date"] - lots[s][0][0]).days, take))
            lots[s][0][1] -= take
            left -= take
            if not lots[s][0][1]:
                lots[s].popleft()
        if left:
            broken.add(s)
    return [p for s, ps in pieces.items() if s not in broken for p in ps], sorted(broken)


def _ratio(a: Decimal, b: Decimal) -> str | None:
    return format((a / b).quantize(_Q4, ROUND_HALF_UP), "f") if b else None


def _money(v: Decimal) -> str:
    return format(v.quantize(Decimal(1), ROUND_HALF_UP), "f")


def _row(year: int | None, orders: list[dict], held: list[tuple[int, int, int]]) -> dict:
    value = lambda kind: sum((o["quantity"] * Decimal(o["price"]) for o in orders if o["type"] == kind), Decimal(0))  # noqa: E731
    buy, sell = value("buy"), value("sell")
    fee, tax = sum((Decimal(o["fee"]) for o in orders), Decimal(0)), sum((Decimal(o["tax"]) for o in orders), Decimal(0))
    shares = Decimal(sum(q for _, _, q in held))
    band = lambda test: _ratio(Decimal(sum(q for _, d, q in held if test(d))), shares)  # noqa: E731
    return {"year": year, "orders": len(orders), "buys": sum(o["type"] == "buy" for o in orders), "sells": sum(o["type"] == "sell" for o in orders), "symbols": len({o["symbol"] for o in orders}),
            "buy_value": _money(buy), "sell_value": _money(sell), "fee": _money(fee), "tax": _money(tax), "costs": _money(fee + tax), "cost_share": _ratio(fee + tax, buy + sell),
            "avg_hold_days": format((Decimal(sum(d * q for _, d, q in held)) / shares).quantize(_Q1, ROUND_HALF_UP), "f") if shares else None,
            "held_short": band(lambda d: d <= SHORT_DAYS), "held_mid": band(lambda d: SHORT_DAYS < d <= LONG_DAYS), "held_long": band(lambda d: d > LONG_DAYS)}


def trade_behaviour(orders: list[dict]) -> dict:
    """By year of the order; holding time by year of the sale."""
    if not orders:
        return {"years": [], "total": None, "no_holding_time": []}
    held, broken = _held(orders)
    by_year = sorted({o["date"].year for o in orders})
    return {"years": [_row(y, [o for o in orders if o["date"].year == y], [h for h in held if h[0] == y]) for y in by_year], "total": _row(None, orders, held), "no_holding_time": broken}
