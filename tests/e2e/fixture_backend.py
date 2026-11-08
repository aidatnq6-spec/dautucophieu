"""Browser-test backend: the real FastAPI app over an in-memory personal store and a
labelled synthetic market (one priced issuer with one document). Synthetic data only."""

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import uvicorn

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.insights.store import InsightStore
from investment_agent.jobs.runner import JobStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.trend import SnapshotStore
from investment_agent.market.view import EvidenceRef, PricePoint, SyntheticMarket
from investment_agent.notifications.outbox import DeliveryStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

# FPT: 21 weekday closes ending 2026-10-23 at 57,000 (previous 55,000; 20 sessions earlier 50,000), for the watchlist.
_DAYS = [d for d in (date(2026, 10, 23) - timedelta(days=i) for i in range(40)) if d.weekday() < 5][:21][::-1]
FPT_HISTORY = [PricePoint(Decimal(v), d) for v, d in zip([50_000] * 19 + [55_000, 57_000], _DAYS)]
INDEX_HISTORY = [PricePoint(Decimal(v), d) for v, d in zip(["1700"] * 20 + ["1774.15"], _DAYS)]

MARKET = SyntheticMarket(
    prices={"FPT": PricePoint(Decimal(60_000), date(2026, 10, 23))},
    history={"FPT": FPT_HISTORY, "VNINDEX": INDEX_HISTORY},
    documents={"FPT": [EvidenceRef("doc-fpt-1", "BCTC quý III/2026 (tổng hợp)", "financial_statement",
                                   "https://example.invalid/fpt-q3.pdf", "2026-10-20", "FPT")]},
    industries={"FPT": "tech"},
)

def _c(macd, rsi, zone, reason=None, **changed):
    return {"macd": macd, "rsi": rsi, "zone": zone, "reason": reason, "macd_changed": False, "previous_macd": None,
            "rsi_changed": False, "previous_zone": None, **changed}


TREND = {"session_date": "2026-10-23", "generated_at": "2026-10-23T08:35:00+00:00", "board_version": "trend-2026-10-25.1",
         "previous_date": "2026-10-22", "errors": {},
         "groups": [{"id": "macro", "label": "Vĩ mô", "rows": [{"id": "VN10Y", "label": "VN10Y", "note": None,
                     "cells": {f: _c(None, None, None, "Không có nguồn miễn phí hợp lệ") for f in ("M", "W", "D1", "H4", "H1")}}]},
                    {"id": "stocks", "label": "Cổ phiếu", "rows": [{"id": "FPT", "label": "FPT", "note": None, "cells": {
                        "M": _c("up,>0", 63, "neutral"), "W": _c("down,<0", 45, "neutral"),
                        "D1": _c("up,>0", 72, "overbought", macd_changed=True, previous_macd="down,<0", rsi_changed=True, previous_zone="neutral"),
                        "H4": _c("down,<0", 45, "neutral"), "H1": _c(None, None, None, "Chưa có giá của phiên")}}]}]}

if __name__ == "__main__":
    repository = PersonalRepository(os.environ["FIREBASE_OWNER_UID"], MemoryDocumentStore())
    data = tempfile.mkdtemp(prefix="investment-e2e-")  # job leases and outbox for this run only
    deliveries = DeliveryStore(os.path.join(data, "deliveries.sqlite"))
    with open(os.path.join(data, "market-symbols.txt"), "w", encoding="utf-8") as f:
        f.write("FPT\nVCB\n")
    with open(os.path.join(data, "index-groups.json"), "w", encoding="utf-8") as f:
        json.dump({"as_of": "2026-10-25", "source": "synthetic", "groups": {"VN30": ["FPT"], "VN100": ["FPT", "VCB"]}}, f)
    with open(os.path.join(data, "industries.json"), "w", encoding="utf-8") as f:
        json.dump({"as_of": "2026-10-25", "source": "synthetic", "level": 2, "sectors": {"FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}}, f,
                  ensure_ascii=False)
    SnapshotStore(os.path.join(data, "trend")).save(TREND)
    # Reference valuation: FPT with P/E 12 every year and yearly cash dividends; VCB has no statements.
    FundamentalsStore(os.path.join(data, "fundamentals")).save({
        "symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "synthetic",
        "years": {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2020, 2026)},
        "quarters": {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")},
        "dividends": [{"date": f"{y}-07-01", "cash": "500"} for y in range(2021, 2026)] + [{"date": "2026-07-01", "cash": "500"}], "issues": [],
        # Chất lượng báo cáo: better on every line each year (F-Score 9/9), a bonus issue in 2025, a quarter first seen today.
        "annual": {y: {k: str(v * 10**9) for k, v in dict(revenue=r, gross_profit=g, profit=p, total_assets=a, current_assets=ca, current_liabilities=cl,
                                                             long_liabilities=ll, receivables=rc, cfo=c).items()}
                   for y, (r, g, p, a, ca, cl, ll, rc, c) in {"2023": (80, 16, 4, 100, 50, 40, 30, 10, 5), "2024": (90, 19, 6, 100, 55, 40, 28, 11, 8),
                                                              "2025": (110, 25, 9, 105, 60, 38, 25, 12, 12)}.items()},
        "share_issues": [{"date": "2025-06-01", "kind": "bonus"}],
        "latest_quarter_seen": {"quarter": "2026-Q2", "on": date.today().isoformat()}})
    # Bang so tai chinh: VNDirect-style statements for FPT (tỷ đồng × 1e9; costs positive, capex negative).
    from investment_agent.market.statements import StatementStore
    def fs(rev, npat, **more):
        base = {"revenue": rev, "cogs": rev * 0.6, "gross_profit": rev * 0.4, "selling": rev * 0.1, "admin": rev * 0.05, "fin_income": 5,
                "fin_expense": 8, "interest": 6, "associates": 0, "other_profit": 1, "pbt": npat * 1.25, "tax": npat * 0.25, "npat": npat,
                "npat_parent": npat, "depreciation": 20, "cfo": npat * 1.2, "capex": -npat * 0.5, "equity": 1000, "minority_equity": 10,
                "st_debt": 300, "lt_debt": 200, "cash": 100, "st_investments": 50}
        base.update(more)
        return {k: str(int(v * 10**9)) for k, v in base.items()}
    StatementStore(os.path.join(data, "statements")).save({
        "symbol": "FPT", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo",
        # Parent profit 0.25 tỷ a quarter and parent equity 10 tỷ, as the Vnstock figures above, so the weekly series reads the same.
        "quarters": {f"{y}-Q{k}": fs(250 + 20 * (y - 2024) + k, 0.25, equity=10, minority_equity=0) for y in range(2020, 2026) for k in (1, 2, 3, 4)},
        "years": {str(y): fs(1010, 1, equity=10, minority_equity=0, charter_capital=10) for y in range(2020, 2026)}, "quarters_created": {},
        "years_created": {}, "year_end_close": {"2024": {"date": "2024-12-31", "close": "11"}, "2025": {"date": "2025-12-31", "close": "12"}},
        "quarters_conflicts": [], "years_conflicts": []})
    SeriesStore(os.path.join(data, "trend-sources")).upsert("FPT-1d", [(datetime(y, 12, 31), "12") for y in range(2020, 2026)])
    # Quy mo va dinh gia of a bank: VCB's own layout, apart from the general statements; 1 tỷ parent profit a quarter, 100 tỷ equity.
    StatementStore(os.path.join(data, "statements-financial")).save({
        "symbol": "VCB", "kind": "bank", "fetched_at": "2026-11-07T00:00:00+00:00", "source": "vndirect:finfo",
        "quarters": {f"{y}-Q{k}": {"npat_parent": str(10**9), "equity": str(100 * 10**9), "charter_capital": str(10 * 10**9),
                                   "ppop": str(2 * 10**9), "operating_income": str(3 * 10**9)} for y in (2025, 2026) for k in (1, 2, 3, 4)},
        "years": {}, "quarters_conflicts": [], "years_conflicts": [], "year_end_close": {},
        "quarter_end_close": {"2026-Q3": {"date": "2026-09-30", "close": "60"}}})
    # Month-end closes that move around (P/E chart); the 31 December closes above stay 12 for the valuation tests.
    SeriesStore(os.path.join(data, "trend-sources")).upsert("FPT-1d", [(datetime(y, m, 28), str(12 + ((y * 12 + m) % 9) - 4))
                                                                       for y in range(2020, 2026) for m in range(1, 12)])
    # Nhận định: two synthetic verified report records published 5 and 20 days ago, one SSI title.
    def _insight(ref, days, view, sectors):
        return {"source": "acbs", "ref_id": ref, "title": f"Báo cáo mẫu {ref}", "page_url": f"https://example.invalid/{ref}",
                "pdf_url": f"https://example.invalid/{ref}.pdf", "published": (date.today() - timedelta(days=days)).isoformat(),
                "status": "ok", "telegram_sent": True, "model": "synthetic", "cost_usd": "0",
                "insight": {"macro_now": {"view": view, "reasons": [{"text": f"Tăng trưởng GDP vững ({ref})", "quote": "GDP tăng 7,5%", "page": 1}]},
                            "macro_outlook": {"view": "neutral", "reasons": [{"text": "Lãi suất neo cao", "quote": "lãi suất cao", "page": 2}]},
                            "sectors": [{"sector": s, "effect": e, "reason": f"Lý do {s}", "quote": "q", "page": 3} for s, e in sectors], "dropped": 0}}
    insights = InsightStore(os.path.join(data, "insights"))
    insights.save(_insight("mau-1", 5, "favourable", [("Công nghệ Thông tin", "benefit"), ("Ngân hàng", "harm")]))
    insights.save(_insight("mau-2", 20, "favourable", [("Ngân hàng", "benefit")]))
    with open(os.path.join(data, "insights", "status.json"), "w", encoding="utf-8") as f:
        json.dump({"at": datetime.now().astimezone().isoformat(), "status": "ok", "processed": [], "errors": {"acbs:loi-mau": "download_failed"}}, f)
    with open(os.path.join(data, "insights", "ssi.json"), "w", encoding="utf-8") as f:
        json.dump({"at": "synthetic", "titles": [{"title": "Cập nhật Ngành Thép mẫu", "kind": "ngành", "date": "2026-10-20",
                                                  "url": "https://example.invalid/ssi-thep"}]}, f, ensure_ascii=False)
    # After-close brief: synthetic public market snapshot for session 2026-10-23 (no network in tests).
    os.makedirs(os.path.join(data, "brief"), exist_ok=True)
    with open(os.path.join(data, "brief", "2026-10-23.json"), "w", encoding="utf-8") as f:
        json.dump({"session_date": "2026-10-23", "updated_at": "2026-10-23T15:40:00+07:00",
                   "indices": {"status": "ok", "rows": [{"id": "VNINDEX", "status": "ok", "close": "1658.52", "change": "12.30", "pct": "0.0075"},
                                                        {"id": "VN30", "status": "missing", "reason": "Chưa có giá chỉ số phiên này"}]},
                   "board": {"status": "ok", "trading_date": "2026-10-23", "value_matched_bn": "17010.24", "volume_matched": 605225925,
                             "breadth": {"up": 180, "down": 150, "flat": 50, "no_trade": 27},
                             "foreign": {"buy_volume": 70754422, "sell_volume": 90395166, "buy_value_bn": "1896.84", "sell_value_bn": "2374.56",
                                         "net_value_bn": "-477.72", "top_sell": [{"symbol": "VHM", "net_value_bn": "-210.50"}],
                                         "top_buy": [{"symbol": "FPT", "net_value_bn": "45.00"}]},
                             "sectors": [{"sector": "Công nghệ Thông tin", "pct": "0.0120", "count": 9}, {"sector": "Ngân hàng", "pct": "-0.0040", "count": 27}],
                             "symbols": {"FPT": {"price": 57000, "ref": 55000, "change": 2000, "pct": "0.0364", "sector": "Công nghệ Thông tin"},
                                         "VCB": {"price": 61000, "ref": 61000, "change": 0, "pct": "0.0000", "sector": "Ngân hàng"}}},
                   "hose": {"status": "missing", "reason": "HOSE chưa công bố"},
                   "proprietary": {"status": "missing", "reason": "Chưa có nguồn miễn phí"},
                   "news": {"status": "ok", "items": [{"title": "FPT ký hợp đồng AI lớn", "url": "https://example.invalid/fpt-news", "source": "CafeF",
                                                       "published": "2026-10-23T10:00:00+07:00"}]}}, f, ensure_ascii=False)
    # Hiệu quả danh mục: weekday closes from the synthetic buy (02/02/2026) to 30/04/2026 for FPT (thousand đồng) and VN-Index.
    perf_days = [date(2026, 2, 2) + timedelta(days=i) for i in range(88) if (date(2026, 2, 2) + timedelta(days=i)).weekday() < 5]
    SeriesStore(os.path.join(data, "trend-sources")).upsert("FPT-1d", [(datetime.combine(d, datetime.min.time()), str(50 + i * 0.2))
                                                                       for i, d in enumerate(perf_days)])
    SeriesStore(os.path.join(data, "trend-sources")).upsert("VNINDEX-1d", [(datetime.combine(d, datetime.min.time()), str(1200 + i))
                                                                           for i, d in enumerate(perf_days)])
    # Lịch sự kiện: synthetic corporate events relative to today (FPT dividend in 3 days, VCB meeting in 10, FPT insider deal 2 days ago).
    from investment_agent.market.corporate_events import EventStore
    def _ev(i, sym, kind, days, title):
        d = (date.today() + timedelta(days=days)).isoformat()
        return {"id": f"{sym}-{i}", "symbol": sym, "code": "X", "kind": kind, "title": title, "key_date": d, "exright": d,
                "record": d, "payout": None, "ratio": None, "value_per_share": 2000.0 if kind == "dividend_cash" else None}
    EventStore(data).save("FPT", [_ev(1, "FPT", "dividend_cash", 3, "Trả cổ tức bằng tiền mặt - Đợt 1/2026 - 2,000 VND"),
                                  _ev(2, "FPT", "insider", -2, "Nguyễn Văn A - Đăng kí Mua 10,000 FPT"),
                                  _ev(3, "FPT", "dividend_cash", -30, "Trả cổ tức bằng tiền mặt - Đợt 2/2026 - 2,000 VND")],  # past: drafted into the ledger
                    fetched_at="2026-10-26T15:40:00+07:00")
    EventStore(data).save("VCB", [_ev(1, "VCB", "meeting", 10, "VCB - Tổ chức ĐHĐCĐ bất thường 2026")], fetched_at="2026-10-26T15:40:00+07:00")
    MacroStore(data).upsert("us10y", [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")], entry="auto")
    # CAPM hint and the people block: a stored bond yield and beta, and cached shareholders so the page never calls Vnstock.
    MacroStore(data).upsert("vn10y", [(date.today() - timedelta(days=1), "4.49")], entry="auto")
    from investment_agent.market.beta import BetaStore
    from investment_agent.market.company_people import PeopleStore
    BetaStore(data).save({"values": {"FPT": {"beta": "0.73", "date": (date.today() - timedelta(days=1)).isoformat()}}})
    for sym, holder in (("FPT", "Trương Gia Bình"), ("VCB", "Ngân hàng Nhà nước Việt Nam")):
        PeopleStore(data).save(sym, {"schema": 2, "symbol": sym, "fetched_at": datetime.now(timezone.utc).isoformat(), "source": "synthetic",
                                     "ownership": {"foreign": "0.2222", "foreign_max": "0.49", "state": "0", "free_float": None},
                                     "structure": [{"type": "Tổ chức nước ngoài", "percent": "0.2854", "shares": 1466163575, "updated": "2025-12-31"}],
                                     "shareholders": [{"name": holder, "type": "Individual" if sym == "FPT" else "Organization", "quantity": 117347966,
                                                       "percent": 0.0689, "updated": "2026-08-03"}],
                                     "officers": [{"name": "Bùi Quang Ngọc", "position": "Phó Chủ tịch Hội đồng Quản trị", "percent": 0.0148,
                                                   "quantity": 25255715},
                                                  {"name": "Trương Gia Bình", "position": "Chủ tịch Hội đồng Quản trị", "percent": 0.0689,
                                                   "quantity": 117347966}]})
    from investment_agent.market.erp import ErpStore
    ErpStore(data).save({"erp": "0.0813", "erp_cds": "0.0632", "rating": "Ba2", "published": "2026-02-16", "fetched_at": datetime.now(timezone.utc).isoformat()})
    from investment_agent.market.insider_deals import InsiderStore
    InsiderStore(data).save("FPT", {"symbol": "FPT", "fetched_at": datetime.now(timezone.utc).isoformat(), "source": "synthetic", "deals": [
        {"date": (date.today() - timedelta(days=30)).isoformat(), "kind": "Bán", "shares": 2000000, "source": "HOSE",
         "title": "Báo cáo kết quả giao dịch cổ phiếu của Người nội bộ Bùi Quang Ngọc", "url": "https://dstock.vndirect.com.vn/tin-tuc/tin-tu-so/1"},
        {"date": (date.today() - timedelta(days=45)).isoformat(), "kind": "Đăng kí bán", "shares": 2000000, "source": "HOSE",
         "title": "Thông báo giao dịch cổ phiếu của Người nội bộ Bùi Quang Ngọc", "url": None},
        {"date": (date.today() - timedelta(days=60)).isoformat(), "kind": None, "shares": None, "source": "HOSE",
         "title": "Báo cáo kết quả giao dịch cổ phiếu ESOP của người nội bộ", "url": None}]})
    # Bank health score: VCB sector ratios, Q3/2026 against Q3/2025, better on all seven (7/7, mạnh).
    from investment_agent.market.financial_ratios import FinancialRatioStore
    FinancialRatioStore(os.path.join(data, "financial-ratios")).save({"symbol": "VCB", "kind": "bank", "fetched_at": "2026-10-31T00:00:00+00:00",
        "source": "synthetic", "quarters": {"2025-09-30": {"BAD_LOANS_RATIO_AQ": "0.0103", "ROAA_TR_AVG4Q": "0.0154", "OVERDUE_LOANS_RATIO_AQ": "0.0131",
                                                           "PROVISION_BAD_LOANS_AQ": "2.02", "NET_INTEREST_MARGIN_TR_AVG5Q": "0.0223", "EQUITY_TO_ASSET_AQ": "0.094"},
                                            "2026-09-30": {"BAD_LOANS_RATIO_AQ": "0.0071", "ROAA_TR_AVG4Q": "0.0166", "OVERDUE_LOANS_RATIO_AQ": "0.0098",
                                                           "PROVISION_BAD_LOANS_AQ": "2.43", "NET_INTEREST_MARGIN_TR_AVG5Q": "0.024", "EQUITY_TO_ASSET_AQ": "0.095"}}})
    # Định giá chỉ số: VN30 at P/E 15 and P/B 2 for six years, today P/E 12 at 1,800 points (fair 2,025, −11,1%); VNINDEX has no multiples.
    ix_days = [datetime.combine(date.today() - timedelta(days=i), datetime.min.time()) for i in range(6 * 365, 0, -1)
               if (date.today() - timedelta(days=i)).weekday() < 5]
    SeriesStore(os.path.join(data, "index-valuation")).upsert("VN30-pe-1d", [(d, "15") for d in ix_days[:-1]] + [(ix_days[-1], "12")])
    SeriesStore(os.path.join(data, "index-valuation")).upsert("VN30-pb-1d", [(d, "2") for d in ix_days])
    SeriesStore(os.path.join(data, "trend-sources")).upsert("VN30-1d", [(ix_days[-1], "1800")])
    # Chuỗi giá trị: oil up 10% over a month (bad for plastic pipe, good for drilling and gas) and world rubber up (good for rubber).
    MacroStore(data).upsert("wti", [(date.today() - timedelta(days=35), "60"), (date.today() - timedelta(days=1), "66")], entry="auto")
    MacroStore(data).upsert("com_rubber", [(date.today() - timedelta(days=60), "120"), (date.today() - timedelta(days=30), "130")], entry="auto")
    # Bảng giá và biểu đồ: a fixed board (FPT up to its ceiling, VNINDEX down) and 60 daily candles; no network.
    from investment_agent.api.routes import trend as trend_routes

    class FixtureSource:
        def board(self, symbols):
            return [{"symbol": "FPT", "trading_date": date.today().isoformat(), "ref_price": 52700, "match_price": 56300, "ceiling": 56300,
                     "floor": 49100, "highest": 56300, "lowest": 52600, "accumulated_volume": 5661600}]

        def index_minutes(self, index):
            vn = timezone(timedelta(hours=7))
            return [(datetime(2026, 10, 29, 14, 45, tzinfo=vn), "1755.61"), (datetime(2026, 10, 30, 14, 45, tzinfo=vn), "1741.62")] if index == "VNINDEX" else []

        def get(self, url):  # Coinbase stats: Bitcoin down 1% over 24 hours; gold left to its stored close
            if "BTC-USD" in url:
                return '{"open": "78000", "last": "77220"}'
            raise RuntimeError("offline")

        def ohlcv(self, symbol, interval, start, end, index):
            if symbol == "MWG":  # Đáy nhịp tuần: four years of a rising saw-tooth (12 weeks up, 4 down), only this row asks for it
                first, price, out = date.today() - timedelta(weeks=208), 50.0, []
                for w in range(208):
                    price += 0.75 * (1 + w // 16 * 0.3) if w % 16 < 12 else -1.5  # steeper each cycle
                    for d in range(5):
                        t = datetime.combine(first + timedelta(weeks=w, days=d), datetime.min.time(), tzinfo=timezone(timedelta(hours=7)))
                        out.append({"time": t, "open": f"{price:.2f}", "high": f"{price + 1:.2f}", "low": f"{price - 1:.2f}", "close": f"{price:.2f}", "volume": 1000})
                return out
            first = datetime.combine(date.today() - timedelta(days=59), datetime.min.time(), tzinfo=timezone(timedelta(hours=7)))  # ends today
            return [{"time": first + timedelta(days=i), "open": "50", "high": "55", "low": "49", "close": str(50 + i % 4), "volume": 1000 + i}
                    for i in range(60)]
    trend_routes._source = FixtureSource
    # Số liệu vận hành: a synthetic public bulletin behind one example link; any other link is refused as the real check would do.
    from investment_agent.api.routes import operating as operating_routes
    from investment_agent.domain.bank_figures import UnsafeUrl
    BULLETIN = "https://example.invalid/ban-tin-10-2026.pdf"
    operating_routes._read_pdf = lambda url: ["BẢN TIN SẢN XUẤT KINH DOANH THÁNG 10/2026",
                                              "Sản lượng bán hàng thép xây dựng đạt 412.300 tấn, tăng 18% so với cùng kỳ" + chr(10) + "Thép HRC: 512.000 tấn"]
    def _only_bulletin(url):
        if url != BULLETIN:
            raise UnsafeUrl("Chỉ nhận đường dẫn https tới địa chỉ công khai.")
    operating_routes.check_public_https = _only_bulletin
    # Kênh tuần: four years of US10Y closes in a rising saw-tooth that steepens each cycle (only the trend board reads this series).
    us_days, us_level, us_points = date.today() - timedelta(weeks=208), 2.0, []
    for w in range(208):
        us_level += 0.015 * (1 + w // 16 * 0.3) if w % 16 < 12 else -0.03
        us_points += [(datetime.combine(us_days + timedelta(weeks=w, days=d), datetime.min.time()), f"{us_level:.3f}") for d in range(5)]
    SeriesStore(os.path.join(data, "trend-sources")).upsert("US10Y-1d", us_points)
    SeriesStore(os.path.join(data, "trend-sources")).upsert("DXY-ecb-1d", [(datetime(2026, 8, 1) + timedelta(days=i), str(99 + (i % 3) / 10))
                                                                       for i in range(60)])
    app = create_app(InternalAuthSettings.from_env(), personal_repository=repository, market=MARKET,
                     jobs=JobStore(os.path.join(data, "jobs.sqlite")), outbox=deliveries, deliveries=deliveries, data_dir=data)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["E2E_PYTHON_PORT"]), workers=1, access_log=False)
