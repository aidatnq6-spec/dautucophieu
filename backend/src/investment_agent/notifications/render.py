"""Plain-text Telegram rendering of a published report, split after rendering.

Plain text (no parse mode) avoids escaping errors. The 4096-character limit
applies to the rendered text, so splitting happens last, on line boundaries
where possible, and every part carries "(i/n)".
"""

MAX_MESSAGE = 4096
_PREFIX_RESERVE = 12  # "(99/99)\n"

ACTIONS = {"buy_tranche": "Mua từng phần", "hold": "Giữ", "reduce": "Cân nhắc giảm", "wait": "Chờ", "insufficient_basis": "Chưa đủ cơ sở"}


def vnd(value: str | None) -> str:
    if value is None:
        return "chưa có"
    negative = value.startswith("-")
    whole, _, frac = value.lstrip("-").partition(".")
    if frac and frac[0] >= "5":
        whole = str(int(whole) + 1)
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{'−' if negative and grouped != '0' else ''}{grouped} đ"


def render_report(report: dict) -> str:
    s = report["ledger_summary"]
    lines = [f"BẢN TIN SAU PHIÊN {report['session_date']}", f"(dữ liệu {report['provenance']})", "",
             f"KẾT LUẬN: {report['decision']['headline']}", "", "DANH MỤC",
             f"Tiền trong sổ: {vnd(s['cash'])} · Lãi/lỗ đã thực hiện: {vnd(s['realized_gain'])} · Cổ tức ròng: {vnd(s['dividend_income'])}"]
    for h in report["holdings"]:
        lines.append(f"- {h['security_id']}: {h['quantity']} cp · giá trị {vnd(h['market_value'])} · lãi/lỗ chưa thực hiện {vnd(h['unrealized_gain'])}"
                     f" · giá ngày {h['price_date'] or 'chưa có'}")
    lines += ["", "THỊ TRƯỜNG", report["narrative"]["text"], "", "CƠ HỘI"]
    lines += [f"- {i['entity_id']}: {ACTIONS.get(i['action'], i['action'])} ({', '.join(i['reasons'])})" for i in report["items"]] or ["- Không có"]
    if report.get("reminders"):
        lines += ["", "NHẮC CẬP NHẬT SỐ LIỆU VĨ MÔ (nhập ở trang Vĩ mô)"] + [f"- {r}" for r in report["reminders"]]
    lines += ["", "RỦI RO VÀ GIỚI HẠN DỮ LIỆU"] + [f"- {f}" for f in report["verification_flags"]] + \
             ["- Khuyến nghị không tự đặt lệnh; kiểm tra lại trước khi giao dịch."]
    if report.get("sources"):
        lines += ["", "Nguồn: " + ", ".join(report["sources"])]
    return "\n".join(lines)


def split_message(text: str, limit: int = MAX_MESSAGE) -> list[str]:
    room = limit - _PREFIX_RESERVE
    chunks, current, started = [], "", False
    for line in text.split("\n"):
        piece = line
        while True:
            sep = "\n" if started else ""
            space = room - len(current) - len(sep)
            if len(piece) <= space:
                current, started = current + sep + piece, True
                break
            if (len(piece) <= room and started) or space <= 0:  # start a fresh part, keeping a fitting line whole
                chunks.append(current)
                current, started = "", False
                continue
            # Over-long line: fill this part, continue the line in the next one.
            chunks.append(current + sep + piece[:space])
            current, started, piece = "", False, piece[space:]
    if current or not chunks:
        chunks.append(current)
    return [f"({i}/{len(chunks)})\n{chunk}" for i, chunk in enumerate(chunks, 1)]
