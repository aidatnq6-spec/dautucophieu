# Xác thực cá nhân và API loopback

Task 6 chỉ thiết lập biên xác thực. Form đăng nhập Google thuộc luồng UI sau này; chưa có sổ Firestore hoặc endpoint nghiệp vụ tài chính. Không cần credentials để chạy unit tests.

## Cấu hình cục bộ

- Firebase: bật Google sign-in trong project của người dùng; cấu hình đúng authorized domain. `FIREBASE_OWNER_UID` là UID duy nhất được cho phép, không phải email. Token của phương thức đăng nhập khác bị từ chối.
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`: credentials phía máy chủ; private key nhận newline thật hoặc `\\n`. Không đưa vào biến `NEXT_PUBLIC_*`, Git hoặc hội thoại. Next.js dùng Admin SDK cho Auth; Firestore Admin chỉ được thêm ở repository Python trong Task 7.
- `APP_ORIGIN`: ví dụ `http://127.0.0.1:3000`, không có dấu `/` cuối. Phải khớp chính xác địa chỉ truy cập và Host header. Chỉ cho localhost/127.0.0.1/::1. HTTP loopback cho phép cookie không Secure; HTTPS luôn đặt Secure. Không triển khai công khai với cấu hình này.
- `PYTHON_API_ORIGIN`: `http://127.0.0.1:8000`. Chỉ hỗ trợ HTTP tại địa chỉ IPv4 loopback này; không URL tùy ý, không redirect.
- `INTERNAL_API_TOKEN` và `INTERNAL_API_HMAC_SECRET`: hai giá trị ASCII khác nhau, ít nhất 32 ký tự, sinh ngẫu nhiên riêng (nên dùng 32 byte random mã hóa hex). Cấu hình cùng giá trị tương ứng ở Next.js và Python, không truyền trong command line hay qua trình duyệt.

Next.js đọc cấu hình từ môi trường tiến trình hoặc `.env.local` nằm trong `apps/web`. Python đọc môi trường tiến trình, chưa tự tải `.env`. `.env.example` ở gốc chỉ là danh sách biến. Không copy tệp bí mật vào hồ sơ kiểm chứng.

Khởi động sau khi cấu hình môi trường, từ gốc worktree:

```powershell
.\.venv\Scripts\python.exe -m investment_agent.api.app
npm.cmd --prefix apps/web run dev
```

Lệnh Python bind `127.0.0.1:8000`, một worker, tắt proxy headers và access log. Không chạy nhiều worker hoặc bind `0.0.0.0`: bộ chống replay hiện giữ nonce trong RAM của một tiến trình. Nonce không sống qua restart; cửa sổ chữ ký tối đa 60 giây mỗi phía. Nếu sau này cần nhiều worker, bổ sung kho nonce dùng chung trước khi đổi mô hình chạy.

## Hợp đồng HTTP cho UI

1. `GET /api/session` trả `{csrfToken}` và đặt cookie `investment_csrf` HttpOnly, SameSite Strict, hết hạn sau một giờ. Frontend giữ token trả về trong bộ nhớ, không đọc cookie HttpOnly.
2. Đăng nhập Google qua Firebase client với persistence trong bộ nhớ/không lưu lâu dài; lấy ID token. Gửi `POST /api/session` với JSON `{idToken}`, `Content-Type: application/json`, `X-CSRF-Token` vừa nhận. Trình duyệt tự gửi Origin và cookies cùng nguồn. Máy chủ xác minh token/revocation, UID, Google provider và `auth_time` trong 5 phút trước tạo cookie phiên 5 ngày; không trả cookie/token qua JSON. Sau đó đăng xuất Firebase client để chỉ dùng phiên máy chủ.
3. `GET /api/account` xác minh lại cookie với revocation check trước gọi `/internal/identity`. Đây là endpoint xác nhận cầu nối, chỉ trả UID/role/correlation ID. Chưa trả hồ sơ hay dữ liệu đầu tư.
4. `POST /api/logout` yêu cầu cùng Origin và CSRF, xác minh phiên rồi revoke refresh tokens của owner; xóa hai cookie. Nếu Firebase không thể revoke, trả lỗi 503 và vẫn xóa cookie cục bộ; không tuyên bố phiên trên thiết bị khác đã được thu hồi.

Mọi phản hồi xác thực đặt `Cache-Control: no-store`. Không có CORS hoặc đường chuyển tiếp URL tùy ý. Đường thay đổi nghiệp vụ sau này phải dùng `assertMutation` trước hành động; mọi API cá nhân phải dùng `verifyOwnerSession`, không chỉ kiểm tra cookie có tồn tại. Chưa có private page cần guard ở Task 6; layout UI riêng phải xác minh phiên khi được thêm.

## Chữ ký nội bộ v1

Bearer token riêng và HMAC-SHA256 riêng. Canonical UTF-8, nối bằng LF, không LF cuối:

```text
v1
timestamp Unix giây nguyên
nonce random 16 byte, 32 hex thường
UID đã được xác minh
owner
correlation ID do máy chủ tạo
HTTP method chữ hoa
raw path kèm ?query nếu có
SHA256 hex thường của nguyên bytes request body
```

Headers: `Authorization`, `X-Owner-Uid`, `X-Owner-Role`, `X-Correlation-Id`, `X-Request-Timestamp`, `X-Request-Nonce`, `X-Request-Signature`. Next.js không chuyển header nhận dạng do browser gửi. Python kiểm tra loopback peer, owner, role, thời gian ±60 giây, chữ ký và nonce trước handler. Ngoại lệ công khai duy nhất là `GET /health` trả `{"status":"ok"}`. Docs/OpenAPI bị tắt. Route Python mới tự được middleware bảo vệ; repository phải lấy `require_owner(request)` và kiểm tra owner namespace. Scheduler sau này gọi application service bằng owner cấu hình cục bộ, không giả header từ browser.

`firebase/firestore.rules` từ chối mọi read/write từ client. Chưa deploy rules. Admin SDK bỏ qua Rules: kiểm tra owner ở Task 7 vẫn bắt buộc.

## Bằng chứng và phần chưa chạy

Unit tests dùng auth adapter được inject khi gọi hàm kiểm thử, không có cờ bypass xác thực trong runtime. Runtime từ chối `FIREBASE_AUTH_EMULATOR_HOST` vì emulator không xác minh chữ ký production. Chưa kiểm thử Firebase thật hoặc emulator integration; chưa có project/credentials cấu hình cho lượt này. Không phát hành khả năng đăng nhập thật đã được kiểm chứng cho đến khi thử token Google owner, tài khoản khác, revoke và expiry trên project riêng. Tham chiếu: [Firebase session cookies](https://firebase.google.com/docs/auth/admin/manage-cookies), [Admin setup](https://firebase.google.com/docs/admin/setup), [Firestore server access](https://firebase.google.com/docs/firestore/security/rules-conditions).
