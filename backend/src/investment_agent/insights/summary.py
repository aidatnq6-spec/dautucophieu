"""Aggregate verified per-report insights locally (no AI) and link sectors to the owner's watchlist and valuations."""

from collections import defaultdict

VIEWS = ("favourable", "neutral", "unfavourable")


def _macro(records: list[dict], key: str) -> dict:
    votes = {v: 0 for v in VIEWS}
    reasons = []
    for r in records:
        block = r["insight"][key]
        if block["view"] in votes:  # None: no verified reason, so not a vote
            votes[block["view"]] += 1
        reasons += [{**x, "source": r["source"], "title": r["title"], "url": r["page_url"]} for x in block["reasons"]]
    best = max(votes.values())
    top = [v for v in VIEWS if votes[v] == best]
    consensus = "none" if best == 0 else (top[0] if len(top) == 1 else "mixed")
    return {"votes": votes, "consensus": consensus, "reasons": reasons}


def summarise(records: list[dict]) -> dict:
    ok = [r for r in records if r.get("status") == "ok" and r.get("insight")]
    sectors = defaultdict(lambda: {"benefit": 0, "harm": 0, "claims": []})
    for r in ok:
        for s in r["insight"]["sectors"]:
            entry = sectors[s["sector"]]
            entry[s["effect"]] += 1
            entry["claims"].append({**s, "source": r["source"], "title": r["title"], "url": r["page_url"]})
    rows = [{"sector": name, **v, "mixed": v["benefit"] > 0 and v["harm"] > 0} for name, v in sectors.items()]
    rows.sort(key=lambda x: (-(x["benefit"] - x["harm"]), x["sector"]))
    return {"reports": len(ok), "macro_now": _macro(ok, "macro_now"), "macro_outlook": _macro(ok, "macro_outlook"), "sectors": rows}


def linking_sectors(all_sectors: dict[str, str], *, watched: set[str], held: set[str]) -> dict[str, str]:
    """Sector of each watched or held ticker; other synced tickers are not shown."""
    return {s: sec for s, sec in all_sectors.items() if s in watched or s in held}


def link(summary: dict, *, sectors: dict[str, str], valuation_rows: list[dict], held: set[str]) -> dict:
    """Runs on the owner's machine only: watchlist, valuations and holdings never reach the model."""
    verdict = {r["symbol"]: r["verdict"] for r in valuation_rows}
    by_sector = defaultdict(list)
    for sym, sec in sectors.items():
        by_sector[sec].append(sym)
    out = []
    for row in summary["sectors"]:
        tickers = [{"symbol": t, "verdict": verdict.get(t, "insufficient"), "held": t in held} for t in sorted(by_sector.get(row["sector"], []))]
        warn = [t["symbol"] for t in tickers if t["held"]] if row["harm"] > row["benefit"] else []
        out.append({**row, "tickers": tickers, "held_warning": warn})
    return {**summary, "sectors": out}
