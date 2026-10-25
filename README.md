# Investment Agent

Ứng dụng cá nhân chạy trên Windows để quản lý hồ sơ tài chính, sổ đầu tư và nghiên cứu cổ phiếu HOSE, tạo bản tin sau phiên trong ứng dụng và (tùy chọn) Telegram. Không đặt lệnh chứng khoán.

**Trạng thái (2026-10-25): bản thử nghiệm đã hoàn tất mã và kiểm thử tự động trên dữ liệu tổng hợp. Chưa phải công cụ phân tích thật:** chưa kết nối nguồn dữ liệu thị trường được phép dùng, chưa có danh sách 50 mã đã kiểm chứng, và Firebase/Telegram/OpenRouter chưa được chạy live. Xem [bàn giao bản thử nghiệm](docs/verification/trial-release.md).

## Có gì

- Hồ sơ tài chính → vốn có thể đầu tư có bảng tính được duyệt; khảo sát 13 câu có cờ khả năng tài chính.
- Phân bổ cơ sở 0/10/25/35/50/60%, ngoại lệ tối đa 90% với điều kiện đầy đủ.
- Sổ giao dịch Decimal: bình quân gia quyền, phí/thuế thực tế, cổ tức tiền/cổ phiếu, quyền chờ về, sửa/hủy/khôi phục, đối chiếu hiệu quả.
- Danh sách nghiên cứu cần duyệt; giá/tài chính theo thời điểm; DCF/DDM/thu nhập thặng dư/NAV/chu kỳ với giả định được duyệt; khuyến nghị kiểm tra ràng buộc.
- AI qua OpenRouter (tắt mặc định): payload không chứa số tiền cá nhân, công cụ chỉ đọc, kiểm tra đầu ra, dự phòng không AI.
- Bản tin sau phiên lưu một lần cho mỗi bộ dữ liệu đầu vào; Telegram có trạng thái gửi từng phần; lịch Windows có chạy bù; sao lưu/khôi phục.

## Bắt đầu

- Hướng dẫn từ máy sạch: [docs/operations/personal-trial-guide.md](docs/operations/personal-trial-guide.md)
- Vận hành, lịch, dừng dịch vụ: [docs/operations/windows.md](docs/operations/windows.md)
- Sao lưu và khôi phục: [docs/operations/backup-and-recovery.md](docs/operations/backup-and-recovery.md)
- Xác thực và API nội bộ: [docs/operations/authentication.md](docs/operations/authentication.md)

## Runtime

Node 24 LTS (đã kiểm với 25.9.0), npm 11, Git 2, CPython 3.11 64-bit. Dùng `npm.cmd` trên Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e backend
npm.cmd --prefix apps/web ci
npx.cmd --prefix apps/web playwright install chromium
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\doctor.ps1
```

## Kiểm tra

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\verify.ps1
```

Chạy backend pytest, web typecheck, lint, unit test, build và Playwright e2e (backend fixture tổng hợp, xác thực kiểm thử chỉ hoạt động dưới `next dev`). Kết quả chi tiết: [ma trận nghiệm thu](docs/verification/acceptance-matrix.md). Kiểm chứng live còn lại: [checklist](docs/verification/live-data-checklist.md).

## Nguyên tắc dữ liệu

`.env.local`, `data\`, `backups\`, log và khóa không vào Git. Firestore là nguồn sự thật của dữ liệu cá nhân; SQLite/Parquet cục bộ giữ dữ liệu thị trường có phiên bản và cache. Fixture luôn gắn nhãn `synthetic`.
