# Bàn giao bản thử nghiệm

Ngày 2026-10-25 · nhánh `feat/investment-agent` (chưa merge vào `main`).

## Kết luận

Toàn bộ 31 task của kế hoạch đã có mã và kiểm thử tự động. **Đây chưa phải bản phân tích đầu tư thật đã hoàn tất**: các cổng dữ liệu thật (Mốc A về nguồn, 50 mã × 10 năm) chưa qua, và chưa chạy live Firebase, Telegram hay OpenRouter. Ứng dụng đóng chặt khi thiếu cấu hình: không bịa giá, không phát hành khuyến nghị thật, không gửi tin, không gọi AI tính phí.

## Theo mốc

| Mốc | Kết quả | Giới hạn |
|---|---|---|
| A · Nền tảng | Runtime khóa phiên bản, hợp đồng Decimal, snapshot, công cụ audit | Task 5 `partial`: chưa có nguồn dữ liệu được phép dùng |
| B · Sổ cá nhân | Phân quyền một tài khoản, hồ sơ, khảo sát, phân bổ, sổ, cổ tức, đối chiếu | Firestore emulator/live chưa chạy (Java 8, khóa chưa cấu hình) |
| C · Phân tích có nguồn | Danh sách cần duyệt, giá/tài chính theo thời điểm, mô hình định giá, khuyến nghị | Không có dữ liệu thật nên không thể kích hoạt danh sách hay ra khuyến nghị thật |
| D · AI kiểm soát được | Gateway đóng chặt, ZDR/không thu thập, ngân sách cục bộ, payload allowlist, kiểm tra đầu ra | Chưa gọi live, chưa đánh giá/chọn model |
| E · Trải nghiệm và tự động | Giao diện A+B/C, bản tin lưu trước gửi, Telegram, lịch Windows, sao lưu | Tác vụ Windows chưa đăng ký; chưa có lịch HOSE chính thức; Telegram chưa gửi thật |
| F · Nghiệm thu | `verify.ps1` đạt toàn bộ trên dữ liệu tổng hợp; ma trận nghiệm thu | Mọi mục live `not_run` |

Chi tiết từng điều kiện: [acceptance-matrix.md](acceptance-matrix.md). Việc còn lại: [live-data-checklist.md](live-data-checklist.md).

## Đo đạc

- Chi phí quan sát: 0 USD (không gọi dịch vụ tính phí). Chi phí thật của Firestore/OpenRouter chưa đo.
- Thời gian: bộ test backend ≈ 6 giây; e2e ≈ 25 giây trên máy phát triển. Thời gian job với dữ liệu 50 mã × 10 năm chưa đo.
- Độ phủ dữ liệu thật: 0/50 mã đã kiểm chứng.

## Minh họa đã có trên dữ liệu tổng hợp (e2e)

Tổng quan A+B (kết luận trước, bảng danh mục, mở căn cứ, truy nguồn), sửa giao dịch và tính lại giá vốn, bản tin C với cờ dữ liệu, dữ liệu thiếu hiển thị giới hạn thay vì nút mua. Ngoại lệ 90% chỉ có ở mức domain test (không có giao diện bật ngoại lệ thật).

## Bằng chứng trong Git

Chỉ tài liệu và fixture tổng hợp; không có dữ liệu tài khoản, khóa hay báo cáo cá nhân.
