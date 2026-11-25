# Thuế TNDN trong Bảng số tài chính (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 của đề xuất). Kaizen từ bài "Chi phí thuế thu nhập doanh nghiệp" (HPG 2021, thuyết minh 40): không lấy LNTT ×
20% làm chi phí thuế; tách thuế hiện hành và hoãn lại; xem thuế suất thực tế. Doanh nghiệp thường, dữ liệu công khai, không gọi AI.

## Nguồn
- Đã có: chi phí thuế TNDN (22070), LNTT. Thêm (tên kiểm trong `v4/financial_models` ngày 25/11/2026): 22051 thuế TNDN hiện hành, 22052 thuế TNDN
  hoãn lại, 31180 thuế TNDN đã nộp (lưu chuyển tiền tệ, âm), 12620 tài sản thuế thu nhập hoãn lại, 13350 thuế thu nhập hoãn lại phải trả.
  `LINES_VERSION` lên 13.
- Đối chiếu HPG 2021: hiện hành 2.855,3 (bài: 2.855,3), hoãn lại −319,5 (bài: −319), tổng 2.535,8 (bài: 2.535), LNTT 37.056,8; thuế đã nộp 2.743,1.
  Thu nhập chịu thuế và ưu đãi từng công ty con chỉ có trong thuyết minh.
- 42 mã theo dõi, năm gần nhất (đều có lãi): thuế suất thực tế dưới 5% 0 mã, dưới 10% 3 mã, dưới 15% 12 mã.

## Bảng
Nhóm **Thuế TNDN**, sau Vốn chủ sở hữu, trước Quy mô và định giá: thuế TNDN hiện hành, thuế TNDN hoãn lại (chi phí ghi số âm, lợi ích thuế số
dương, như các chi phí khác); **thuế suất thực tế** = chi phí thuế TNDN ÷ LNTT (quý: 4 quý; LNTT không dương: để trống); **thuế đã nộp ÷ chi phí
thuế** (số của kỳ; chi phí thuế không dương: để trống); tài sản thuế thu nhập hoãn lại; thuế thu nhập hoãn lại phải trả (số dư cuối kỳ). Ghi chú
"Chưa đồng bộ" cho bản ghi trước phiên bản 13.

## Dấu hiệu "Thuế suất thực tế thấp" (bổ sung 25/11/2026, chủ sở hữu duyệt bước 2, ngưỡng dưới 10%)
- Chất lượng báo cáo, sau "Biên gộp lệch mạnh". Bản ghi cơ bản lấy thêm theo năm: chi phí thuế TNDN, thuế hiện hành, thuế hoãn lại.
- Bật khi LNTT năm gần nhất dương mà chi phí thuế TNDN ÷ LNTT **dưới 10%** (một nửa thuế suất phổ thông 20%). Hiện chi phí thuế, phần hiện hành và
  hoãn lại, thuế suất hai năm. Nhắc đọc thuyết minh thuế: ưu đãi theo dự án, địa bàn, chuyển lỗ, phần lợi nhuận không chịu thuế (ví dụ lãi mua rẻ).
- Lỗ trước thuế, hoặc thiếu chi phí thuế: không đánh giá được. Thử 42 mã: 3 mã bật (HPG 2021: 6,8%). Chỉ hiện trên trang.
