"""Browser-test backend: the real FastAPI app over an in-memory personal store and a
labelled synthetic market (one priced issuer with one document). Synthetic data only."""

import os
import tempfile
from datetime import date
from decimal import Decimal

import uvicorn

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.jobs.runner import JobStore
from investment_agent.market.view import EvidenceRef, PricePoint, SyntheticMarket
from investment_agent.notifications.outbox import DeliveryStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

MARKET = SyntheticMarket(
    prices={"FPT": PricePoint(Decimal(60_000), date(2026, 10, 23))},
    documents={"FPT": [EvidenceRef("doc-fpt-1", "BCTC quý III/2026 (tổng hợp)", "financial_statement",
                                   "https://example.invalid/fpt-q3.pdf", "2026-10-20", "FPT")]},
    industries={"FPT": "tech"},
)

if __name__ == "__main__":
    repository = PersonalRepository(os.environ["FIREBASE_OWNER_UID"], MemoryDocumentStore())
    data = tempfile.mkdtemp(prefix="investment-e2e-")  # job leases and outbox for this run only
    deliveries = DeliveryStore(os.path.join(data, "deliveries.sqlite"))
    app = create_app(InternalAuthSettings.from_env(), personal_repository=repository, market=MARKET,
                     jobs=JobStore(os.path.join(data, "jobs.sqlite")), outbox=deliveries, deliveries=deliveries)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["E2E_PYTHON_PORT"]), workers=1, access_log=False)
