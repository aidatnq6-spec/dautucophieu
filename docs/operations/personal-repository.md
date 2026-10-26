# Kho dữ liệu cá nhân có phiên bản

Firestore là nguồn sự thật; SQLite chỉ lưu bản sao có thể bỏ đi. Task 7 chưa thêm endpoint ghi dữ liệu chung: các domain service ở task sau phải kiểm tra hồ sơ, khảo sát và sổ trước khi gọi repository. Không dùng MemoryDocumentStore trong cấu hình thật.

## Hợp đồng repository

`PersonalRepository(owner_uid, store)` yêu cầu `OwnerContext` đã được middleware Task 6 xác minh; kiểm tra UID cấu hình và role owner trước mọi truy cập store/cache. Admin SDK bỏ qua Firestore Rules nên kiểm tra này là bắt buộc.

- `read(context, collection, record_id, version=None)`: đọc phiên bản hiện tại hoặc revision lịch sử; không có record/version trả None.
- `write(..., expected_version, request_id)`: tạo revision bất biến. Lần đầu dùng expected_version=0. Sai phiên bản trả VersionConflict; request_id trùng với cùng nội dung trả revision đã commit, kể cả khi đã có revision mới hơn. Cùng request_id khác record/payload/expected_version trả IdempotencyConflict.
- `require_current(context, versions)`: đọc các head trong cùng transaction và so sánh đúng phiên bản đầu vào. Không dùng cache. Đây là kiểm tra tại thời điểm đọc, **không phải khóa publish**; Task 26 phải kiểm tra phiên bản trong chính transaction publish để tránh thay đổi giữa kiểm tra và ghi báo cáo.

Payload là JSON không float; số Decimal truyền chuỗi theo hợp đồng tiền. Chặn các tên trường bí mật đã biết, kể cả trong object con; không lưu credentials trong settings. Domain/schema cụ thể sẽ tiếp tục giới hạn trường khi thêm tính năng. Không dùng secret scanner này làm bộ lọc toàn văn tài liệu.

## Namespace và transaction

```text
owners/{uid}/{collection}/{hash(collection,record_id)}-v{version}
owners/{uid}/record_heads/{hash(collection,record_id)}
owners/{uid}/mutation_requests/{request_id}
```

Các collection được phép: profile_versions, risk_versions, ledger_events, approvals, valuation_assumptions, reports, settings, journal. Mỗi mutation đọc request record và head trước; sau đó tạo revision, cập nhật head và tạo request record trong một Firestore transaction. Request ID thuộc namespace owner, dùng cho một mutation duy nhất. Không đặt TTL xóa request record trong bản này vì sẽ làm thay đổi ý nghĩa retry.

Version ở Task 7 có phạm vi từng record. Khi sổ có nhiều event, Task 11 phải tạo phiên bản aggregate/transaction phù hợp để bảo đảm quy tắc tồn kho và thứ tự trên toàn sổ; không suy CAS một record thành CAS toàn danh mục.

`firestore.indexes.json` chưa có composite index vì chưa dùng query xuyên trường; bỏ index payload cho bảy collection để tránh index dữ liệu lồng không cần thiết. Chưa deploy index hoặc Rules lên project thật.

## Cache và mất kết nối

`PersonalCache(Path(...))` dùng SQLite riêng, ví dụ `data/personal-cache.sqlite`, không thay schema catalog thị trường. Chỉ lưu sau read/write thành công từ remote. Cache giữ owner, collection, record ID, version, payload và thời điểm kiểm chứng. Không ghi lùi phiên bản nếu một retry cũ về sau lần cập nhật mới.

`CachedPersonalRepository.read` trả PersonalView với `stale` và `verified_at`. Mất Firestore cho đọc bản đã lưu với stale=true; không có cache thì báo unavailable. Mutation không thành công trên Firestore không được ghi cache hoặc xếp hàng offline. require_current không fallback nên không cấp phép khuyến nghị cá nhân mới từ cache. Lỗi cache không biến một remote write đã commit thành thất bại nghiệp vụ; retry dùng cùng request_id để khôi phục kết quả.

File cache chứa dữ liệu tài chính cá nhân, giữ trong data được Git bỏ qua; giới hạn quyền truy cập Windows theo tài khoản máy. Đây chưa phải backup; Task 29 phải xuất Firestore cùng metadata để khôi phục nguồn sự thật.

## Tạm hoãn private key

Người dùng đang tạm hoãn cấu hình FIREBASE_PRIVATE_KEY. Có thể triển khai và chạy test synthetic/fake như bình thường. Không đổi runtime để bỏ xác thực; không chuyển dữ liệu cá nhân sang local làm nguồn sự thật.

Factory `personal_repository_from_env()` chỉ đọc biến môi trường tiến trình, không tự đọc `.env.local` và không gọi factory khi import module. Thiếu cấu hình hoặc key không hợp lệ trả lỗi an toàn. Production từ chối emulator settings. Dùng Firebase Admin Python 7.7.0, khóa dependencies trong requirements.lock.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/repositories/test_personal_repository.py backend/tests/repositories/test_firestore_adapter.py -q
```

Integration emulator là opt-in, không yêu cầu private key. Khởi chạy emulator Firestore riêng trên 127.0.0.1 với project `demo-investment-agent-tests`, rồi chạy:

```powershell
$env:INVESTMENT_AGENT_TEST_FIRESTORE_EMULATOR='127.0.0.1:8080'
.\.venv\Scripts\python.exe -m pytest backend/tests/repositories/test_firestore_emulator.py -q
```

Test từ chối host ngoài loopback, dùng AnonymousCredentials và project demo cố định; chỉ dọn namespace UUID tạo riêng trong test đó. Không đặt biến này cho project thật. Nếu chưa có emulator, test báo skipped; không coi fake/spy PASS là SDK integration đã qua.

Tham chiếu: [Firestore transactions](https://firebase.google.com/docs/firestore/manage-data/transactions), [Firebase Admin setup](https://firebase.google.com/docs/admin/setup). Đọc tài liệu và cài dependency không đồng nghĩa đã kết nối project của người dùng.
