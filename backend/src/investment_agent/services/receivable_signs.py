"""Bảng dấu hiệu phải thu on Ngành theo quý: for each watched non-financial ticker, which receivable signs are on, gathered from
Chất lượng báo cáo (the latest fiscal year) and the Phải thu block (the latest quarter). True on, False read and off, None not read.
Readings to look into, not a finding and not advice. Public figures only."""

from pathlib import Path

from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.balance_watch import cover_thinning, gross_loss, inventory_pace, price_check, year_end_provision, lending_view, raise_prepay, receivables_view
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.statements import StatementStore
from investment_agent.market.value_chains import inventory_price_series
from investment_agent.market.watchlist import load_watchlist
from investment_agent.valuation.quality import report_quality

# (key, column title), in the order of the board
SIGNS = [("other_receivables", "Phải thu khác lớn"), ("other_high", "Cao hơn ngành"), ("prepay_suppliers", "Trả trước lớn"),
         ("raise_prepay", "Trả trước sau huy động vốn"), ("paper_income", "Thu nhập tài chính chưa thu tiền"),
         ("financial_profit", "Phụ thuộc thu nhập tài chính"), ("receivables_outpace_revenue", "Phải thu tăng nhanh hơn doanh thu"),
         ("provision_jump", "Dự phòng tăng mạnh"), ("lending", "Cho vay lớn so với vốn chủ"),
         ("inventory_fast", "Tồn kho tăng nhanh hơn giá vốn"), ("gross_loss", "Bán dưới giá vốn, dự phòng không tăng"),
         ("cover_thinning", "Dự phòng mỏng dần, hàng tồn lâu hơn"), ("audit_gap", "Dự phòng tồn kho quý 4 khác số năm cập nhật sau"),
         ("price_drop", "Giá bán giảm, dự phòng không tăng")]
# A bank's row holds only these (Chất lượng tài sản ngân hàng, owner 23/11/2026), from VNDirect's bank lines and Vietcap's groups 1–5.
BANK_SIGNS = [("provision_cut", "Lợi nhuận đỡ bởi giảm trích lập"), ("accrued_outpace", "Lãi dự thu tăng nhanh hơn thu nhập lãi")]
SIGNS += BANK_SIGNS
QUALITY = {"other_receivables", "prepay_suppliers", "paper_income", "financial_profit", "receivables_outpace_revenue"}
BANK = "Ngân hàng"


def _pct(v) -> str:
    return f"{abs(round(float(v) * 100))}%"


BILLION = Decimal(1_000_000_000)


def _pct1(v) -> str:
    """A ratio as a percentage with one decimal, half up: "2,0%"."""
    return f"{(Decimal(str(v)) * 100).quantize(Decimal('0.1'), ROUND_HALF_UP)}%".replace(".", ",")


def _num(v) -> str:
    """A price as the series gives it, with Vietnamese grouping: 3.340 or 412,5."""
    whole, _, frac = format(Decimal(str(v)).normalize(), "f").partition(".")
    return f"{int(whole):,}".replace(",", ".") + (f",{frac}" if frac else "")


def _moved(v) -> str:
    """"tăng 5%" or "giảm 20%": the word follows the figure's sign (review 23/11/2026: a fall was written as a rise)."""
    return f"{'giảm' if float(v) < 0 else 'tăng'} {_pct(v)}"


def _ty(v) -> str:
    """Tỷ đồng with one decimal, half up, as printed in Vietnamese (1.234,5): 450 million is "0,5", never "0" (review 23/11/2026 (2))."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(str(v))
    rounded = abs(d).quantize(Decimal("0.1"), ROUND_HALF_UP)
    whole, frac = f"{rounded:f}".split(".")
    # the sign of -0,45 kept (int("-0") dropped it; review 23/11/2026 (3)); none on a value that rounds to zero, as formatDecimal on the web
    return ("-" if d < 0 and rounded else "") + f"{int(whole):,}".replace(",", ".") + f",{frac}"


def _bank_row(data_dir: Path, symbol: str, sector: str) -> dict:
    """The bank signs of one watched bank; public figures only, like the rest of this board (the owner's entries stay on the bank's page).
    A store that cannot be read, or of the wrong shape, leaves this bank unread, never the board; the shape is checked where the stores are
    read (bank_notes.load_public), so a fault in the figures' own code still shows (review 23/11/2026 (3))."""
    from investment_agent.domain.bank_figures import accrued_view, provision_view
    from investment_agent.market.bank_notes import load_public
    loaded = load_public(data_dir, symbol)
    if loaded is None:
        return {"symbol": symbol, "sector": sector, "signs": {k: None for k, _ in BANK_SIGNS}, "count": 0, "details": {}}
    public, statements = loaded
    table = {q: v["values"] for q, v in public.items()}
    p, a = provision_view(statements, table), accrued_view(statements, table)
    signs, details = {"provision_cut": p["flag"], "accrued_outpace": a["flag"]}, {}
    if a["flag"]:
        q = a["quarter"]
        details["accrued_outpace"] = (f"Lãi, phí phải thu quý {q[-1]}/{q[:4]} {_moved(a['accrued_growth_yoy'])} so cùng kỳ, thu nhập lãi "
                                      f"{_moved(a['income_growth_yoy'])}; lãi dự thu bằng {_pct(a['ratio'])} thu nhập lãi của quý (cùng kỳ {_pct(a['ratio_year_ago'])}).")
    if p["flag"]:
        q = p["quarter"]
        # the flag needs the expense down 30% and groups 3–5 up; with none the quarter before there is no growth to state, only the amounts
        bad = (f"tăng {_pct(p['bad_growth_qoq'])} so quý trước" if p["bad_growth_qoq"] is not None
               else f"tăng từ {_ty(p['bad_prev'])} lên {_ty(p['bad_now'])} tỷ so quý trước")
        details["provision_cut"] = (f"Chi phí dự phòng quý {q[-1]}/{q[:4]} giảm {_pct(p['expense_growth_yoy'])} so cùng kỳ trong khi nợ nhóm 3–5 {bad}"
                                    + (f"; chi phí dự phòng bằng {_pct(p['share'])} lợi nhuận trước dự phòng." if p["share"] else "."))
    return {"symbol": symbol, "sector": sector, "signs": signs, "count": sum(1 for v in signs.values() if v is True), "details": details}


def receivable_signs(data_dir: Path) -> list[dict]:
    data_dir = Path(data_dir)
    sectors = load_sectors(data_dir)[0]
    statements, fundamentals = StatementStore(data_dir / "statements"), FundamentalsStore(data_dir / "fundamentals")
    watched = load_watchlist(data_dir).symbols
    kept = {s: statements.read(s) or {} for s in watched if kind_of(sectors.get(s)) is None}
    quarters = {s: rec.get("quarters", {}) for s, rec in kept.items()}
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
            lend = lending_view(qs)  # loans and other receivables against equity (owner, 22/11/2026)
            signs["lending"] = None if lend["share"] is None else lend["flag"] is not None
            pace = inventory_pace(qs, peers, property=sector == "Bất động sản")  # Tồn kho tăng nhanh hơn sức bán (owner, 22/11/2026)
            signs["inventory_fast"] = pace["flag"]
            loss = gross_loss(qs, property=sector == "Bất động sản")  # Bán dưới giá vốn nhưng dự phòng không tăng (owner, 23/11/2026)
            signs["gross_loss"] = loss["flag"]
            thin = cover_thinning(qs, property=sector == "Bất động sản")  # Dự phòng mỏng dần (owner, 23/11/2026)
            signs["cover_thinning"] = thin["flag"]
            # Dự phòng chốt khi kiểm toán (owner, 23/11/2026): Q4 as first reported against the audited year; not for a property developer
            audit = year_end_provision(qs, kept[symbol].get("years", {}), years_modified=kept[symbol].get("years_modified"),
                                       quarters_created=kept[symbol].get("quarters_created"))
            signs["audit_gap"] = False if sector == "Bất động sản" else audit["flag"]
            # Giá đầu ra giảm nhưng dự phòng không đổi (owner, 23/11/2026): only where the value chain ties a goods price to the ticker
            found = inventory_price_series(data_dir, symbol)
            price = None
            if found is not None:
                price = price_check(qs, found[2], indicator=found[0], label=found[1], property=sector == "Bất động sản")
                signs["price_drop"] = price["flag"]
        else:
            signs.update(other_high=None, provision_jump=None, raise_prepay=None, lending=None, inventory_fast=None, gross_loss=None,
                         cover_thinning=None, audit_gap=None)
            lend = pace = loss = thin = audit = price = None
        details = {k: quality[k]["detail"] for k in QUALITY if k in quality and quality[k]["flag"]}
        if signs["inventory_fast"]:
            pct = lambda v: f"{round(float(v) * 100)}%"  # noqa: E731
            details["inventory_fast"] = (f"Tồn kho tăng {pct(pace['inventory_growth'])} so cùng kỳ, giá vốn bốn quý tăng {pct(pace['cogs_growth'])}; "
                                         f"tồn kho đủ {pace['days']} ngày (cùng kỳ {pace['year_ago']} ngày).")
        if signs["gross_loss"]:
            q = loss["quarter"]
            details["gross_loss"] = (f"Lỗ gộp {_ty(-Decimal(loss['gross_profit']) / BILLION)} tỷ trong quý {q[-1]}/{q[:4]}; tỷ lệ trích lập dự phòng tồn kho "
                                     f"{_pct1(loss['coverage'])} (quý trước {_pct1(loss['coverage_prev'])}).")
        if signs["cover_thinning"]:
            q = thin["quarter"]
            details["cover_thinning"] = (f"Tồn kho đủ {thin['days']} ngày giá vốn (cùng kỳ {thin['days_year_ago']} ngày) trong khi tỷ lệ trích lập dự phòng "
                                         f"còn {_pct1(thin['coverage'])} (cùng kỳ {_pct1(thin['coverage_year_ago'])}), quý {q[-1]}/{q[:4]}.")
        if signs.get("price_drop"):
            q = price["quarter"]
            details["price_drop"] = (f"{price['label']} cuối quý {q[-1]}/{q[:4]} {_moved(price['change'])} so cùng kỳ "
                                     f"({_num(price['price_year_ago'])} → {_num(price['price'])}) trong khi tỷ lệ trích lập dự phòng tồn kho "
                                     f"{_pct1(price['coverage'])} (cùng kỳ {_pct1(price['coverage_year_ago'])}).")
        if signs["audit_gap"]:
            r = next(r for r in audit["rows"] if r["year"] == audit["year"])
            q4, yb = Decimal(r["q4_balance"]) / BILLION, Decimal(r["year_balance"]) / BILLION
            on = r["updated_on"]
            details["audit_gap"] = (f"Năm {r['year']}: dự phòng giảm giá tồn kho cuối quý 4 tự lập {_ty(q4)} tỷ; số năm VNDirect cập nhật ngày "
                                    f"{on[8:10]}/{on[5:7]}/{on[:4]} là {_ty(yb)} tỷ ({'thêm' if yb > q4 else 'bớt'} {_ty(abs(yb - q4))} tỷ). "
                                    "Đối chiếu báo cáo năm đã kiểm toán."
                                    + (" Số năm gấp nhiều lần các quý quanh đó: có thể là lỗi dữ liệu nguồn, đối chiếu báo cáo gốc." if r["spike"] else ""))
        if signs["lending"]:
            q = lend["quarter"]
            details["lending"] = (f"Cho vay và phải thu khác bằng {round(float(lend['share']) * 100)}% vốn chủ (quý {q[-1]}/{q[:4]}); "
                                  "xem Sổ phải thu bên liên quan trên hồ sơ mã.")
        rows.append({"symbol": symbol, "sector": sector, "signs": signs, "count": sum(1 for v in signs.values() if v is True), "details": details})
    rows += [_bank_row(data_dir, s, BANK) for s in watched if sectors.get(s) == BANK]
    order = {s: i for i, s in enumerate(watched)}
    return sorted(rows, key=lambda r: (-r["count"], order[r["symbol"]]))
