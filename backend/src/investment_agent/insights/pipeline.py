"""insights-run: discover new public reports, extract text, ask the model (public text only), keep verified claims."""

import json
from datetime import timedelta

from investment_agent.ai.openrouter import AIUnavailable

from .extract import RESPONSE_FORMAT, build_messages, validate
from .store import _ID

MAX_REPORTS, FIRST_WINDOW_DAYS, PAUSE, MAX_ATTEMPTS = 3, 60, 2.0, 3
# Codes that will fail the same way for every report: stop the run and leave reports unprocessed.
STOPPING = {"key_missing", "policy_not_approved", "budget_not_configured", "budget_exceeded", "catalog_stale",
            "no_eligible_model", "unknown_task", "concurrency_cap"}


def _parse(content, texts, sectors) -> dict | None:
    """Model output is untrusted: anything that is not a JSON object of the expected shape yields no insight."""
    try:
        raw = json.loads(content) if isinstance(content, str) else None
        return validate(raw, texts, sectors) if isinstance(raw, dict) else None
    except Exception:
        return None


def run_insights(*, store, discover, download, pages, gateway, sectors, now, sleep) -> dict:
    since = (now - timedelta(days=FIRST_WINDOW_DAYS)).date()
    failures = store.failures()

    def pending(ref) -> bool:
        if not (_ID.fullmatch(ref.source) and _ID.fullmatch(ref.ref_id)):
            return False  # unexpected id shape from a source: never used as a file name
        attempts = int((failures.get(f"{ref.source}:{ref.ref_id}") or {}).get("attempts", 0))
        return store.read(ref.source, ref.ref_id) is None and attempts < MAX_ATTEMPTS

    todo = [r for r in discover(since) if pending(r)][:MAX_REPORTS]
    processed, errors = [], {}

    def fail(key: str, code: str) -> None:
        errors[key] = code
        store.record_failure(key, code, now.isoformat())  # given up after MAX_ATTEMPTS runs, so it cannot block newer reports

    for i, ref in enumerate(todo):
        key = f"{ref.source}:{ref.ref_id}"
        if i:
            sleep(PAUSE)
        try:
            texts = pages(download(ref.pdf_url))
        except Exception:  # network, size refusal or unreadable file
            fail(key, "download_failed")
            continue
        record = {"source": ref.source, "ref_id": ref.ref_id, "title": ref.title, "page_url": ref.page_url, "pdf_url": ref.pdf_url,
                  "published": ref.published.isoformat(), "processed_at": now.isoformat(), "telegram_sent": False}
        if not any(t.strip() for t in texts):
            store.save({**record, "status": "no_text", "insight": None, "model": None, "cost_usd": "0"})
            processed.append(key)
            continue
        try:
            done = gateway.complete("insights", build_messages(ref.title, texts, sectors), job_id=f"insights-{ref.source}-{ref.ref_id}",
                                    response_format=RESPONSE_FORMAT)
        except AIUnavailable as exc:
            if exc.code in STOPPING:
                return {"status": f"stopped:{exc.code}", "processed": processed, "skipped": len(todo) - len(processed), "errors": errors}
            fail(key, exc.code)
            continue
        insight = _parse(done.content, texts, sectors)
        claims = insight and (insight["macro_now"]["reasons"] or insight["macro_outlook"]["reasons"] or insight["sectors"])
        store.save({**record, "status": "ok" if claims else "no_reliable_claims", "insight": insight, "model": done.model,
                    "cost_usd": str(done.cost_usd)})
        processed.append(key)
    return {"status": "ok", "processed": processed, "skipped": 0, "errors": errors}
