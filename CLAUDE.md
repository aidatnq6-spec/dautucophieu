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
- Sau `verify.ps1`, bước build sửa `apps/web/next-env.d.ts`: khôi phục bằng `git checkout -- apps/web/next-env.d.ts`, không commit.

## Quy trình
- Nhánh `feat/…`, `fix/…`, `chore/…`, `docs/…` tạo từ `origin/main`; mỗi việc một PR, chủ sở hữu tự merge.
- TDD: viết test, thấy đỏ, rồi mới viết code. Chạy toàn bộ test backend trước mỗi commit.
- Commit một dòng tiếng Anh dạng `feat: …`/`fix: …`, tên tính năng giữ tiếng Việt như trên giao diện (ví dụ `feat: Chuỗi tác động vĩ mô on Vĩ mô …`).
- Máy không có `gh`: push nhánh rồi đưa link `https://github.com/aidatnq6-spec/dautucophieu/pull/new/<nhánh>` kèm tiêu đề và mô tả PR.

## Vận hành và dữ liệu
- Lịch Windows `InvestmentAgent-AfterClose` chạy [scripts/windows/run-after-close.ps1](scripts/windows/run-after-close.ps1) lúc 08:30, 15:30, 20:00 và khi đăng nhập; mỗi bước ghi một dòng vào `logs/scheduler.log`.
- Bản tin Telegram gửi một lần lúc 15:30 và không sửa sau đó; trang web đọc lại ảnh chụp phiên (`data/brief/`) nên số HOSE hiện sau lượt 20:00.
- Vnstock 6.0.0 (bắt buộc từ 11/11/2026) bỏ các nguồn miễn phí: mọi nguồn giá cần khóa API của công ty chứng khoán. Giá ngày và VN-Index nay lấy từ API công khai VNDirect (`market/providers/vndirect_market.py`, cùng giá đã điều chỉnh); danh sách HOSE, bảng giá cuối phiên và sự kiện doanh nghiệp cũng từ VNDirect (`market/providers/vndirect_data.py`). Ngành ICB và VN30 cũng từ VNDirect (mã đã phân ngành giữ nguyên, khác biệt chỉ được báo); VN100 không có nguồn công khai nên giữ danh sách đã lưu kèm ngày. Bảng giá Xu hướng là giá cuối phiên VNDirect (không có giá theo phút). Báo cáo cơ bản (EPS, cổ tức, phát hành, các dòng Chất lượng báo cáo) dựng từ VNDirect (`market/fundamentals_vndirect.py`); số cổ phiếu lưu hành giữ số Vnstock 11/2026 vì số VNDirect (51004) và vốn điều lệ đều chậm. Cổ đông lớn và ban lãnh đạo cũng từ VNDirect (chỉ người đang nắm cổ phiếu; không có tỷ lệ Nhà nước, tự do chuyển nhượng, cơ cấu theo loại cổ đông). Không còn phần nào phụ thuộc Vnstock.
- Nguồn công khai đọc theo robots.txt; không lấy VnExpress.
