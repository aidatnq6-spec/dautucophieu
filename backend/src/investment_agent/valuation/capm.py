"""CAPM hint for the required return: cost of equity Ke = Rf + β × ERP, with Rf (the 10-year Vietnamese government bond
yield) and ERP (the owner's equity risk premium) in percent and β as a plain number. A hint shown next to the owner's
required return, never applied to it. A missing input gives a reason instead of a number.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def _d(v) -> Decimal | None:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d.is_finite() else None


def capm(*, rf, beta, erp) -> dict:
    """Ke as a decimal ratio string (0.1018 for 10,18%)."""
    for value, reason in ((rf, "Chưa có lợi suất trái phiếu 10 năm"), (beta, "Chưa có beta của mã"),
                          (erp, "Chưa nhập phần bù rủi ro (ERP) trong Cài đặt")):
        if _d(value) is None:
            return {"ke": None, "reason": reason}
    ke = (_d(rf) + _d(beta) * _d(erp)) / 100
    return {"ke": str(ke.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "reason": None}
