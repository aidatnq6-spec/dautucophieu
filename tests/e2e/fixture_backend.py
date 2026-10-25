"""Browser-test backend: the real FastAPI app over an in-memory personal store (synthetic data only)."""

import os

import uvicorn

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

if __name__ == "__main__":
    repository = PersonalRepository(os.environ["FIREBASE_OWNER_UID"], MemoryDocumentStore())
    app = create_app(InternalAuthSettings.from_env(), personal_repository=repository)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["E2E_PYTHON_PORT"]), workers=1, access_log=False)
