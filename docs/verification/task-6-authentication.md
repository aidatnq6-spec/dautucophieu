# Task 6 — xác thực và API nội bộ

Ngày: 25/10/2026. Branch: `feat/investment-agent`; base: `554d3e9`.

## Phạm vi thực hiện

- Firebase Admin SDK 14.5.0 phía Next.js: UID owner duy nhất, Google provider, đăng nhập mới trong 5 phút, verify token và session với revocation check.
- Cookie phiên HttpOnly 5 ngày; CSRF token 1 giờ; Origin/Host chặt; Secure theo HTTPS, chỉ cho HTTP loopback.
- API session/CSRF/logout và `/api/account` kiểm chứng identity qua Python, không có proxy URL tùy ý. Logout revoke rồi xóa cookie, lỗi không lộ token hoặc nội dung exception.
- Bearer + HMAC v1 ràng buộc UID/role/correlation/timestamp/nonce/method/target/body. Chống replay trong cửa sổ 60 giây, một tiến trình.
- FastAPI mặc định private; chỉ GET health công khai, không docs/OpenAPI, bind loopback. Firestore client Rules deny all; chưa deploy.

## Bằng chứng kiểm thử

Đã quan sát test RED do module chức năng chưa tồn tại; sau triển khai test GREEN. Một lỗi tích hợp phát hiện NextRequest chuẩn hóa 127.0.0.1 thành localhost; sửa để kiểm tra Host thực tế theo APP_ORIGIN, vẫn so khớp Origin mutation chính xác. Không nới kiểm tra sang chấp nhận mọi nguồn loopback.

| Kiểm tra | Kết quả |
| --- | --- |
| `python -m pytest backend/tests -q` | PASS, 99 test (30 API auth) |
| `npm.cmd --prefix apps/web run test -- --run` | PASS, 36 test |
| `npm.cmd --prefix apps/web run typecheck` | PASS |
| `npm.cmd --prefix apps/web run lint` | PASS |
| `npm.cmd --prefix apps/web run build` | PASS, 3 API routes động |
| TypeScript signer → Python HTTP loopback | PASS: GET hợp lệ, replay/tampering bị chặn; POST UTF-8 body hợp lệ đến routing 405, sửa body bị 401 |
| Firebase project thật / Auth emulator | not_run, chưa cấu hình project/credentials; không có runtime bypass |
| Firestore Rules deploy / emulator Rules tests | not_run; chưa có Firestore repository, tiếp tục Task 7 |
| Google sign-in UI/browser | not_run; thuộc Task 24, Task 6 chỉ có server API |

Build và test không cần key thật; chưa tạo Firebase resource hoặc gửi dữ liệu cá nhân. Còn cảnh báo deprecation Starlette TestClient dùng httpx trong dependency hiện đã khóa; test vẫn PASS. Môi trường Node kiểm chứng vẫn là phiên bản sẵn có đã ghi trong README, chưa chứng minh Node 24.

## Rà soát độc lập

Reviewer đọc implementation/tests và biên quyền của Task 6: không có Critical/Important. Hai mục Minor chưa sửa trong task này:

1. Body limit được kiểm tra sau khi đọc trọn request vào RAM; nên giới hạn trong quá trình streaming trước khi mở rộng môi trường vận hành.
2. Lỗi Firebase khi xác minh session, kể cả mạng/dịch vụ, hiện trả 401 chung. Vẫn chặn truy cập nhưng có thể khiến người dùng hiểu nhầm là phiên hết hạn. Nên phân biệt lỗi unavailable với invalid/revoked.

Không coi kiểm thử adapter giả lập là bằng chứng Firebase thật. Không gọi Task 6 đã nghiệm thu live; phần triển khai và kiểm tra cục bộ đã hoàn tất. Task 7 phải dùng owner context trong repository vì Admin SDK bỏ qua Rules. Hướng dẫn: [authentication.md](../operations/authentication.md).
