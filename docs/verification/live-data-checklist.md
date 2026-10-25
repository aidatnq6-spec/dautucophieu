# Checklist kiểm chứng live

Mục chưa đánh dấu đang **not_run** (cập nhật 2026-10-25). Ghi `passed`/`failed`/`not_run` kèm ngày, người chạy và bằng chứng đã che thông tin cá nhân. Không chuyển kết quả test tổng hợp thành bằng chứng chất lượng đầu tư thật.

## Nguồn dữ liệu (cần trước khuyến nghị thật)

- [ ] Chọn nguồn được phép dùng (điều khoản gói/tài khoản đã đọc; chủ sở hữu tự đăng ký/mua nếu cần). — not_run
- [ ] Viết adapter cho nguồn đã chọn; capability chỉ ghi `verified` khi có bằng chứng audit. — not_run
- [ ] Audit từng ứng viên 50 mã: ≥ 10 năm, ≥ 10 kỳ năm, ≥ 40 kỳ quý, ngày công bố, sự kiện vốn, quyền sử dụng. — not_run
- [ ] Đối chiếu một số mã với báo cáo gốc (ngân hàng, phi tài chính, chu kỳ, bất động sản, một mã chuyển sàn). — not_run
- [ ] Kiểm tra P/E, P/B qua phát hành thêm/tách cổ phiếu và bản sửa số liệu. — not_run
- [x] Lịch nghỉ HOSE 2026 (`config/trading-calendar-hose-2026.json`) theo Thông báo 2294/TB-SGDHCM và bản cập nhật 25/12/2025 — passed 2026-10-25 qua bản đăng lại; còn đối chiếu bản gốc hsx.vn.
- [x] Lô, bước giá, biên độ, thuế ghi vào `docs\decisions\market-rules.md` kèm căn cứ — passed 2026-10-25 (một phần): còn Phụ lục III của 22/QĐ-HĐTV/2026 và điều khoản T+2 gốc.

## Firebase

- [x] Cấu hình service account cục bộ (khóa ngoài repo), owner UID, đăng nhập Google — passed 2026-10-25: chủ sở hữu đăng nhập và mở trang Tổng quan.
- [ ] Xác nhận một tài khoản Google khác bị từ chối trên môi trường thật. — not_run (đã có test tự động)
- [ ] Chạy `test_firestore_emulator.py` với emulator (cần Java ≥ 21). — not_run
- [x] Deploy Firestore Rules (deny client) — passed 2026-10-25T09:55Z, chủ sở hữu chạy `firebase deploy --only firestore:rules`; rules cũ của project dùng chung được sao lưu ngoài repo. Kiểm tra client bằng Rules Test API chưa chạy được (service account không có quyền); dựa vào nội dung rules: mặc định từ chối.
- [x] Smoke test `PersonalRepository` trên Firestore thật, namespace tạm `owners/smoke-<ngẫu nhiên>` đã xóa sau khi chạy — passed 2026-10-25, 10/10: tạo revision, retry idempotent, từ chối request_id dùng lại với payload khác, CAS, giữ lịch sử, chặn ghi khi input cũ, export, khôi phục vào namespace rỗng.
- [x] Sao lưu thật (`cli backup`) — passed 2026-10-25, bản `backups/20261025T095916Z-manual`, checksum khớp.
- [ ] Diễn tập khôi phục từ một bản sao lưu thật vào project/thư mục riêng. — not_run (khôi phục mới được thử trong smoke test)

## AI (sau khi chủ sở hữu đặt ngân sách)

- [ ] Duyệt chính sách AI (model cụ thể, endpoint ZDR, không thu thập dữ liệu, ngân sách USD). — not_run
- [ ] Chạy bộ đánh giá 2–3 model theo `docs\verification\model-evaluation.md`. — not_run
- [ ] Xác nhận tham số `usage` không xung đột với `require_parameters`. — not_run

## Telegram

- [ ] Đặt `TELEGRAM_BOT_TOKEN`, Group ID, xác nhận thành viên được xem dữ liệu cá nhân. — not_run
- [ ] "Gửi thử" một bản tin đã phát hành; kiểm tra message ID, chia phần, xử lý timeout. — not_run

## Windows

- [ ] `register-tasks.ps1 -Register`, kiểm tra chạy 17:30/18:30/20:00 và chạy bù khi đăng nhập. — not_run
- [ ] Một phiên thật từ dữ liệu thật đến bản tin (không gửi trùng). — not_run
