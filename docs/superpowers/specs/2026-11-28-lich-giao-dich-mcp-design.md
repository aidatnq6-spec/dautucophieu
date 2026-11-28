# Lịch giao dịch HOSE cho Claude (MCP)

Chủ sở hữu duyệt ngày 28/11/2026. Claude cần biết một ngày có phiên không, phiên trước và sau, số phiên giữa hai ngày, theo đúng lịch HOSE mà các bước tự động dùng (`config/trading-calendar-hose-<năm>.json`, có nguồn là thông báo của HOSE).

## Thiết kế

Một công cụ `lich_giao_dich(ngay=None, den_ngay=None)` trong `public_tools.py`, đăng ký ở `mcp_server`.

- `ngay` (YYYY-MM-DD, mặc định hôm nay giờ Việt Nam): `co_phien`, `ly_do` khi không có phiên ("cuối tuần" hoặc "ngày nghỉ theo lịch HOSE"), `phien_truoc` và `phien_sau` (phiên gần nhất trước và sau, không tính chính ngày đó).
- `den_ngay`: `so_phien` từ `ngay` đến `den_ngay` (tính cả hai đầu; `den_ngay` trước `ngay` thì đổi chỗ), `cac_phien` khi không quá 260 phiên.
- Luôn kèm: `ngay_nghi_con_lai` (ngày nghỉ rơi vào ngày thường, từ `ngay` đến hết phạm vi lịch), `pham_vi` (`tu`, `den`), `phien_ban`, `nguon`, `xac_minh`.
- Ngày ngoài phạm vi lịch: `thieu: true`, lý do "chưa có lịch giao dịch HOSE năm <năm> trong kho". Phiên trước hoặc sau ra ngoài phạm vi thì `null` kèm `ly_do_phien_truoc` hoặc `ly_do_phien_sau`. Không suy ra ngày nghỉ, không đặt tên ngày lễ (tệp lịch chỉ có ngày).
- Ngày sai định dạng: `thieu` "Ngày không hợp lệ (cần YYYY-MM-DD)."

## Kèm theo

- `load_calendar` và `_read_calendar` chuyển từ `cli.py` sang `market/calendar.py` (`cli.py` import lại, hành vi giữ nguyên), vì `public_tools.py` chỉ được import `investment_agent.market…`.
- Thư mục lịch: `config/` của repo (`PublicData(..., config_dir=...)` cho test).
- Mô tả công cụ, `docs/claude-project-instructions.md`, danh sách công cụ đã duyệt trong test; plugin 0.29.0.
