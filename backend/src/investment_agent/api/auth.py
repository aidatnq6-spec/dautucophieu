"""Versioned server context; a browser-supplied UID alone has no authority."""

from dataclasses import dataclass, field
import hashlib
import hmac
import os
import re
from threading import Lock
from typing import Callable

from fastapi import Request


@dataclass(frozen=True)
class InternalAuthSettings:
    owner_uid: str
    token: str = field(repr=False)
    hmac_secret: str = field(repr=False)

    def __post_init__(self):
        if not self.owner_uid or len(self.owner_uid) > 128 or any(ord(c) < 32 for c in self.owner_uid):
            raise ValueError("Invalid owner configuration")
        if any(len(s) < 32 or not s.isascii() or any(ord(c) < 33 for c in s) for s in (self.token, self.hmac_secret)):
            raise ValueError("Internal secrets must be separate ASCII values of at least 32 characters")
        if self.token == self.hmac_secret:
            raise ValueError("Internal secrets must be different")

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("FIREBASE_OWNER_UID", ""), os.environ.get("INTERNAL_API_TOKEN", ""), os.environ.get("INTERNAL_API_HMAC_SECRET", ""))


@dataclass(frozen=True)
class OwnerContext:
    uid: str
    role: str
    correlation_id: str


class Unauthorized(Exception):
    pass


class InternalAuthenticator:
    """One process, one worker. Nonces expire with the signed timestamp window."""

    def __init__(self, settings: InternalAuthSettings, clock: Callable[[], float]):
        self.settings = settings
        self.clock = clock
        self._nonces: dict[str, int] = {}
        self._lock = Lock()

    def verify(self, request: Request, body: bytes) -> OwnerContext:
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            raise Unauthorized()
        headers = request.headers
        required = ("authorization", "x-owner-uid", "x-owner-role", "x-correlation-id", "x-request-timestamp", "x-request-nonce", "x-request-signature")
        if any(len(headers.getlist(k)) != 1 for k in required):
            raise Unauthorized()
        if not hmac.compare_digest(headers["authorization"].encode(), f"Bearer {self.settings.token}".encode()):
            raise Unauthorized()
        uid, role = headers["x-owner-uid"], headers["x-owner-role"]
        correlation, nonce = headers["x-correlation-id"], headers["x-request-nonce"]
        if uid != self.settings.owner_uid or role != "owner":
            raise Unauthorized()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", correlation) or not re.fullmatch(r"[a-f0-9]{32}", nonce):
            raise Unauthorized()
        timestamp = headers["x-request-timestamp"]
        if not re.fullmatch(r"[0-9]{1,12}", timestamp):
            raise Unauthorized()
        now = int(self.clock())
        if abs(now - int(timestamp)) > 60:
            raise Unauthorized()
        target = request.scope["raw_path"].decode("ascii")
        query = request.scope["query_string"].decode("ascii")
        if query:
            target += "?" + query
        canonical = "\n".join(["v1", timestamp, nonce, uid, role, correlation, request.method, target, hashlib.sha256(body).hexdigest()])
        expected = hmac.new(self.settings.hmac_secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(headers["x-request-signature"].encode(), expected.encode()):
            raise Unauthorized()
        with self._lock:
            self._nonces = {key: expiry for key, expiry in self._nonces.items() if expiry >= now}
            if nonce in self._nonces or len(self._nonces) >= 10000:
                raise Unauthorized()
            self._nonces[nonce] = int(timestamp) + 60
        return OwnerContext(uid, role, correlation)


def require_owner(request: Request) -> OwnerContext:
    """Repositories/routes consume this verified context, never UID query fields."""
    context = getattr(request.state, "owner", None)
    if not isinstance(context, OwnerContext):
        raise Unauthorized()
    return context
