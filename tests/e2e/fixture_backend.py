"""Browser-test backend: the real FastAPI app over an in-memory personal store and a
labelled synthetic market (one priced issuer with one document). Synthetic data only."""

import json
import os
import tempfile
from datetime import date, timedelta
from decimal import Decimal

import uvicorn

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.jobs.runner import JobStore
from investment_agent.market.leading import MacroStore
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
    MacroStore(data).upsert("us10y", [(date(2026, 10, 21), "4.91"), (date(2026, 10, 23), "4.96")], entry="auto")
    app = create_app(InternalAuthSettings.from_env(), personal_repository=repository, market=MARKET,
                     jobs=JobStore(os.path.join(data, "jobs.sqlite")), outbox=deliveries, deliveries=deliveries, data_dir=data)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["E2E_PYTHON_PORT"]), workers=1, access_log=False)
