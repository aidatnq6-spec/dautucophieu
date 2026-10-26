"""insights-run: discover new public reports, extract text, ask the model (public text only), keep verified claims."""

import json
from datetime import timedelta

from investment_agent.ai.openrouter import AIUnavailable

from .extract import RESPONSE_FORMAT, build_messages, validate

MAX_REPORTS, FIRST_WINDOW_DAYS, PAUSE = 3, 60, 2.0
# Codes that will fail the same way for every report: stop the run and leave reports unprocessed.
STOPPING = {"key_missing", "policy_not_approved", "budget_not_configured", "budget_exceeded", "catalog_stale",
            "no_eligible_model", "unknown_task"}


def run_insights(*, store, discover, download, pages, gateway, sectors, now, sleep) -> dict:
    since = (now - timedelta(days=FIRST_WINDOW_DAYS)).date()
    todo = [r for r in discover(since) if store.read(r.source, r.ref_id) is None][:MAX_REPORTS]
    processed = []
    for i, ref in enumerate(todo):
        if i:
            sleep(PAUSE)
        try:
            texts = pages(download(ref.pdf_url))
        except Exception:  # network or size refusal: retried on the next run
            continue
        record = {"source": ref.source, "ref_id": ref.ref_id, "title": ref.title, "page_url": ref.page_url, "pdf_url": ref.pdf_url,
                  "published": ref.published.isoformat(), "processed_at": now.isoformat(), "telegram_sent": False}
        if not any(t.strip() for t in texts):
            store.save({**record, "status": "no_text", "insight": None, "model": None, "cost_usd": "0"})
            processed.append(f"{ref.source}:{ref.ref_id}")
            continue
        try:
            done = gateway.complete("insights", build_messages(ref.title, texts, sectors), job_id=f"insights-{ref.source}-{ref.ref_id}",
                                    response_format=RESPONSE_FORMAT)
        except AIUnavailable as exc:
            if exc.code in STOPPING:
                return {"status": f"stopped:{exc.code}", "processed": processed, "skipped": len(todo) - len(processed)}
            continue  # transient: retried on the next run
        try:
            raw = json.loads(done.content or "{}")
            insight = validate(raw, texts, sectors) if isinstance(raw, dict) else None
        except ValueError:
            insight = None
        claims = insight and (insight["macro_now"]["reasons"] or insight["macro_outlook"]["reasons"] or insight["sectors"])
        store.save({**record, "status": "ok" if claims else "no_reliable_claims", "insight": insight, "model": done.model,
                    "cost_usd": str(done.cost_usd)})
        processed.append(f"{ref.source}:{ref.ref_id}")
    return {"status": "ok", "processed": processed, "skipped": 0}
