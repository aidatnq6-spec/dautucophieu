# Vận hành trên Windows

Ứng dụng chạy cục bộ, chỉ nghe trên `127.0.0.1`. Không mở cổng ra Internet.

## Khởi động

1. Kiểm tra môi trường: `powershell -ExecutionPolicy Bypass -File scripts\windows\doctor.ps1`.
2. Tạo `.env.local` ở gốc kho từ `.env.example` (Git bỏ qua). Điền Firebase, `INTERNAL_API_TOKEN`, `INTERNAL_API_HMAC_SECRET`, `APP_ORIGIN=http://127.0.0.1:3000`, và tùy chọn `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`. Không dán giá trị vào hội thoại hay tài liệu.
3. Build giao diện một lần: `npm --prefix apps/web run build`.
4. Chạy `scripts\windows\start-app.ps1`: khởi động API Python (cổng 8000) và Next.js (cổng 3000) trong cửa sổ ẩn. Script từ chối chạy nếu còn biến `INVESTMENT_E2E_AUTH`. Dừng bằng `scripts\windows\stop-app.ps1` (trả mã 0 cả khi tiến trình con của Python đã tự tắt theo tiến trình cha).

Dữ liệu cục bộ (`data\jobs.sqlite`, `data\deliveries.sqlite`, cache) nằm trong `data\`, Git bỏ qua. Firestore vẫn là nguồn sự thật của dữ liệu cá nhân.

Tùy chọn: cài Tesseract kèm dữ liệu tiếng Việt để đọc báo cáo ngân hàng dạng scan (xem README). `doctor.ps1` báo có hay chưa; không có thì file scan được báo "chưa cài Tesseract" và nhập tay.

## Lịch sau phiên

`scripts\windows\run-after-close.ps1` gọi `python -m investment_agent.cli scheduled-run` một lần:

- Giờ Việt Nam: 15:30 chạy phiên hôm nay; 20:00 chỉ chạy lại khi phiên đó chưa có bản tin đã phát hành (dữ liệu về muộn). Tối đa 2 lần cho một phiên. Bản tin chỉ phát hành khi mọi mã đang nắm có giá của đúng phiên đó; nguồn chưa cập nhật lúc 15:30 thì để khung sau.
- 08:30 sáng chỉ chạy bù phiên trước nếu phiên đó chưa có bản tin (ví dụ máy tắt buổi tối); không tạo bản tin mới cho phiên chưa giao dịch.
- Ngày nghỉ/cuối tuần không tạo phiên mới. Bản tuần/tháng tạo ở phiên giao dịch cuối của tuần/tháng theo lịch.
- Máy bật lại sau khi bỏ lỡ: chỉ chạy bù phiên gần nhất chưa có bản tin, đếm số phiên cũ bị bỏ lỡ; không gửi hàng loạt bản tin cũ.
- Khóa lease trong `data\jobs.sqlite` chặn hai tiến trình chạy cùng lúc.
- Telegram chỉ gửi tự động khi trong Cài đặt đã bật cả "Cho phép gửi" và "Gửi tự động theo lịch".

### Các bước tự động khác

Mỗi bước ghi một dòng `<thời điểm> <tên bước> exit=<mã>` vào `logs\scheduler.log`. Một bước lỗi không chặn các bước sau. Các bước mới nhất:

| Lệnh | Khi nào | Làm gì | Dữ liệu |
|---|---|---|---|
| `valuation-check-sync` | Từ lượt 20:00 | Đọc vốn hoá, P/E, P/B, số cổ phiếu của các mã theo dõi từ VNDirect để đối chiếu | `data\valuation-check\` |
| `bank-notes-sync` | Từ lượt 20:00, mỗi ngân hàng một lần một tuần | Đọc thuyết minh Vietcap (nợ theo nhóm, tiền gửi theo loại, CAR), mỗi lượt gọi cách nhau 10 giây; nguồn từ chối thì dừng, không thử lại | `data\bank-notes\` |
| `drawdown-check` | Mỗi lượt | Lấy toàn bộ lịch sử giá một lần cho mỗi mã, cả mã cũ; nhắc khi mã đang nắm giảm quá ngưỡng so với giá vốn | `data\trend-sources\`, mã không có giá ghi ở `_no_prices.json` |
| `lights-check` | Mỗi lượt | Báo Telegram khi một chỉ báo của Bảng đèn đổi màu; màu thấy lần đầu chỉ được ghi nhớ | `data\alerts\lights.json` |
| `backup-drill` | Mỗi lượt, tự bỏ qua nếu chưa đủ 7 ngày | Khôi phục bản sao lưu mới nhất vào thư mục tạm rồi xóa | `data\alerts\restore-drill.json` |
| `health-check` | Mỗi lượt và trong tác vụ `InvestmentAgent-Alerts` | Xem mục Tình trạng hệ thống bên dưới | `data\alerts\system-health.json` |

### Tình trạng hệ thống

`health-check` chỉ đọc tên bước và mã thoát trong nhật ký, không đọc nội dung bước in ra. Xem kết quả ở trang Cài đặt. Mỗi vấn đề được báo Telegram một lần và báo lại khi hồi phục. Các trường hợp bị coi là vấn đề:

- Một bước lỗi từ 2 lần liên tiếp.
- Lượt sau phiên gần nhất đã xong quá 2 ngày, hoặc nhật ký chưa có lượt nào.
- Dữ liệu cũ hơn hạn: giá VN-Index, Xu hướng 6 ngày; Vĩ mô, Lịch sự kiện 3 ngày; báo cáo Vnstock, báo cáo VNDirect, chỉ số ngành, đối chiếu định giá 4 ngày; thuyết minh ngân hàng 10 ngày.
- Diễn tập khôi phục thất bại, chưa chạy lần nào, hoặc lần gần nhất quá 14 ngày.

`health-check` cũng chạy trong `InvestmentAgent-Alerts` (09:00, 5 phút một lần, trong 6 giờ 5 phút, cùng `price-alerts` và `thesis-check --scope price`), nên vẫn phát hiện được khi lịch sau phiên ngừng chạy.

### Lịch giao dịch

Lịch tự động dùng `data\trading-calendar.json` nếu có, nếu không thì `config\trading-calendar-hose-<năm hiện tại>.json` (đã có năm 2026, xem `docs\decisions\market-rules.md`). Định dạng khi tự lập:

```json
{"version": "hose-2026", "source": "<đường dẫn thông báo chính thức>", "holidays": ["2026-09-02"], "first": "2026-01-02", "last": "2026-12-31"}
```

Thiếu file hoặc `source` rỗng/`synthetic` thì lệnh thoát mã 2 và không chạy gì. Mỗi năm cần thêm lịch mới khi HOSE công bố.

### Đăng ký tác vụ

```powershell
scripts\windows\register-tasks.ps1            # chỉ hiển thị kế hoạch
scripts\windows\register-tasks.ps1 -Register  # đăng ký cho người dùng hiện tại
scripts\windows\register-tasks.ps1 -Unregister
```

Đăng ký yêu cầu `.env.local`, lịch giao dịch năm hiện tại và múi giờ máy UTC+07. Tác vụ dùng đường dẫn tuyệt đối, không truyền token qua tham số, chạy ẩn, `StartWhenAvailable` để chạy bù, và không sửa tác vụ khác. Máy tắt hoặc ngủ thì không bảo đảm đúng giờ.

Nhật ký: `logs\scheduler.log` chỉ ghi thời điểm, mã thoát và tóm tắt JSON (không có bí mật hay số liệu cá nhân).

### Tự cập nhật ứng dụng

Tác vụ `InvestmentAgent-Update` (đăng ký cùng `register-tasks.ps1 -Register`) chạy `scripts\windows\update-app.ps1` 10 phút một lần và khi đăng nhập. Khi `main` trên GitHub có commit mới: kéo về (chỉ fast-forward), cài lại thư viện nếu `backend/requirements.lock`, `backend/pyproject.toml` hoặc `apps/web/package-lock.json` đổi, build giao diện, rồi khởi động lại API và web bằng `start-app.ps1`.

- Chỉ chạy khi thư mục đang ở nhánh `main` và không có thay đổi chưa commit; đang làm trên nhánh khác thì bỏ qua.
- Build lỗi thì quay về commit trước, build lại và khởi động bản đó.
- Nhật ký: `logs\update.log`, một dòng mỗi lần có cập nhật, bỏ qua hoặc lỗi.

## Dừng

- Dừng lịch: `register-tasks.ps1 -Unregister`.
- Dừng Telegram: tắt "Cho phép gửi" trong Cài đặt hoặc xóa `TELEGRAM_BOT_TOKEN`.
- Dừng AI: giữ chính sách AI ở trạng thái chưa duyệt hoặc xóa `OPENROUTER_API_KEY`.
- Dừng ứng dụng: kết thúc tiến trình `python.exe` (investment_agent.api.app) và `node.exe` (next start) trong Task Manager.
