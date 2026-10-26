"""Telegram summary for each newly processed report; the ticker linking is done locally before rendering."""

from investment_agent.notifications.render import split_message

VIEW_VI = {"favourable": "Thuận lợi", "neutral": "Trung tính", "unfavourable": "Bất lợi"}
VERDICT_VI = {"cheap": "Rẻ", "fair": "Hợp lý", "expensive": "Đắt", "insufficient": "chưa đủ dữ liệu"}
SOURCE_VI = {"acbs": "ACBS", "worldbank": "World Bank"}
MAX_SECTORS = 5


def _tickers(row: dict, warn: bool) -> str:
    parts = []
    for t in row["tickers"]:
        mark = " ⚠ đang nắm" if warn and t["held"] else ""
        parts.append(f"{t['symbol']} ({VERDICT_VI.get(t['verdict'], t['verdict'])}){mark}")
    return f" — {', '.join(parts)}" if parts else ""


def render_insight(record: dict, linked_sectors: list[dict]) -> str:
    ins = record["insight"]
    lines = [f"NHẬN ĐỊNH MỚI · {SOURCE_VI.get(record['source'], record['source'])}", record["title"], "",
             f"Vĩ mô hiện tại: {VIEW_VI.get(ins['macro_now']['view'], 'không có nhận định kiểm chứng được')}"]
    lines += [f"• {r['text']}" for r in ins["macro_now"]["reasons"]]
    lines.append(f"6–12 tháng: {VIEW_VI.get(ins['macro_outlook']['view'], 'không có nhận định kiểm chứng được')}")
    lines += [f"• {r['text']}" for r in ins["macro_outlook"]["reasons"]]
    for effect, sign, heading in (("benefit", "+", "Ngành hưởng lợi"), ("harm", "−", "Ngành bất lợi")):
        # Most-cited first; on a tie, sectors with watched tickers first, since those are the ones the owner can act on.
        rows = sorted((r for r in linked_sectors if r[effect] > 0), key=lambda r: (-r[effect], not r["tickers"]))[:MAX_SECTORS]
        if rows:
            lines += ["", heading]
            for row in rows:
                reason = next((c["reason"] for c in row["claims"] if c["effect"] == effect), "")
                lines.append(f"{sign} {row['sector']}: {reason}{_tickers(row, effect == 'harm')}")
    lines += ["", record["page_url"], "Tóm tắt tự động từ báo cáo công khai, không phải khuyến nghị đầu tư."]
    return "\n".join(lines)


def send_new(store, sender, settings, render, *, since: str) -> dict:
    """Send every verified, not-yet-sent report published on or after since (ISO date), so switching Telegram on later
    does not flood the chat with old reports. A message that fails part-way resumes at the failed part next run."""
    if not (settings.enabled and settings.scheduled_enabled and settings.chat_id):
        return {"sent": 0, "failed": 0}
    sent = failed = 0
    for record in store.all():
        if record.get("status") != "ok" or record.get("telegram_sent") or record["published"] < since:
            continue
        parts = split_message(render(record))
        done = int(record.get("telegram_parts_sent") or 0)
        for part in parts[done:]:
            if sender.send(settings.chat_id, part).status != "sent":
                break
            done += 1
        if done >= len(parts):
            store.save({**record, "telegram_sent": True, "telegram_parts_sent": done})
            sent += 1
        else:
            store.save({**record, "telegram_parts_sent": done})
            failed += 1
    return {"sent": sent, "failed": failed}
