"""Warm-up after a restart: the first page view used to pay for opening the Firestore connection and reading the market files. Once the
app answers, it opens its main pages itself with signed loopback requests (responses are discarded and stay on this machine), and every
20 minutes it reads one small record so the connection and its token stay open. Never raises: a failure only means a slower first view."""

import hashlib
import hmac
import secrets
import threading
import time
import uuid

from .auth import InternalAuthSettings, OwnerContext

BASE = "http://127.0.0.1:8000"
WARM_PATHS = ("/internal/glance", "/internal/overview", "/internal/equity-budget", "/internal/earnings")
KEEP_ALIVE_SECONDS = 20 * 60
STARTUP_WAIT_SECONDS = 60


def signed_headers(settings: InternalAuthSettings, method: str, target: str, *, now: float) -> dict[str, str]:
    timestamp, nonce, correlation = str(int(now)), secrets.token_hex(16), str(uuid.uuid4())
    canonical = "\n".join(["v1", timestamp, nonce, settings.owner_uid, "owner", correlation, method, target, hashlib.sha256(b"").hexdigest()])
    return {"authorization": f"Bearer {settings.token}", "x-owner-uid": settings.owner_uid, "x-owner-role": "owner", "x-correlation-id": correlation,
            "x-request-timestamp": timestamp, "x-request-nonce": nonce,
            "x-request-signature": hmac.new(settings.hmac_secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()}


def warm_once(settings: InternalAuthSettings, *, get, clock=time.time, base: str = BASE) -> int:
    """Open each main page once; the number that answered 200."""
    ok = 0
    for path in WARM_PATHS:
        try:
            response = get(base + path, headers=signed_headers(settings, "GET", path, now=clock()))
            ok += response.status_code == 200
        except Exception:  # noqa: BLE001 - warming is best effort
            pass
    return ok


def keep_alive(repo, owner_uid: str) -> bool:
    """One small read (a head and, the first time, its revision) to keep the Firestore connection open."""
    if repo is None:
        return False
    try:
        repo.read(OwnerContext(owner_uid, "owner", "warmup"), "settings", "portfolio")
        return True
    except Exception:  # noqa: BLE001 - best effort
        return False


def start(settings: InternalAuthSettings, repo, *, base: str = BASE) -> threading.Thread:
    """A daemon thread: wait for the app to answer, warm the pages, then keep the connection open."""
    import httpx

    def run():
        with httpx.Client(timeout=60) as client:
            for _ in range(STARTUP_WAIT_SECONDS):
                try:
                    if client.get(base + "/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            warm_once(settings, get=client.get, base=base)
        while True:
            time.sleep(KEEP_ALIVE_SECONDS)
            keep_alive(repo, settings.owner_uid)
    thread = threading.Thread(target=run, name="warmup", daemon=True)
    thread.start()
    return thread
