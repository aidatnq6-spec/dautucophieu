# Checklist kiểm chứng live

Mọi mục dưới đây đang **not_run** (2026-10-25). Ghi `passed`/`failed`/`not_run` kèm ngày, người chạy và bằng chứng đã che thông tin cá nhân. Không chuyển kết quả test tổng hợp thành bằng chứng chất lượng đầu tư thật.

## Nguồn dữ liệu (cần trước khuyến nghị thật)

- [ ] Chọn nguồn được phép dùng (điều khoản gói/tài khoản đã đọc; chủ sở hữu tự đăng ký/mua nếu cần). — not_run
- [ ] Viết adapter cho nguồn đã chọn; capability chỉ ghi `verified` khi có bằng chứng audit. — not_run
- [ ] Audit từng ứng viên 50 mã: ≥ 10 năm, ≥ 10 kỳ năm, ≥ 40 kỳ quý, ngày công bố, sự kiện vốn, quyền sử dụng. — not_run
- [ ] Đối chiếu một số mã với báo cáo gốc (ngân hàng, phi tài chính, chu kỳ, bất động sản, một mã chuyển sàn). — not_run
- [ ] Kiểm tra P/E, P/B qua phát hành thêm/tách cổ phiếu và bản sửa số liệu. — not_run
- [ ] Lập `data\trading-calendar.json` từ lịch nghỉ chính thức HOSE, ghi nguồn. — not_run
- [ ] Đối chiếu quy tắc T+, lô, thuế/phí hiện hành vào `docs\decisions\market-rules.md`. — not_run

## Firebase

- [ ] Cấu hình service account cục bộ, owner UID, đăng nhập Google; xác nhận tài khoản khác bị từ chối. — not_run
- [ ] Chạy `test_firestore_emulator.py` với emulator (cần Java ≥ 21). — not_run
- [ ] Deploy Firestore Rules (deny client) và indexes; kiểm tra client không đọc được dữ liệu. — not_run
- [ ] Sao lưu thật (`cli backup`) và diễn tập khôi phục vào project/thư mục riêng. — not_run

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
