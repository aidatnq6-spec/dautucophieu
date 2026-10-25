# Hướng dẫn chạy thử cá nhân

Dành cho chủ sở hữu, từ máy Windows sạch. Không cần dán khóa hay bí mật vào hội thoại; mọi giá trị chỉ nằm trong `.env.local` trên máy.

## 1. Runtime và mã

Cài Node 24 LTS, Git 2, Python 3.11 64-bit. Làm theo phần "Runtime" trong README, rồi chạy `scripts\windows\doctor.ps1` cho đến khi không còn mục MISSING/UNSUPPORTED.

## 2. Firebase (một tài khoản)

1. Firebase Console → tạo project; bật **Authentication → Google**; thêm `127.0.0.1` vào **Authorized domains**.
2. Tạo **Firestore Database** (Production mode, vùng `asia-southeast1`).
3. **Project settings → General → Your apps → Web**: đăng ký app, lấy `apiKey`.
4. **Project settings → Service accounts → Generate new private key**: lưu file JSON **ngoài thư mục dự án**.
5. Ghi cấu hình (không in bí mật, sinh khóa nội bộ một lần):
   ```powershell
   scripts\windows\configure-firebase.ps1 -ServiceAccountJson C:\path	o\key.json -WebApiKey <apiKey>
   ```
6. Deploy Rules chặn mọi truy cập trực tiếp từ client: `firebase login`, rồi `firebase deploy --only firestore --project <project-id>`.
7. Build và chạy (bước 3), đăng nhập một lần bằng Google (sẽ bị từ chối vì chưa có UID), lấy UID ở **Authentication → Users**, rồi:
   ```powershell
   scripts\windows\configure-firebase.ps1 -OwnerUid <uid>
   ```
   và khởi động lại ứng dụng.

## 3. Chạy ứng dụng

```powershell
scripts\windowsuild-app.ps1
powershell -ExecutionPolicy Bypass -File scripts\windows\start-app.ps1
```

Mở http://127.0.0.1:3000 → Đăng nhập bằng Google. Tài khoản khác UID đã cấu hình bị từ chối.

## 4. Thiết lập trong ứng dụng

1. **Thiết lập ban đầu**: nhập tài sản, quỹ dự phòng, mục tiêu; bấm "Xem bảng tính vốn", kiểm tra từng dòng trừ/không trừ rồi "Xác nhận". Trả lời 13 câu; nếu có mâu thuẫn, xem lại và xác nhận.
2. **Sổ giao dịch**: nhập số dư đầu kỳ hoặc lịch sử nộp tiền/mua/bán theo sao kê, kèm phí, thuế và ngày thanh toán thực tế. Sửa/hủy để lại dấu vết và có thể khôi phục.
3. **Cài đặt**: nhập phí giao dịch theo biểu phí của bạn (%). Telegram: đặt `TELEGRAM_BOT_TOKEN` trong `.env.local`, nhập Group ID, xác nhận thành viên nhóm được xem dữ liệu danh mục, rồi mới bật gửi.
4. **Nghiên cứu**: duyệt/từ chối đề xuất danh sách; duyệt giả định định giá từng mã (ba kịch bản, biên an toàn, tỷ lệ giải ngân, nguồn).

## 5. Những gì còn thiếu trước khi dùng cho quyết định thật

- **Nguồn dữ liệu thị trường**: ứng dụng hiện dùng `EmptyMarket` — không có giá, tài liệu hay báo cáo tài chính thật, nên mọi khuyến nghị là "chưa đủ cơ sở" và bản tin là "thiếu dữ liệu". Cần chọn nguồn được phép dùng và viết adapter (xem `docs/data/2026-10-25-source-feasibility.md`).
- **Danh sách 50 mã**: chỉ hoàn chỉnh khi mọi mã đạt audit nguồn đã xác minh và bạn xác nhận phiên bản chính sách ngưỡng (`config/universe-policy.json`).
- **Lịch giao dịch**: đã có lịch 2026 (`config\trading-calendar-hose-2026.json`); thêm lịch năm sau khi HOSE công bố.
- **AI**: chính sách mẫu chưa duyệt, ngân sách 0 USD. Muốn bật: tạo key OpenRouter, chọn model có endpoint ZDR, đặt ngân sách, chạy bộ đánh giá (`docs/verification/model-evaluation.md`).
- **Quy tắc giao dịch**: lô, bước giá, biên độ, thuế đã ghi kèm căn cứ (`docs\decisions\market-rules.md`); T+2 mới có nguồn thứ cấp. Khuyến nghị gợi ý số lượng theo lô nhưng bạn vẫn xác nhận trước khi đặt lệnh.

## 6. Lịch, sao lưu, dừng

- Lịch: `scripts\windows\register-tasks.ps1` (xem kế hoạch) → `-Register` khi đã có `.env.local`, lịch giao dịch và múi giờ UTC+07. Máy tắt thì không bảo đảm đúng giờ; lần bật sau chạy bù phiên gần nhất.
- Sao lưu: `.\.venv\Scripts\python.exe -m investment_agent.cli backup --data-dir data --backup-dir backups --kind daily`. Khôi phục theo `docs/operations/backup-and-recovery.md`.
- Dừng lịch/AI/Telegram: xem `docs/operations/windows.md` mục "Dừng".
