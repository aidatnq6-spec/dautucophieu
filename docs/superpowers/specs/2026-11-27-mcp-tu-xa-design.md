# MCP dữ liệu công khai từ xa (claude.ai web và điện thoại)

Chủ sở hữu duyệt ngày 27/11/2026: dùng các công cụ dữ liệu công khai từ claude.ai trên web và ứng dụng điện thoại, khi không ở cạnh máy. Server stdio ([2026-11-26-mcp-du-lieu-cong-khai-design.md](2026-11-26-mcp-du-lieu-cong-khai-design.md)) chỉ Claude Desktop/Claude Code trên máy gọi được.

## Thay đổi so với spec 26/11

Spec 26/11 ghi "không mở cổng mạng". Từ 27/11/2026 có thêm một đường vào từ Internet, chỉ cho bộ công cụ công khai, qua Tailscale Funnel; bản stdio giữ nguyên.

## Cách làm

| | Cách | Được | Mất |
|---|---|---|---|
| **Tailscale Funnel (chọn)** | Đường hầm Tailscale, địa chỉ `…ts.net` cố định | Miễn phí, không cần tên miền | Phụ thuộc Tailscale; máy phải bật |
| Cloudflare Tunnel | Đường hầm Cloudflare | Nhiều lớp bảo vệ | Cần tên miền riêng (chưa có) |
| Đường hầm tạm Cloudflare | Không tài khoản | Nhanh | Địa chỉ đổi mỗi lần khởi động |

Bảo vệ: **đường dẫn bí mật + giới hạn tần suất** (chọn) thay vì OAuth: dữ liệu chỉ là thị trường công khai; lộ đường dẫn thì đổi chuỗi bí mật.

## Thiết kế

1. `python -m investment_agent.mcp_remote`: cùng `build_server` với bản stdio, HTTP (streamable, không giữ phiên) trên `127.0.0.1:8770`; chỉ trả lời ở `/<bí mật>/mcp` (và `/<bí mật>/healthz` cho kiểm tra trên máy); đường dẫn khác 404. Chặn tên máy lạ (chỉ `127.0.0.1`, `localhost` và tên `…ts.net` trong `MCP_REMOTE_HOST`). Tối đa 120 lượt gọi mỗi phút, quá thì 429.
2. Bí mật `MCP_REMOTE_SECRET` (≥ 32 ký tự ngẫu nhiên) và `MCP_REMOTE_HOST` trong `.env.local`, không vào Git; không có bí mật thì không chạy. `--new-secret` tạo chuỗi mới ghi vào `.env.local` mà không in ra; `--url` in địa chỉ connector cho chủ sở hữu tự chép.
3. Tác vụ Windows `InvestmentAgent-McpRemote` chạy khi đăng nhập, tự chạy lại khi dừng.
4. Tình trạng hệ thống: khi có `MCP_REMOTE_SECRET`, dòng "Kết nối từ xa" báo khi `/<bí mật>/healthz` trên máy không trả lời.
5. Hướng dẫn cài Tailscale, bật Funnel, thêm connector trên claude.ai ở `docs/operations/mcp-tu-xa.md`.

## Không làm

- Không thêm công cụ, không chạm kho cá nhân, không liệt kê mã theo dõi.
- Không OAuth; không mở cổng trên mạng LAN.
