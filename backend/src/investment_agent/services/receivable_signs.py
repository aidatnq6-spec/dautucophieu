"""Bảng dấu hiệu phải thu on Ngành theo quý: for each watched non-financial ticker, which receivable signs are on, gathered from
Chất lượng báo cáo (the latest fiscal year) and the Phải thu block (the latest quarter). True on, False read and off, None not read.
Readings to look into, not a finding and not advice. Public figures only."""

from pathlib import Path

from investment_agent.domain.balance_watch import raise_prepay, receivables_view
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.valuation.quality import report_quality

# (key, column title), in the order of the board
SIGNS = [("other_receivables", "Phải thu khác lớn"), ("other_high", "Cao hơn ngành"), ("prepay_suppliers", "Trả trước lớn"),
         ("raise_prepay", "Trả trước sau huy động vốn"), ("paper_income", "Thu nhập tài chính chưa thu tiền"),
         ("financial_profit", "Phụ thuộc thu nhập tài chính"), ("receivables_outpace_revenue", "Phải thu tăng nhanh hơn doanh thu"),
         ("provision_jump", "Dự phòng tăng mạnh")]
QUALITY = {"other_receivables", "prepay_suppliers", "paper_income", "financial_profit", "receivables_outpace_revenue"}


def receivable_signs(data_dir: Path) -> list[dict]:
    data_dir = Path(data_dir)
    sectors = load_sectors(data_dir)[0]
    statements, fundamentals = StatementStore(data_dir / "statements"), FundamentalsStore(data_dir / "fundamentals")
    watched = load_watchlist(data_dir).symbols
    quarters = {s: (statements.read(s) or {}).get("quarters", {}) for s in watched if kind_of(sectors.get(s)) is None}
    rows = []
    for symbol, qs in quarters.items():
        record, sector = fundamentals.read(symbol), sectors.get(symbol)
        quality = {s["id"]: s for s in report_quality(record, sector).get("signs", [])}
        signs = {k: quality[k]["flag"] if k in quality else None for k in QUALITY}
        if qs:
            peers = {p: q for p, q in quarters.items() if p != symbol and q and sectors.get(p) == sector}
            view = receivables_view(qs, peers)
            signs["other_high"] = view["other_vs_sector"]["high"]
            signs["provision_jump"] = view["provision"]["kind"] == "jump" if view["provision"]["amount"] is not None else None
            signs["raise_prepay"] = raise_prepay(qs, (record or {}).get("share_issues"))["flag"] if record else None
        else:
            signs.update(other_high=None, provision_jump=None, raise_prepay=None)
        details = {k: quality[k]["detail"] for k in QUALITY if k in quality and quality[k]["flag"]}
        rows.append({"symbol": symbol, "sector": sector, "signs": signs, "count": sum(1 for v in signs.values() if v is True), "details": details})
    order = {s: i for i, s in enumerate(watched)}
    return sorted(rows, key=lambda r: (-r["count"], order[r["symbol"]]))
