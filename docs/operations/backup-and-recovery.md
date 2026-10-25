# Sao lưu và khôi phục

## Nội dung một bản sao lưu

`python -m investment_agent.cli backup --data-dir data --backup-dir backups --kind daily` tạo `backups\<thời điểm UTC>-daily\`:

- `data\*.sqlite`: chép bằng SQLite backup API nên nhất quán kể cả khi có tiến trình đang ghi (WAL); chỉ chứa dữ liệu đã commit.
- `data\prices\<mã>\manifest.json` và các tệp Parquet revision; tài liệu trong `data\documents` (pdf/html/json).
- `personal-export.json`: toàn bộ bản ghi cá nhân trong Firestore dưới `owners/{uid}` (hồ sơ, khảo sát, sổ, phê duyệt, giả định, bản tin, cài đặt, bản ghi idempotency) kèm `owner_uid`, `schema`, `export_version`, thời điểm xuất.
- `manifest.json`: SHA-256 và kích thước từng tệp.

Không bao giờ chép: `.env*`, log, khóa, tệp ngoài allowlist. Thiếu kết nối Firestore thì lệnh dừng (mã 2): chỉ sao chép cache cục bộ không được coi là sao lưu đầy đủ. Bản sao lưu chứa dữ liệu tài chính cá nhân: giữ trong `backups\` (Git bỏ qua), giới hạn quyền tài khoản Windows; ứng dụng không tự tải lên nơi khác.

## Sao lưu tự động

Tác vụ lịch `InvestmentAgent-AfterClose` gọi `backup --kind auto` sau mỗi lần chạy. Lệnh tự quyết định có cần sao lưu không: tối đa một bản mỗi ngày (giờ Việt Nam), từ 20:00 để có bản tin của ngày; nếu máy tắt lúc 20:00 thì lần chạy kế tiếp sao lưu bù khi bản gần nhất đã quá 24 giờ. Bản đầu tiên và mỗi 7 ngày một lần là `weekly`, còn lại `daily`; bản `manual` không được tính. Không đến hạn thì ghi `skipped` vào `logs\scheduler.log` và không đọc Firestore.

Giữ lại 7 bản `daily` và 4 bản `weekly` mới nhất; bản `manual` không tự xóa. Việc xóa chỉ áp dụng cho thư mục nằm trực tiếp trong thư mục sao lưu đã resolve, không theo symlink/junction ra ngoài.

## Khôi phục

1. Kiểm tra: `verify_backup` so checksum; sai một tệp là dừng.
2. Dữ liệu cục bộ: `restore_local(<bản sao lưu>, <thư mục mới rỗng>)`, rồi trỏ `INVESTMENT_DATA_DIR` sang thư mục đó sau khi kiểm tra. Không khôi phục đè lên thư mục đang dùng.
3. Firestore: `preview_personal_restore` cho số bản ghi sẽ tạo, trùng khớp và xung đột. `restore_personal(..., confirm=True)` chỉ tạo bản ghi còn thiếu; nếu có bản ghi hiện tại khác bản sao lưu (dữ liệu mới hơn) thì từ chối toàn bộ để chủ sở hữu tự xử lý — không ghi đè im lặng. Bản xuất của chủ sở hữu khác bị từ chối.

## Diễn tập

`backend/tests/operations/test_recovery.py` diễn tập trên dữ liệu tổng hợp: sao lưu khi có giao dịch SQLite chưa commit, loại bí mật/log, từ chối bản bị sửa, khôi phục vào thư mục mới, khôi phục Firestore vào kho rỗng khớp dữ liệu gốc, từ chối ghi đè dữ liệu mới, giới hạn giữ bản. Diễn tập với Firestore thật **chưa chạy** (chưa cấu hình khóa); `FirestoreDocumentStore.dump` chưa được kiểm chứng trên dự án thật.

## Nhật ký tác vụ

`JobLogger` ghi JSON lines chỉ gồm `time`, `phase`, `count`, `error_code` (đã che bí mật). Không có trường văn bản tự do nên không ghi prompt, số tiền hay dữ liệu cá nhân.
