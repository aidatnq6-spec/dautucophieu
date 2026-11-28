# CLAUDE.md

Ứng dụng cá nhân trên Windows để theo dõi đầu tư cổ phiếu HOSE: backend Python 3.11 (FastAPI, [backend/src/investment_agent/](backend/src/investment_agent/)) và web Next.js ([apps/web/](apps/web/), xem [apps/web/AGENTS.md](apps/web/AGENTS.md) — bản Next.js này khác với kiến thức cũ). Giao diện và tài liệu bằng tiếng Việt. Ứng dụng không đặt lệnh.

## Quy tắc cứng
- **Không đoán số.** Nguồn thiếu thì ghi rõ thiếu kèm lý do; không nội suy, không ước lượng, không lấp chỗ trống.
- **Không gửi danh mục hay dữ liệu cá nhân cho AI.** AI chỉ được đọc văn bản báo cáo công khai, với ngân sách thấp (`config/ai-policy.json`).
- `.env.local`, `data/`, `backups/`, `logs/` và khóa không vào Git; không chép số liệu cá nhân vào code, test, commit hay PR.
- Spec là căn cứ: [docs/superpowers/specs/](docs/superpowers/specs/), kế hoạch ở [docs/plans/](docs/plans/), quy tắc thị trường ở [docs/decisions/market-rules.md](docs/decisions/market-rules.md). Đổi hành vi đã có trong spec thì hỏi chủ sở hữu trước.

## Lệnh
- Python của dự án: `.venv/Scripts/python.exe` (Python hệ thống không có pytest).
- Test backend: `.venv/Scripts/python.exe -m pytest backend/tests -q -p no:warnings`
- Kiểm tra toàn bộ (bắt buộc đạt trước khi mở PR): `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\verify.ps1`
- Web: `npm.cmd --prefix apps/web run <dev|typecheck|lint|test|build>`; CLI backend: `python -m investment_agent.cli <lệnh>`.
- `verify.ps1` dựng web vào `apps/web/.next-verify` (không đụng `.next` của ứng dụng đang chạy) và tự khôi phục `next-env.d.ts`; một lệnh build tay vẫn sửa tệp đó: khôi phục bằng `git checkout -- apps/web/next-env.d.ts`, không commit. Sau khi merge vào main, chạy `scripts\windows\update-app.ps1` để dựng lại và khởi động lại ứng dụng (kể cả MCP từ xa, qua `restart-mcp-remote.ps1`).

## Quy trình
- Nhánh `feat/…`, `fix/…`, `chore/…`, `docs/…` tạo từ `origin/main`; mỗi việc một PR, chủ sở hữu tự merge.
- TDD: viết test, thấy đỏ, rồi mới viết code. Chạy toàn bộ test backend trước mỗi commit.
- Commit một dòng tiếng Anh dạng `feat: …`/`fix: …`, tên tính năng giữ tiếng Việt như trên giao diện (ví dụ `feat: Chuỗi tác động vĩ mô on Vĩ mô …`).
- Máy không có `gh`: push nhánh rồi đưa link `https://github.com/aidatnq6-spec/dautucophieu/pull/new/<nhánh>` kèm tiêu đề và mô tả PR.

## Vận hành và dữ liệu
- Lịch Windows `InvestmentAgent-AfterClose` chạy [scripts/windows/run-after-close.ps1](scripts/windows/run-after-close.ps1) lúc 08:30, 15:30, 20:00 và khi đăng nhập; mỗi bước ghi một dòng vào `logs/scheduler.log`.
- Bản tin Telegram gửi một lần lúc 15:30 và không sửa sau đó; trang web đọc lại ảnh chụp phiên (`data/brief/`) nên số HOSE hiện sau lượt 20:00.
- Vnstock 6.0.0 (bắt buộc từ 11/11/2026) bỏ các nguồn miễn phí: mọi nguồn giá cần khóa API của công ty chứng khoán. Giá ngày và VN-Index nay lấy từ API công khai VNDirect (`market/providers/vndirect_market.py`, cùng giá đã điều chỉnh); danh sách HOSE, bảng giá cuối phiên và sự kiện doanh nghiệp cũng từ VNDirect (`market/providers/vndirect_data.py`). Ngành ICB và VN30 cũng từ VNDirect (mã đã phân ngành giữ nguyên, khác biệt chỉ được báo); VN100 không có nguồn công khai nên giữ danh sách đã lưu kèm ngày. Bảng giá Xu hướng là giá cuối phiên VNDirect (không có giá theo phút). Tự doanh của bản tin cũng từ VNDirect (`proprietary_trading`), chậm vài phiên nên luôn ghi phiên của số; lượt 20:00 lưu từng phiên khoảng 1 năm vào `data/proprietary/` cho công cụ `tu_doanh`. Báo cáo cơ bản (EPS, cổ tức, phát hành, các dòng Chất lượng báo cáo) dựng từ VNDirect (`market/fundamentals_vndirect.py`); số cổ phiếu lưu hành chỉ đổi khi số lưu hành của HOSE (`providers/hose_data.py`, api.hsx.vn) và số VNDirect (51004) cùng ra một số mới; hai nguồn mâu thuẫn thì giữ số đang có và ghi `shares_check`. Cổ đông lớn và ban lãnh đạo cũng từ VNDirect (chỉ người đang nắm cổ phiếu; không có tỷ lệ Nhà nước, tự do chuyển nhượng, cơ cấu theo loại cổ đông). Không còn phần nào phụ thuộc Vnstock. Giao dịch nội bộ VNDirect thiếu số lượng thì lượt 20:00 đọc văn bản PDF đính kèm tin HOSE (`market/insider_docs.py`, api.hsx.vn, OCR trên máy) và chỉ nhận khi trước ± đã giao dịch = sau.
- Văn bản công bố (`market/filings.py`, lượt 20:00): báo cáo tài chính từ danh mục CafeF của từng mã (trang công ty khi CafeF không có), nghị quyết từ trang công ty trong `data/report-sources.json` và tin VNDirect.
- Nguồn công khai đọc theo robots.txt; không lấy VnExpress.
- MCP dữ liệu công khai cho Claude (`python -m investment_agent.mcp_server`), đăng ký qua plugin [plugins/dautucophieu/](plugins/dautucophieu/) (marketplace ở `.claude-plugin/`, lệnh tắt `/dautu-ma`, `/dautu-sosanh`, `/dautu-quy`, `/dautu-thitruong`, `/dautu-vimo`; sửa skill xong chạy `claude plugin marketplace update dautucophieu` rồi `claude plugin update dautucophieu@dautucophieu`): chỉ đọc tệp thị trường trong `data/` qua [public_tools.py](backend/src/investment_agent/public_tools.py), không chạm Firestore hay dữ liệu cá nhân, không liệt kê các mã đang theo dõi; spec [2026-11-26-mcp-du-lieu-cong-khai-design.md](docs/superpowers/specs/2026-11-26-mcp-du-lieu-cong-khai-design.md). claude.ai trên web và điện thoại gọi bản HTTP `python -m investment_agent.mcp_remote` (127.0.0.1:8770, đường dẫn bí mật `MCP_REMOTE_SECRET`, qua Tailscale Funnel; [docs/operations/mcp-tu-xa.md](docs/operations/mcp-tu-xa.md)). Tab Chat của Claude Desktop khai báo server trong cấu hình Desktop và dùng hướng dẫn Project ở [docs/claude-project-instructions.md](docs/claude-project-instructions.md); thêm hay đổi công cụ thì sửa cả tệp đó (có test kiểm tra).
