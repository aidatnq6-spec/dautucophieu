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


def _num(value, places: int = 2, sign: bool = False) -> str:
    """Vietnamese grouping (1.234,56) with a real minus sign; sign=True adds '+' to positives."""
    d = float(value)
    whole = f"{abs(d):,.{places}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return ("−" if d < 0 else "+" if sign and d > 0 else "") + whole


def _pct(value) -> str:
    return _num(float(value) * 100, 2, sign=True) + "%"


def _missing(name: str, section: dict | None) -> str:
    return f"{name}: chưa có số liệu ({(section or {}).get('reason', 'không rõ lý do')})"


def _session_lines(shape: dict | None) -> list[str]:
    """VN-Index's range, its run of sessions and matched volume against its base (brief.session_shape); numbers only."""
    if not shape or shape.get("status") != "ok":
        return [_missing("Trong phiên", shape)] if shape else []
    r, k, v = shape["range"], shape["streak"], shape["volume"]
    lines = [f"Trong phiên: cao {_num(r['high'])} · thấp {_num(r['low'])} · đóng cửa cách đỉnh {_num(r['from_high'])} điểm, "
             f"cách đáy {_num(r['from_low'])} điểm"]
    if k["direction"] == "flat":
        lines.append("Chuỗi: đứng giá so với phiên trước")
    elif k["direction"]:
        word = "tăng" if k["direction"] == "up" else "giảm"
        lines.append(f"Chuỗi: {word} ít nhất {k['sessions']} phiên liên tiếp" if k["at_least"]
                     else f"Chuỗi: {word} {k['sessions']} phiên liên tiếp, {_num(k['change'], sign=True)} điểm ({_pct(k['pct'])})")
    lines.append(_base_line(f"Khối lượng khớp lệnh: {_num(v['today'], 0)} cp", v, "change_pct") if v.get("status") == "ok"
                 else _missing("Khối lượng khớp lệnh", v))
    return lines


def _base_line(head: str, figures: dict, change_key: str) -> str:
    parts = [head]
    if figures.get(change_key) is not None:
        parts.append(f"{_pct(figures[change_key])} so với phiên trước")
    if figures.get("ratio20") is not None:
        parts.append(f"bằng {_num(figures['ratio20'])} lần trung bình 20 phiên")
    return ", ".join(parts)


def _spread_line(spread: dict | None, indices: dict | None) -> str | None:
    """Every traded stock at the same weight beside the cap-weighted VN-Index; an opposite direction is named, nothing more."""
    if not spread or spread.get("mean_pct") is None:
        return None
    line = (f"Lan tỏa: trung bình cộng các mã {_pct(spread['mean_pct'])}, trung vị {_pct(spread['median_pct'])} "
            f"({spread['count']} mã có giao dịch)")
    vn = next((r for r in (indices or {}).get("rows", []) if r["id"] == "VNINDEX" and r["status"] == "ok"), None)
    if vn:
        line += f"; VN-Index {_pct(vn['pct'])}"
        if float(vn["pct"]) * float(spread["mean_pct"]) < 0:
            line += ", ngược chiều"
    return line


def _recovery_line(r: dict) -> str:
    """Bảng kiểm "Thị trường phục hồi" in one line: the count met, then each condition with its figure (brief.recovery)."""
    unknown = r["total"] - r["known"]
    head = f"Bảng kiểm phục hồi: {r['met']}/{r['total']} đạt" + (f", {unknown} chưa có số" if unknown else "")
    parts = [f"{c['label']}: {c['figure']}" if c["met"] is None else f"{c['label']}: {'đạt' if c['met'] else 'chưa'} ({c['figure']})"
             for c in r["checks"]]
    return head + " — " + " · ".join(parts)


def render_market_brief(report: dict, market: dict) -> str:
    """Short phone version agreed on 2026-10-26: market first, holdings' prices, a few news, one portfolio line, reminders."""
    day = report["session_date"]
    lines = [f"BẢN TIN SAU PHIÊN {day[8:10]}/{day[5:7]}/{day[:4]}", ""]
    for row in (market.get("indices") or {}).get("rows", []):
        name = "VN-Index" if row["id"] == "VNINDEX" else row["id"]
        lines.append(f"{name} {_num(row['close'])} ({_num(row['change'], sign=True)} điểm, {_pct(row['pct'])})" if row["status"] == "ok"
                     else _missing(name, row))
    lines += _session_lines(market.get("index_session"))
    board, hose = market.get("board") or {}, market.get("hose") or {}
    if board.get("status") == "ok":
        b, f = board["breadth"], board["foreign"]
        lines += [f"Giá trị khớp lệnh HOSE: {_num(board['value_matched_bn'])} tỷ đồng ({_num(board['volume_matched'], 0)} cp)"]
        if hose.get("status") == "ok":
            value = market.get("hose_liquidity") or {}
            head = f"HOSE công bố tổng (gồm thỏa thuận): {_num(hose['total_value_bn'])} tỷ đồng"
            lines.append(_base_line(head, value, "change_pct") if value.get("status") == "ok" else head)
        lines += [f"Độ rộng: {b['up']} tăng · {b['down']} giảm · {b['flat']} đứng giá · {b['no_trade']} không giao dịch"]
        if board["sectors"]:
            lines.append(f"Ngành tăng: {sum(1 for s in board['sectors'] if float(s['pct']) > 0)}/{len(board['sectors'])}")
        if (spread := _spread_line(board.get("spread"), market.get("indices"))):
            lines.append(spread)
        if (recovery := market.get("recovery") or {}).get("status") == "ok":
            lines.append(_recovery_line(recovery))
        lines += [
                  f"Khối ngoại: mua {_num(f['buy_value_bn'])} tỷ · bán {_num(f['sell_value_bn'])} tỷ · ròng {_num(f['net_value_bn'], sign=True)} tỷ"]
        if f["top_sell"]:
            lines.append("Bán ròng mạnh: " + "; ".join(f"{x['symbol']} {_num(x['net_value_bn'], sign=True)} tỷ" for x in f["top_sell"]))
        if f["top_buy"]:
            lines.append("Mua ròng mạnh: " + "; ".join(f"{x['symbol']} {_num(x['net_value_bn'], sign=True)} tỷ" for x in f["top_buy"]))
    else:
        lines.append(_missing("Bảng giá cả sàn (giá trị, độ rộng, khối ngoại, ngành)", board))
    lines.append(_missing("Tự doanh", market.get("proprietary")))
    if board.get("status") == "ok" and board["sectors"]:
        lines += ["", "NGÀNH"] + [f"- {s['sector']} {_pct(s['pct'])} ({s['count']} mã)" for s in board["sectors"]]
    held = [t for t in market.get("tickers", []) if t["held"]]
    if held:
        lines += ["", "MÃ ĐANG NẮM"] + [f"- {t['symbol']} {_num(t['price'], 0)} ({_pct(t['pct'])})" if t["pct"] is not None
                                        else f"- {t['symbol']}: chưa giao dịch phiên này" if t.get("state") == "no_trade"
                                        else f"- {t['symbol']}: chưa có giá" for t in held]
    news = market.get("news") or {}
    if news.get("status") == "ok" and news["items"]:
        lines += ["", "TIN NÓNG"] + [f"- {n['title']} ({n['source']})" for n in news["items"][:5]]
    lines += ["", f"Danh mục: {report['decision']['headline']}"]
    if report.get("reminders"):
        lines += ["", "NHẮC CẬP NHẬT SỐ LIỆU VĨ MÔ (nhập ở trang Vĩ mô)"] + [f"- {r}" for r in report["reminders"]]
    lines += ["", "Xem bản đầy đủ trong ứng dụng, mục Bản tin sau phiên.", "Chỉ để theo dõi, không phải khuyến nghị."]
    return "\n".join(lines)


def render_report(report: dict, market: dict | None = None) -> str:
    if market:
        try:
            return render_market_brief(report, market)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass  # a snapshot of another shape: fall back to the full text rather than not sending
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
