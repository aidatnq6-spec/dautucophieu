# Sao lưu và khôi phục

## Nội dung một bản sao lưu

`python -m investment_agent.cli backup --data-dir data --backup-dir backups --kind daily` tạo `backups\<thời điểm UTC>-daily\`:

- `data\*.sqlite`: chép bằng SQLite backup API nên nhất quán kể cả khi có tiến trình đang ghi (WAL); chỉ chứa dữ liệu đã commit.
- `data\prices\<mã>\manifest.json` và các tệp Parquet revision; tài liệu trong `data\documents` (pdf/html/json).
- `personal-export.json`: toàn bộ bản ghi cá nhân trong Firestore dưới `owners/{uid}` (hồ sơ, khảo sát, sổ, phê duyệt, giả định, bản tin, cài đặt, bản ghi idempotency) kèm `owner_uid`, `schema`, `export_version`, thời điểm xuất.
- `manifest.json`: SHA-256 và kích thước từng tệp.

Danh sách theo dõi `market-symbols.txt` được sao lưu (từ 09/11/2026) vì sửa tay và không tải lại được.

Không bao giờ chép: `.env*`, log, khóa, tệp ngoài allowlist. Thiếu kết nối Firestore thì lệnh dừng (mã 2): chỉ sao chép cache cục bộ không được coi là sao lưu đầy đủ. Bản sao lưu chứa dữ liệu tài chính cá nhân: giữ trong `backups\` (Git bỏ qua), giới hạn quyền tài khoản Windows; ứng dụng không tự tải lên nơi khác.

## Mã hóa

Từ 09/11/2026, vì bản sao lưu được chép lên đám mây hoặc ổ ngoài, `personal-export.json`, các tệp SQLite và `market-symbols.txt` chỉ được ghi dưới dạng `.enc` (AES-256-GCM, mỗi tệp gắn với vị trí của nó). Giá thị trường, tài liệu công khai và `manifest.json` không mã hóa. Kiểm tra checksum không cần khóa.

- Khóa là `BACKUP_ENCRYPTION_KEY` trong `.env.local`, không bao giờ nằm trong bản sao lưu. **Mất khóa thì không mở được các bản đã mã hóa**: giữ một bản ở trình quản lý mật khẩu, tách khỏi nơi chứa bản sao lưu.
- Thiếu khóa hoặc khóa sai định dạng: lệnh `backup` dừng (mã 2, `backup_key_missing`), không ghi bản rõ.
- Tạo khóa mới: `python -c "from investment_agent.operations.backup import generate_key; print(generate_key())"`. Khóa mới không mở được bản cũ.
- Bản cũ chưa mã hóa vẫn khôi phục được bình thường.

## Sao lưu tự động

Tác vụ lịch `InvestmentAgent-AfterClose` gọi `backup --kind auto` sau mỗi lần chạy. Lệnh tự quyết định có cần sao lưu không: tối đa một bản mỗi ngày (giờ Việt Nam), từ 20:00 để có bản tin của ngày; nếu máy tắt lúc 20:00 thì lần chạy kế tiếp sao lưu bù khi bản gần nhất đã quá 24 giờ. Bản đầu tiên và mỗi 7 ngày một lần là `weekly`, còn lại `daily`; bản `manual` không được tính. Không đến hạn thì ghi `skipped` vào `logs\scheduler.log` và không đọc Firestore.

Giữ lại 7 bản `daily` và 4 bản `weekly` mới nhất; bản `manual` không tự xóa. Việc xóa chỉ áp dụng cho thư mục nằm trực tiếp trong thư mục sao lưu đã resolve, không theo symlink/junction ra ngoài.

## Khôi phục

1. Kiểm tra: `verify_backup` so checksum; sai một tệp là dừng.
2. Dữ liệu cục bộ: `restore_local(<bản sao lưu>, <thư mục mới rỗng>)`, rồi trỏ `INVESTMENT_DATA_DIR` sang thư mục đó sau khi kiểm tra. Không khôi phục đè lên thư mục đang dùng.
3. Firestore: `preview_personal_restore` cho số bản ghi sẽ tạo, trùng khớp và xung đột. `restore_personal(..., confirm=True)` chỉ tạo bản ghi còn thiếu; nếu có bản ghi hiện tại khác bản sao lưu (dữ liệu mới hơn) thì từ chối toàn bộ để chủ sở hữu tự xử lý — không ghi đè im lặng. Bản xuất của chủ sở hữu khác bị từ chối.

## Diễn tập

`backend/tests/operations/test_recovery.py` diễn tập trên dữ liệu tổng hợp: sao lưu khi có giao dịch SQLite chưa commit, loại bí mật/log, từ chối bản bị sửa, khôi phục vào thư mục mới, khôi phục Firestore vào kho rỗng khớp dữ liệu gốc, từ chối ghi đè dữ liệu mới, giới hạn giữ bản. Khôi phục vào Firestore thật **chưa diễn tập**.

### Diễn tập tự động

Từ 09/11/2026, lệnh `backup-drill` chạy trong lịch sau phiên và tự bỏ qua nếu lần trước chưa đủ 7 ngày. Lệnh khôi phục bản sao lưu mới nhất vào thư mục tạm (so checksum), đọc thử `personal-export.json`, rồi xóa thư mục tạm. Kết quả ở `data\alerts\restore-drill.json`, chỉ gồm thời điểm, tên bản sao lưu, số tệp và loại lỗi.

Lệnh còn khôi phục dữ liệu cá nhân của bản sao lưu vào một kho tạm trong bộ nhớ rồi so với Firestore đang dùng, chỉ giữ lại số đếm. Mọi bản ghi trong bản sao lưu phải còn nguyên; chỉ phiên bản hiện hành của một bản ghi được phép mới hơn. Thiếu, khác nội dung, lùi phiên bản hoặc con trỏ không có bản ghi thì diễn tập thất bại (`PersonalMismatch`). Không kết nối được Firestore thì ghi `unavailable`, không kết luận bản sao lưu hỏng. Chạy ngay ngoài lịch: `python -m investment_agent.cli backup-drill --data-dir data --force`.

Phạm vi: diễn tập **không** ghi vào Firestore, nên chưa thử bước ghi ngược lên Firestore thật; muốn thử cần một dự án Firebase riêng. Khi diễn tập hỏng hoặc quá 14 ngày chưa chạy, `health-check` sẽ báo (xem `windows.md`).

## Nhật ký tác vụ

`JobLogger` ghi JSON lines chỉ gồm `time`, `phase`, `count`, `error_code` (đã che bí mật). Không có trường văn bản tự do nên không ghi prompt, số tiền hay dữ liệu cá nhân.
