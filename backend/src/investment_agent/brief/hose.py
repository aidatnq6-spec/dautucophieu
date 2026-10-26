"""HOSE's own statistics for one session: foreign buy/sell (value and volume) and total trading value.

Values come in million đồng and volumes in thousand shares, as strings with ',' separators. The session's
report is usually published the morning after, so it only cross-checks the price-board figures.
"""

import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_Q2 = Decimal("0.01")


def _num(text) -> Decimal:
    return Decimal(str(text).replace(",", "").strip())


def _rows(raw: str) -> dict[str, dict]:
    data = json.loads(raw)["data"]
    return {r["trading_type_name"]: r for r in data}


def parse_hose(value_json: str, volume_json: str) -> dict:
    try:
        value, volume = _rows(value_json), _rows(volume_json)
        if not value or not volume:
            return {"status": "missing", "reason": "HOSE chưa công bố"}
        bn = lambda x: str((_num(x) / 1000).quantize(_Q2, ROUND_HALF_UP))
        shares = lambda x: int((_num(x) * 1000).to_integral_value(ROUND_HALF_UP))
        return {"status": "ok", "total_value_bn": bn(value["Mua"]["market_value"]), "total_volume": shares(volume["Mua"]["market_volumn"]),
                "foreign": {"buy_value_bn": bn(value["Mua"]["foreign_trading_value"]), "sell_value_bn": bn(value["Bán"]["foreign_trading_value"]),
                            "net_value_bn": bn(value["Mua - Bán"]["foreign_trading_value"]),
                            "buy_volume": shares(volume["Mua"]["foreign_trading_volumn"]),
                            "sell_volume": shares(volume["Bán"]["foreign_trading_volumn"])}}
    except (ValueError, KeyError, TypeError, InvalidOperation):
        return {"status": "missing", "reason": "HOSE đổi định dạng"}
