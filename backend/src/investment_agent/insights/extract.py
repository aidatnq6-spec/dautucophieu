"""Per-report extraction: prompt built from public report text only, JSON schema output, quotes verified locally.

Nothing personal (holdings, watchlist, valuations) is ever passed here; the owner allowed AI for public report text only.
"""

import re
import unicodedata

from investment_agent.ai.prompts import load_prompt

VIEWS = ("favourable", "neutral", "unfavourable")
VIEW = {"type": "string", "enum": list(VIEWS)}
REASON = {"type": "object", "additionalProperties": False, "required": ["text", "quote", "page"],
          "properties": {"text": {"type": "string"}, "quote": {"type": "string"}, "page": {"type": "integer"}}}
MACRO = {"type": "object", "additionalProperties": False, "required": ["view", "reasons"],
         "properties": {"view": VIEW, "reasons": {"type": "array", "items": REASON, "maxItems": 5}}}
SECTOR = {"type": "object", "additionalProperties": False, "required": ["sector", "effect", "reason", "quote", "page"],
          "properties": {"sector": {"type": "string"}, "effect": {"type": "string", "enum": ["benefit", "harm"]},
                         "reason": {"type": "string"}, "quote": {"type": "string"}, "page": {"type": "integer"}}}
RESPONSE_FORMAT = {"type": "json_schema", "json_schema": {"name": "report_insight", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["macro_now", "macro_outlook", "sectors"],
    "properties": {"macro_now": MACRO, "macro_outlook": MACRO, "sectors": {"type": "array", "maxItems": 12, "items": SECTOR}}}}}
MAX_CHARS = 120_000  # keeps one request well under the per-request budget


def prompt_version() -> str:
    return load_prompt("insights").version


def build_messages(title: str, pages: list[str], sectors: list[str]) -> list[dict]:
    body, used = [], 0
    for i, text in enumerate(pages, start=1):
        chunk = f"[Trang {i}]\n{text.strip()}\n"
        if used + len(chunk) > MAX_CHARS and body:
            break
        body.append(chunk[:MAX_CHARS])
        used += len(chunk)
    user = f"Tiêu đề báo cáo: {title}\nDanh sách ngành được phép: {', '.join(sectors)}\n\n" + "\n".join(body)
    return [{"role": "system", "content": load_prompt("insights").text}, {"role": "user", "content": user}]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", str(text)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]|_", " ", text)).strip()


def _page(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _found(item: dict, pages: list[str]) -> bool:
    q, page = normalise(item.get("quote", "")), _page(item.get("page"))
    return bool(q) and 1 <= page <= len(pages) and q in normalise(pages[page - 1])


def _items(value) -> list[dict]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def validate(raw: dict, pages: list[str], sectors: list[str]) -> dict:
    """Keep only claims whose quote is on the cited page and whose sector is in the closed list; count the rest."""
    dropped, allowed, out = 0, set(sectors), {}
    for key in ("macro_now", "macro_outlook"):
        block = raw.get(key) if isinstance(raw.get(key), dict) else {}
        given = _items(block.get("reasons"))
        reasons = [{"text": str(r.get("text", "")), "quote": str(r["quote"]), "page": r["page"]} for r in given if _found(r, pages)]
        dropped += len(given) - len(reasons)
        view = block.get("view") if block.get("view") in VIEWS else "neutral"
        out[key] = {"view": view, "reasons": reasons}
    given = _items(raw.get("sectors"))
    kept = [{"sector": s["sector"], "effect": s["effect"], "reason": str(s.get("reason", "")), "quote": str(s["quote"]), "page": s["page"]}
            for s in given if s.get("sector") in allowed and s.get("effect") in ("benefit", "harm") and _found(s, pages)]
    dropped += len(given) - len(kept)
    out["sectors"], out["dropped"] = kept, dropped
    return out
