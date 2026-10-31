"""Browser-test backend: the real FastAPI app over an in-memory personal store and a
labelled synthetic market (one priced issuer with one document). Synthetic data only."""

import json
import os
import tempfile
from datetime import date, datetime, timedelta
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
    SeriesStore(os.path.join(data, "trend-sources")).upsert("FPT-1d", [(datetime(y, 12, 31), "12") for y in range(2020, 2026)])
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
                                  _ev(2, "FPT", "insider", -2, "Nguyễn Văn A - Đăng kí Mua 10,000 FPT")], fetched_at="2026-10-26T15:40:00+07:00")
    EventStore(data).save("VCB", [_ev(1, "VCB", "meeting", 10, "VCB - Tổ chức ĐHĐCĐ bất thường 2026")], fetched_at="2026-10-26T15:40:00+07:00")
    MacroStore(data).upsert("us10y", [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")], entry="auto")
    # Định giá chỉ số: VN30 at P/E 15 and P/B 2 for six years, today P/E 12 at 1,800 points (fair 2,025, −11,1%); VNINDEX has no multiples.
    ix_days = [datetime.combine(date.today() - timedelta(days=i), datetime.min.time()) for i in range(6 * 365, 0, -1)
               if (date.today() - timedelta(days=i)).weekday() < 5]
    SeriesStore(os.path.join(data, "index-valuation")).upsert("VN30-pe-1d", [(d, "15") for d in ix_days[:-1]] + [(ix_days[-1], "12")])
    SeriesStore(os.path.join(data, "index-valuation")).upsert("VN30-pb-1d", [(d, "2") for d in ix_days])
    SeriesStore(os.path.join(data, "trend-sources")).upsert("VN30-1d", [(ix_days[-1], "1800")])
    # Chuỗi giá trị: oil up 10% over a month (bad for plastic pipe, good for drilling and gas) and world rubber up (good for rubber).
    MacroStore(data).upsert("wti", [(date.today() - timedelta(days=35), "60"), (date.today() - timedelta(days=1), "66")], entry="auto")
    MacroStore(data).upsert("com_rubber", [(date.today() - timedelta(days=60), "120"), (date.today() - timedelta(days=30), "130")], entry="auto")
    app = create_app(InternalAuthSettings.from_env(), personal_repository=repository, market=MARKET,
                     jobs=JobStore(os.path.join(data, "jobs.sqlite")), outbox=deliveries, deliveries=deliveries, data_dir=data)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["E2E_PYTHON_PORT"]), workers=1, access_log=False)
