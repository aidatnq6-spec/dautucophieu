# Tự doanh cho Claude — Implementation Plan

**Goal:** Công cụ MCP `tu_doanh` trả mua, bán, ròng của tự doanh HOSE theo khoảng phiên và theo mã, từ kho `data/proprietary/`.

**Spec:** [docs/superpowers/specs/2026-11-27-tu-doanh-mcp-design.md](../superpowers/specs/2026-11-27-tu-doanh-mcp-design.md)

## Global Constraints
- Số giữ đơn vị nguồn (đồng, cổ phiếu) dạng chuỗi số thập phân; không làm tròn trong kho.
- Không lấy phiên khác thế vào; phiên thiếu số được liệt kê.
- Công cụ chỉ đọc `data/`; không gọi mạng.

## Review Focus
- Phiên VNDirect đăng bù sau khi đã ghi thiếu (trong 20 phiên gần nhất): tải lại và thay tệp thiếu — Task 1.
- Chạy trước 15:00: không hỏi phiên hôm nay — Task 1.
- Mã không có dòng trong một phiên có số: tính là không giao dịch, không phải thiếu — Task 2.
- `so_phien` ngoài 1–250 hay không phải số: kẹp về khoảng, mặc định 60 — Task 2.
- Kho trống: `thieu` kèm lý do — Task 2.

### Task 1: Kho và `proprietary-sync`
- Create `backend/src/investment_agent/market/proprietary_history.py`: `ProprietaryStore(data_dir)` (`read(day) -> dict|None`, `save(record)`, `days() -> list[str]`, `prune(before: date)`), `parse_session(text, day) -> dict` (record of spec item 1; `thieu` when no `VNINDEX` row for the day), `sync_proprietary(data_dir, *, get, now, sessions: list[date], limit=260, sleep, pace=0.5) -> {"status","due","fetched","missing","failed"}`.
- `URL = BASE + "proprietary_trading?q=floor:HOSE~date:{day}&size=9999"`; RETRY_SESSIONS = 20; KEEP_DAYS = 370.
- `cli.py`: `proprietary-sync --data-dir --limit 260`; sessions from `public_tools._sessions(today-370d, today)`.
- `scripts/windows/run-after-close.ps1`: step in the 20:00 block; test in `tests/test_scheduler_script.py`.
- Tests `tests/market/test_proprietary_history.py`: parse keeps STOCK rows only and the VNINDEX row, `khop` true/false; sync newest first, skips stored, retries a missing one inside the last 20 sessions and replaces it, writes `thieu` once for an older one and does not ask again, skips today before 15:00, prunes files older than 370 days, a failing call reported and others go on.

### Task 2: `tu_doanh` in public_tools and mcp_server
- `PublicData.tu_doanh(so_phien=60, ma=None) -> dict` per spec item 3; registered in `mcp_server.py`.
- Tests in `tests/test_public_tools.py`: window ending at newest stored session with `phien_thieu`, `cham_phien`; market totals and top lists (ranked by net value, ties by symbol); `ma` gives per-session rows with "không giao dịch" distinct from missing; clamp of `so_phien`; empty store `thieu`. Tool list test includes `tu_doanh`.

### Task 3: Docs and plugin
- `docs/claude-project-instructions.md` names `tu_doanh`; `/dautu-thitruong` adds a 60-session line; plugin 0.21.0; CLAUDE.md data line.

### Task 4: verify.ps1, live backfill (counts only), final review, merge, update-app, plugin update.
