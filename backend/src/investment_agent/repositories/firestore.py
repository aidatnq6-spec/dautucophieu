"""Firestore Admin transaction adapter. No client-side or offline write path."""

import os
from uuid import uuid4

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.exceptions import GoogleAuthError
from google.cloud import firestore

from .personal import PersonalRepository, RepositoryUnavailable


class _FirestoreTransaction:
    def __init__(self, client, transaction):
        self.client, self.transaction = client, transaction

    def read(self, path):
        snapshot = self.client.document(path).get(transaction=self.transaction, retry=None, timeout=10)
        return snapshot.to_dict() if snapshot.exists else None

    def create(self, path, value):
        self.transaction.create(self.client.document(path), value)

    def put(self, path, value):
        self.transaction.set(self.client.document(path), value)


class FirestoreDocumentStore:
    def __init__(self, client):
        self.client = client

    def atomic(self, operation):
        @firestore.transactional
        def execute(transaction):
            return operation(_FirestoreTransaction(self.client, transaction))
        try:
            return execute(self.client.transaction(max_attempts=3))
        except (GoogleAPICallError, RetryError, GoogleAuthError):
            # Exception text/chained trace can contain request payloads or credentials.
            raise RepositoryUnavailable("Personal repository unavailable") from None


def personal_repository_from_env() -> PersonalRepository:
    """Explicit production factory; never substitutes MemoryDocumentStore or ADC."""
    if os.environ.get("FIRESTORE_EMULATOR_HOST") or os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise RepositoryUnavailable("Production repository rejects emulator configuration")
    required = ("FIREBASE_PROJECT_ID", "FIREBASE_CLIENT_EMAIL", "FIREBASE_PRIVATE_KEY", "FIREBASE_OWNER_UID")
    values = {key: os.environ.get(key, "") for key in required}
    if not all(values.values()):
        raise RepositoryUnavailable("Personal repository configuration incomplete")
    # Validate namespace before creating a privileged client.
    from .personal import InvalidRecord
    try:
        PersonalRepository(values["FIREBASE_OWNER_UID"], None)
    except InvalidRecord:
        raise RepositoryUnavailable("Invalid owner configuration") from None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as admin_firestore
        credential = credentials.Certificate({
            "type": "service_account", "project_id": values["FIREBASE_PROJECT_ID"],
            "client_email": values["FIREBASE_CLIENT_EMAIL"],
            "private_key": values["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        app = firebase_admin.initialize_app(credential, {"projectId": values["FIREBASE_PROJECT_ID"]}, name=f"personal-{uuid4().hex}")
        try:
            client = admin_firestore.client(app=app)
        except Exception:
            firebase_admin.delete_app(app)
            raise
        # Caller constructs this once per worker; no HTTP/network call here.
        return PersonalRepository(values["FIREBASE_OWNER_UID"], FirestoreDocumentStore(client))
    except Exception:
        raise RepositoryUnavailable("Personal repository configuration unavailable") from None
