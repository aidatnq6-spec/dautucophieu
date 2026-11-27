# Khối ngoại và tự doanh ròng 20 phiên — Implementation Plan

**Spec:** [docs/superpowers/specs/2026-11-27-ngoai-tu-doanh-20-phien-design.md](../superpowers/specs/2026-11-27-ngoai-tu-doanh-20-phien-design.md)

## Global Constraints
- Khối ngoại ròng = tổng các mã STOCK (mua giá trị − bán giá trị), như mục Khối ngoại hiện nay. Tự doanh ròng = dòng `VNINDEX` của `data/proprietary/`.
- Phiên thiếu số: cột trống, không vẽ 0; tổng ghi số phiên thiếu. Số trống không lưu thành 0.
- Không đổi mục Khối ngoại, Tự doanh hiện có và Telegram.

## Review Focus
- Phiên VNDirect chỉ có dòng chỉ số (24/11/2026): thiếu, hỏi lại khi còn trong 20 phiên — Task 1.
- Phiên mới nhất có số cũ hơn phiên bản tin: ghi phiên và số phiên chậm — Task 2.
- Kho trống hoặc không đọc được: dòng ghi "chưa có số", phần còn lại của bản tin không hỏng — Task 2.
- Tất cả cột cùng dấu hoặc bằng 0: thang không chia cho 0 — Task 3.

### Task 1: Kho khối ngoại
- `market/proprietary_history.py`: tách `SessionStore(data_dir, folder)` và `sync_sessions(store, *, url, parse, get, now, sessions, limit, sleep, pace)`; `ProprietaryStore`, `sync_proprietary` giữ nguyên hành vi (test cũ xanh).
- `market/foreign_history.py`: `ForeignStore`, `parse_foreign_session(text, day)`, `sync_foreign(...)`; `foreign-sync --limit 260` (cli), bước ở lượt 20:00.
- Tests `tests/market/test_foreign_history.py`: giữ STOCK, bỏ CW/ETF/INDEX khỏi `stocks`, giữ dòng VNINDEX ở `index`; phiên chỉ có dòng chỉ số là thiếu; số trống ở `bo_qua`; sync hỏi lại phiên thiếu gần đây.

### Task 2: `brief/flows.py`
- `net_flows(data_dir, session_date: date, sessions: list[date], n=20) -> {"foreign": Flow, "proprietary": Flow}`; Flow ok = `{"status","date","lag_sessions","net_bn","sum_bn","missing","bars":[{"date","net_bn"|None}]}` (tỷ đồng, 2 số lẻ, chuỗi); missing → `{"status":"missing","reason"}`.
- `market_for_session` gắn `out["flows"]` (lịch: `public_tools._sessions`), lỗi chỉ làm mất phần này.
- Tests `tests/brief/test_brief_flows.py`.

### Task 3: Web
- `brief-market.tsx`: `FlowRows` với hai dòng và SVG 20 cột; hàm thuần `flowHead(flow, label, session)` và `barHeights(bars)` có test vitest.

### Task 4: verify, live (chỉ số đếm), review, merge, update-app.
