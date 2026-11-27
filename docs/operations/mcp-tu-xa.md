# Dùng dữ liệu công khai từ claude.ai trên web và điện thoại

Claude Desktop và Claude Code trên máy này gọi server dữ liệu công khai trực tiếp (stdio). claude.ai trên web và ứng dụng điện thoại chạy trên máy chủ của Anthropic, nên cần một đường vào từ Internet: Tailscale Funnel đưa server `python -m investment_agent.mcp_remote` (chỉ nghe ở `127.0.0.1:8770`) ra một địa chỉ `https://<tên-máy>.<tailnet>.ts.net`. Thiết kế: [docs/superpowers/specs/2026-11-27-mcp-tu-xa-design.md](../superpowers/specs/2026-11-27-mcp-tu-xa-design.md).

Server chỉ có các công cụ dữ liệu thị trường công khai (như bản trên máy), không chạm dữ liệu cá nhân. Nó chỉ trả lời ở một đường dẫn bí mật, chặn tên máy lạ và nhận tối đa 120 lượt gọi mỗi phút. Máy phải bật và đăng nhập thì mới dùng được.

## Cài một lần

1. **Cài Tailscale** (PowerShell): `winget install Tailscale.Tailscale`, mở Tailscale và đăng nhập bằng tài khoản của bạn (gói miễn phí là đủ).
2. **Bật HTTPS và Funnel** trong trang quản trị Tailscale (https://login.tailscale.com/admin):
   - DNS → bật **MagicDNS** và **HTTPS Certificates**.
   - Access controls → thêm thuộc tính `funnel` cho máy này (trang quản trị có nút gợi ý khi chạy lệnh ở bước 4 lần đầu).
3. **Tạo chuỗi bí mật và khai tên máy** (PowerShell, ở thư mục dự án):
   - `.venv\Scripts\python.exe -m investment_agent.mcp_remote --new-secret` (ghi `MCP_REMOTE_SECRET` vào `.env.local`, không in ra).
   - Thêm dòng `MCP_REMOTE_HOST=<tên-máy>.<tailnet>.ts.net` vào `.env.local` (tên lấy trong Tailscale → Machines, phần "Full domain").
4. **Mở Funnel tới cổng 8770**: `tailscale funnel --bg 8770` (chạy nền, giữ sau khi khởi động lại).
5. **Đăng ký tác vụ chạy server**: `powershell -ExecutionPolicy Bypass -File scripts\windows\register-tasks.ps1 -Register`, rồi đăng xuất và đăng nhập lại (hoặc chạy tác vụ `InvestmentAgent-McpRemote` trong Task Scheduler).
6. **Lấy địa chỉ connector**: mở PowerShell, nạp `.env.local` rồi chạy `.venv\Scripts\python.exe -m investment_agent.mcp_remote --url`. Địa chỉ in ra là bí mật: không gửi cho ai, không dán vào chat.
7. **Thêm vào claude.ai**: Settings → Connectors → Add custom connector, đặt tên "Dữ liệu công khai HOSE", dán địa chỉ ở bước 6, không cần OAuth. Ứng dụng điện thoại dùng chung connector của tài khoản.
8. Trong Project "Đầu tư cổ phiếu - dữ liệu trên máy", bật connector đó cho cuộc trò chuyện.

## Kiểm tra và xử lý

- Tình trạng hệ thống có dòng **Kết nối từ xa**: "Quá hạn" nghĩa là server trên máy không trả lời (xem `logs\mcp-remote.log`, tác vụ `InvestmentAgent-McpRemote`).
- Lộ địa chỉ: chạy lại `--new-secret`, khởi động lại tác vụ, lấy địa chỉ mới (bước 6) và sửa connector trên claude.ai.
- Tắt kết nối từ xa: `tailscale funnel --bg off` (hoặc `tailscale funnel reset`), xóa `MCP_REMOTE_SECRET` khỏi `.env.local`.
