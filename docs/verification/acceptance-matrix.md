# Ma trận nghiệm thu bản thử nghiệm

Ngày: 2026-10-25 · Nhánh `feat/investment-agent`. Đối chiếu 11 điều kiện ở §15 của thiết kế (kế hoạch ghi "15 nhóm"; thiết kế hiện có 11 mục).

Trạng thái: **passed** = kiểm thử tự động đạt trên dữ liệu tổng hợp/fake; **not_run** = cần cấu hình hoặc dữ liệu thật chưa có; **failed** = không đạt. Không mục nào được coi là đạt với dữ liệu thật.

Lệnh tổng hợp: `scripts\windows\verify.ps1` — backend pytest (≈590 test), web typecheck, lint, unit (≈70), build, Playwright e2e (17). Kết quả lần chạy cuối: tất cả PASS.

| # | Điều kiện (§15) | Bằng chứng tự động | Synthetic | Live |
|---|---|---|---|---|
| 1 | 13 câu đúng mọi biên; hạn chế tài chính không bị điểm cao vô hiệu | `tests/domain/test_risk.py` (12 biên, cờ câu 4/7, mâu thuẫn), e2e onboarding (13 câu → Cân bằng 39) | passed | not_run |
| 2 | Tỷ trọng 0/10/25/35/50/60%; ngoại lệ ≤ 90%, không kích hoạt khi thiếu đánh giá | `tests/domain/test_allocation.py` (42 test, đột biến đã kiểm) | passed | not_run |
| 3 | Sổ mua/bán, phí, thuế, cổ tức tiền/cổ phiếu, thứ tự trong ngày, số dư đầu, sửa lùi ngày; đối chiếu tài sản, không lãi giả | `test_ledger.py` (oracle Fraction 400 bước), `test_corporate_actions.py`, `test_reconciliation.py` (sai lệch đối chiếu = 0), integration (sửa phí → báo cáo mới), e2e sổ (25.000 → sửa → 26.000) | passed | not_run |
| 4 | Báo cáo nguồn, độ phủ, khoảng thiếu của 50 mã × 10 năm trước phân tích thật | Công cụ audit (`test_coverage.py`), universe chặn bằng chứng do caller gửi (`test_universe*.py`) | passed (công cụ) | **not_run** — chưa có nguồn dữ liệu được phép dùng (Task 5 `partial`); không có danh sách 50 mã hoàn chỉnh |
| 5 | Chuyển sàn/sự kiện vốn không trùng mã, nhảy giá giả, sai số cổ phiếu; tách as-reported và hồi tố | `test_price_pipeline.py`, `test_asof_ratios.py` (đột biến đã kiểm) | passed | not_run |
| 6 | Khuyến nghị có nguồn, giả định, mô hình, giới hạn vốn; không giao dịch thật hay đổi danh sách khi chưa duyệt | `test_recommendations.py`, `test_cashflow_models.py`, `test_sector_models.py`, e2e research (truy nguồn, duyệt/từ chối) | passed | not_run |
| 7 | Ngày nghỉ không báo thiếu; lỗi mạng/máy tắt có trạng thái, chạy bù; tác vụ lặp không trùng | `test_schedule.py` (slot, ngày nghỉ, chạy bù, lease), `test_publication.py` (run key), integration (retry cùng snapshot) | passed | not_run (tác vụ Windows chưa đăng ký; chưa có lịch HOSE chính thức) |
| 8 | Bản tin lưu và gửi đúng nhóm đã xác nhận; lỗi/timeout có trạng thái; chia tin không mất phần | `test_delivery.py`, `test_notifications_route.py`, integration, e2e after-close | passed | **not_run** — chưa có Bot Token/nhóm thật |
| 9 | Đổi model/fallback không đổi quy tắc tài chính, không hạ chính sách dữ liệu; từ chối sai schema/thiếu bằng chứng | `test_gateway.py`, `test_privacy_and_tools.py`, `test_output_validation.py`, integration (hết credit/không có tuyến ZDR/sai schema → bản tin không AI) | passed | **not_run** — chưa có key/ngân sách; chưa đánh giá model |
| 10 | Khóa không ở bundle trình duyệt, Firestore client, Git, log; tài khoản ngoài allowlist bị chặn | `test_auth.py`, session/proxy unit test, redaction test, settings không nhận token, JobLogger trường cố định, e2e chuyển hướng đăng nhập | passed | not_run (đăng nhập Firebase thật, Rules deploy) |
| 11 | Khôi phục bản sao lưu và chạy luồng từ hồ sơ đến bản tin trên Windows | `test_recovery.py` (diễn tập khôi phục), e2e onboarding → sổ → bản tin trên máy Windows này | passed | not_run (Firestore thật) |

## Tiêm lỗi đã kiểm tra (Task 30)

| Lỗi | Kết quả mong đợi | Test |
|---|---|---|
| Firebase offline | 503, không ghi, không phát hành | integration `test_firebase_offline_blocks_mutations_and_publication`; repo tests |
| Nguồn tài chính sửa số liệu | revision mới, quá khứ không đổi | `test_asof_ratios.py::test_later_revision_does_not_rewrite_the_past` |
| Ngày nghỉ | không tạo phiên | `test_schedule.py::test_weekend_and_holiday_produce_no_new_session` |
| Thiếu giá | bản tin `incomplete`, không gửi | integration `test_missing_price_gives_incomplete_unsent_report` |
| Hết credit / provider không ZDR / AI sai schema | bản tin số liệu không AI, cờ `ai_unavailable` | integration (3 ca) |
| Telegram timeout | `unknown`, không tự gửi lại | integration + `test_delivery.py` |
| Máy bật lại | chạy bù phiên gần nhất, đếm phiên bỏ lỡ | `test_schedule.py::test_resume_catches_up_only_the_latest_missed_session_and_counts_others` |
| Hồ sơ đổi giữa job | `failed/inputs_changed`, không phát hành | integration + `test_publication.py` |

## Lỗi thật phát hiện trong quá trình kiểm chứng

- Route sổ báo `cash_negative` thay vì `version_conflict` khi phiên bản cũ (Task 11, đã sửa).
- Vòng theo dõi tác vụ dừng ngay dưới React Strict Mode (Task 30, đã sửa).
- `GET /jobs/{id}` trả 404 ngay sau 202 do race với tác vụ nền (Task 30, đã sửa, có test hồi quy).
