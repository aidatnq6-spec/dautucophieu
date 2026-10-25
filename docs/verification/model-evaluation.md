# Đánh giá model AI

Trạng thái: **chưa đánh giá live** (2026-10-25). Chưa có OpenRouter key, ngân sách USD do chủ sở hữu đặt, hay chính sách AI đã duyệt; `config/ai-policy.example.json` để `status: example_unapproved` và `monthly_usd: 0`, nên gateway không gọi mạng. Chưa chọn model mặc định; không chọn "tốt nhất" theo quảng cáo.

## Đã kiểm chứng bằng mock

- `backend/tests/ai/test_output_validation.py` chạy 8 tình huống tổng hợp trong `tests/fixtures/ai/evaluation_cases.json` (nhãn `synthetic`): đọc BCTC đúng/sai số, P/B ngân hàng sai, phân bổ vượt 90%, nguồn không có trong gói, khẳng định chính trực, mã ngoài gói do tài liệu chèn lệnh, rủi ro rỗng.
- Lỗi được chặn bằng mã: `number_mismatch` (sai lệch P/E, P/B quá 0,05), `allocation_exceeds_policy`, `unknown_source`, `unknown_ticker`, `unsupported_integrity_claim`, `missing_risk`, `stale_inputs`. Văn bản trôi chảy không đủ để qua.
- Tối đa một lần sửa với ghi chú chỉ gồm mã lỗi; lỗi lần hai → bản tin số liệu không dùng AI. Mỗi lần chạy lưu phiên bản prompt (`analysis-vi-1`), schema (`analysis-output-1`), snapshot, model/provider, token, chi phí, độ trễ.

## Quy trình đánh giá live (khi chủ sở hữu bật)

1. Chủ sở hữu tạo key OpenRouter cục bộ, đặt ngân sách và duyệt danh sách 2–3 model có endpoint ZDR, không thu thập dữ liệu, hỗ trợ `tools` và `response_format`.
2. Tải danh mục model mới (ghi ngày tải, giá theo token), chạy cùng bộ tình huống trên gói phân tích thật đã giảm dữ liệu: đọc BCTC, doanh nghiệp chu kỳ, ngân hàng, thiếu dữ liệu, mâu thuẫn, prompt injection.
3. Ghi theo từng model: tỷ lệ đầu ra hợp lệ lần đầu/sau sửa, bám nguồn, sai số định lượng, chất lượng tiếng Việt (chủ sở hữu chấm), chi phí và thời gian thực tế.

| Model | Ngày | Hợp lệ lần đầu | Sau sửa | Sai số | Tiếng Việt | Chi phí | Thời gian | Kết luận |
|---|---|---|---|---|---|---|---|---|
| (chưa chạy) | — | — | — | — | — | — | — | not_run |
