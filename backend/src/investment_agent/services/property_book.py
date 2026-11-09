"""Bức tranh toàn bộ tài sản: the stored property and loan book (`settings/property_book`) with the financial assets from Tháp tài sản, stocks at market
price instead of cost. Only reads Tháp tài sản, never feeds it. Personal data; never sent to a model."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from investment_agent.domain.property_book import PropertyBook, picture
from investment_agent.services.deposit_book import book_quotes
from investment_agent.services.equity_budget import budget_view
from investment_agent.services.overview import compose_overview
from investment_agent.services.records import read_version

RECORD = ("settings", "property_book")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
REASONS = {"no_total": "Chưa có số tài sản tài chính: nhập Sổ tài sản hoặc các lớp của Tháp tài sản.",
           "no_risk": "Tháp tài sản chưa tính được vì chưa có nhóm rủi ro, nên chưa có số tài sản tài chính.",
           "no_layers": "Tháp tài sản đang dùng một con số tổng, chưa tách được phần cổ phiếu: nhập Sổ tài sản hoặc các lớp."}


def _financial(repo, owner, market, data_dir, now: datetime) -> tuple[Decimal | None, str | None, list[str]]:
    """(financial assets, why they are not known, holdings left out for want of a price)."""
    budget, _ = budget_view(repo, owner, quotes=book_quotes(data_dir))
    pyramid = budget.get("pyramid")
    if pyramid is None:
        return None, REASONS["no_layers" if budget["status"] == "ok" else budget["status"]], []
    others = sum((Decimal(l["amount"]) for l in pyramid["layers"] if l["id"] != "stocks"), Decimal(0))
    held = [h for h in compose_overview(repo, owner, market, now)["holdings"] if h["quantity"] + h["pending_quantity"] > 0]
    stocks = sum((Decimal(h["market_value"]) for h in held if h["market_value"] is not None), Decimal(0))
    return others + stocks, None, sorted(h["security_id"] for h in held if h["market_value"] is None)


def property_view(repo, owner, *, market, data_dir, now: datetime) -> dict:
    stored = read_version(repo, owner, *RECORD, None)
    book = PropertyBook.model_validate(stored.payload) if stored else PropertyBook()
    financial, reason, unpriced = _financial(repo, owner, market, data_dir, now)
    return {"version": stored.version if stored else 0, "book": book.model_dump(mode="json"), "financial_reason": reason, "unpriced": unpriced,
            "picture": picture(book, financial=financial, today=now.astimezone(VN).date())}
