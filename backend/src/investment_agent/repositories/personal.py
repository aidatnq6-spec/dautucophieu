"""Owner-authorized, immutable personal revisions with transactional CAS."""

from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import re
from threading import RLock
from typing import Any, Callable, Protocol, TypeVar

from investment_agent.api.auth import OwnerContext

COLLECTIONS = frozenset({"profile_versions", "risk_versions", "ledger_events", "approvals", "valuation_assumptions", "reports", "settings", "journal"})
T = TypeVar("T")


class OwnerDenied(Exception):
    pass


class InvalidRecord(ValueError):
    pass


class VersionConflict(Exception):
    pass


class IdempotencyConflict(Exception):
    pass


class RepositoryUnavailable(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_payload(value: Any, depth=0):
    if depth > 32:
        raise InvalidRecord("Payload too deeply nested")
    if type(value) is dict:
        for key, child in value.items():
            if not isinstance(key, str):
                raise InvalidRecord("Payload keys must be strings")
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in {"apikey", "privatekey", "clientsecret", "bottoken", "telegrambottoken", "openrouterapikey", "internalapitoken", "internalapihmacsecret", "hmacsecret", "authorization", "password", "credentials", "credential", "serviceaccount", "secret"}:
                raise InvalidRecord("Secrets cannot be persisted in personal records")
            validate_payload(child, depth + 1)
    elif type(value) is list:
        for child in value:
            validate_payload(child, depth + 1)
    elif value is not None and type(value) not in {str, int, bool}:
        raise InvalidRecord("Use JSON strings for decimal values, not floats")


@dataclass(frozen=True)
class PersonalRecord:
    owner_uid: str
    collection: str
    record_id: str
    version: int
    payload: dict[str, Any]
    created_at: str
    request_id: str


class DocumentTransaction(Protocol):
    def read(self, path: str) -> dict | None: ...
    def create(self, path: str, value: dict) -> None: ...
    def put(self, path: str, value: dict) -> None: ...


class DocumentStore(Protocol):
    def atomic(self, operation: Callable[[DocumentTransaction], T]) -> T: ...
    def dump(self, prefix: str) -> dict[str, dict]: ...


class _MemoryTransaction:
    def __init__(self, documents):
        self.documents = documents

    def read(self, path):
        return deepcopy(self.documents.get(path))

    def create(self, path, value):
        if path in self.documents:
            raise VersionConflict("Revision already exists")
        self.put(path, value)

    def put(self, path, value):
        self.documents[path] = deepcopy(value)


class MemoryDocumentStore:
    """Deterministic test adapter only; never selected by runtime configuration."""

    def __init__(self):
        self.documents = {}
        self.available = True
        self.fail_commit = False
        self._lock = RLock()

    def atomic(self, operation):
        with self._lock:
            if not self.available:
                raise RepositoryUnavailable("Personal repository unavailable")
            working = deepcopy(self.documents)
            result = operation(_MemoryTransaction(working))
            if self.fail_commit:
                raise RepositoryUnavailable("Personal repository unavailable")
            self.documents = working
            return deepcopy(result)

    def dump(self, prefix):
        with self._lock:
            if not self.available:
                raise RepositoryUnavailable("Personal repository unavailable")
            return {p: deepcopy(d) for p, d in self.documents.items() if p.startswith(prefix)}


class PersonalRepository:
    def __init__(self, owner_uid: str, store: DocumentStore, *, clock=utc_now):
        if not owner_uid or len(owner_uid) > 128 or "/" in owner_uid or any(ord(c) < 32 for c in owner_uid):
            raise InvalidRecord("Invalid configured owner")
        self.owner_uid, self.store, self.clock = owner_uid, store, clock

    def authorize(self, context: OwnerContext):
        if not isinstance(context, OwnerContext) or context.uid != self.owner_uid or context.role != "owner":
            raise OwnerDenied("Owner access required")

    def key(self, collection, record_id):
        if collection not in COLLECTIONS or not isinstance(record_id, str) or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}", record_id):
            raise InvalidRecord("Invalid record namespace or identifier")
        return digest([collection, record_id])

    def _record(self, tx, collection, record_id, version):
        path = f"owners/{self.owner_uid}/{collection}/{self.key(collection, record_id)}-v{version}"
        data = tx.read(path)
        if not data:
            raise RepositoryUnavailable("Personal revision missing")
        record = PersonalRecord(**data)
        if (record.owner_uid, record.collection, record.record_id, record.version) != (self.owner_uid, collection, record_id, version):
            raise RepositoryUnavailable("Personal revision inconsistent")
        return record

    def read(self, context, collection, record_id, *, version=None):
        self.authorize(context)
        key = self.key(collection, record_id)
        if version is not None and (type(version) is not int or version < 1):
            raise InvalidRecord("Invalid revision")

        def operation(tx):
            head = tx.read(f"owners/{self.owner_uid}/record_heads/{key}")
            if head is None:
                return None
            current = head["version"]
            if version is not None and version > current:
                return None
            return self._record(tx, collection, record_id, version or current)
        return self.store.atomic(operation)

    def write(self, context, collection, record_id, payload, *, expected_version, request_id, inputs: dict[tuple[str, str], int] | None = None):
        """inputs: other records whose head versions must still match, checked inside the same transaction."""
        self.authorize(context)
        key = self.key(collection, record_id)
        checks = [(self.key(c, r), v) for (c, r), v in (inputs or {}).items()]
        if any(type(v) is not int or v < 1 for _, v in checks):
            raise InvalidRecord("Explicit existing input versions required")
        if type(expected_version) is not int or expected_version < 0 or not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
            raise InvalidRecord("Invalid expected version or request ID")
        if type(payload) is not dict:
            raise InvalidRecord("Payload must be a JSON object")
        validate_payload(payload)
        payload = deepcopy(payload)
        if len(canonical(payload).encode()) > 524288:
            raise InvalidRecord("Payload too large")
        fingerprint = digest([collection, record_id, expected_version, payload, sorted(checks)])
        root = f"owners/{self.owner_uid}"
        request_path = f"{root}/mutation_requests/{request_id}"
        head_path = f"{root}/record_heads/{key}"
        created_at = self.clock().astimezone(timezone.utc).isoformat()

        def operation(tx):
            previous = tx.read(request_path)
            if previous:
                if previous["fingerprint"] != fingerprint:
                    raise IdempotencyConflict("Request ID has different content")
                return self._record(tx, collection, record_id, previous["version"])
            for input_key, input_version in checks:
                input_head = tx.read(f"{root}/record_heads/{input_key}")
                if input_head is None or input_head["version"] != input_version:
                    raise VersionConflict("Input versions changed")
            head = tx.read(head_path)
            current = head["version"] if head else 0
            if current != expected_version:
                raise VersionConflict("Expected version is no longer current")
            record = PersonalRecord(self.owner_uid, collection, record_id, current + 1, payload, created_at, request_id)
            tx.create(f"{root}/{collection}/{key}-v{record.version}", asdict(record))
            tx.put(head_path, {"version": record.version})
            tx.create(request_path, {"fingerprint": fingerprint, "version": record.version})
            return record
        return self.store.atomic(operation)

    def export(self, context) -> dict[str, dict]:
        """Every document under this owner's namespace, keyed by path relative to owners/{uid}/."""
        self.authorize(context)
        root = f"owners/{self.owner_uid}/"
        return {path[len(root):]: data for path, data in self.store.dump(root).items()}

    def import_documents(self, context, documents: dict[str, dict], *, dry_run: bool) -> tuple[int, int, int]:
        """(to_create, identical, conflicts). Writes nothing unless dry_run is False and there are no conflicts."""
        self.authorize(context)
        root = f"owners/{self.owner_uid}/"
        if any(not isinstance(p, str) or p.startswith("/") or ".." in p.split("/") for p in documents):
            raise InvalidRecord("Invalid document path")

        def operation(tx):
            existing = {path: tx.read(root + path) for path in documents}  # Firestore: every read before any write
            missing = [p for p, d in existing.items() if d is None]
            identical = sum(1 for p, d in existing.items() if d is not None and d == documents[p])
            conflicts = len(documents) - len(missing) - identical
            create = len(missing)
            if not dry_run and not conflicts:
                for path in missing:
                    tx.create(root + path, documents[path])
            return create, identical, conflicts
        return self.store.atomic(operation)

    def require_current(self, context, versions: dict[tuple[str, str], int]):
        """Verify all input heads in one remote transaction; not a publish lock."""
        self.authorize(context)
        keys = [(self.key(c, r), v) for (c, r), v in versions.items()]
        if not keys or any(type(v) is not int or v < 1 for _, v in keys):
            raise InvalidRecord("Explicit existing input versions required")

        def operation(tx):
            for key, expected in keys:
                head = tx.read(f"owners/{self.owner_uid}/record_heads/{key}")
                if head is None or head["version"] != expected:
                    raise VersionConflict("Input versions changed")
        self.store.atomic(operation)
