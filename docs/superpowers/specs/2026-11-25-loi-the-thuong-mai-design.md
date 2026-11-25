# Lợi thế thương mại trong Bảng số tài chính (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 của đề xuất). Kaizen từ bài "Tài sản vô hình và lợi thế thương mại" (ví dụ Novaland 31/12/2021: 5.104 tỷ):
lợi thế thương mại chỉ sinh ra khi mua công ty, là phần trả cao hơn tài sản thuần, phân bổ dần tối đa 10 năm (VAS). Doanh nghiệp thường,
dữ liệu công khai, không gọi AI.

## Nguồn
- Thêm dòng (tên kiểm trong `v4/financial_models` ngày 25/11/2026): 12690 lợi thế thương mại (bảng cân đối), 31111 phân bổ lợi thế thương mại
  (lưu chuyển tiền tệ, khoản cộng lại). Đối chiếu NVL 2021: 5.104,0 tỷ (bài: 5.104). `LINES_VERSION` lên 10 (lấy lại lịch sử một lần).
- Dòng phân bổ của VNDirect thường để trống (NVL cũng vậy, dù lợi thế thương mại giảm mỗi năm), nên chỉ hiện để tham khảo, không dùng tính
  "giảm vượt phân bổ". NVL 2025: VNDirect ghi 0 (2024: 2.476 tỷ); hiện đúng số nguồn, đọc thuyết minh để biết đã xóa sổ hay chưa. NVL 2021 trên bảng: 14,6% vốn chủ công ty mẹ, P/B 5,01 → 5,87 lần khi loại lợi thế thương mại.
- 41 mã theo dõi (năm gần nhất): 16 mã có lợi thế thương mại, không mã nào từ 10% vốn chủ.

## Bảng
- Nhóm Tài sản cố định, sau BĐS đầu tư: **Lợi thế thương mại**; **Lợi thế thương mại ÷ vốn chủ công ty mẹ** (%); **Phân bổ lợi thế thương mại
  (dòng tiền)**.
- Nhóm Quy mô và định giá, sau P/B: **P/B loại lợi thế thương mại** = vốn hoá ÷ (vốn chủ công ty mẹ − lợi thế thương mại), quý và năm như P/B.
  Không trừ TSCĐ vô hình: ở Việt Nam chủ yếu là quyền sử dụng đất, tài sản có giá trị thật. Kỳ không có dòng lợi thế thương mại: để trống.
- Ghi chú "Chưa đồng bộ" cho bản ghi trước phiên bản 10.

## Dấu hiệu "Lợi thế thương mại lớn" (bổ sung 25/11/2026, chủ sở hữu duyệt bước 3, chọn ngưỡng 10%)
- Chất lượng báo cáo, sau "Chi phí trả trước tăng nhanh hơn doanh thu". Bản ghi cơ bản lấy thêm theo năm: lợi thế thương mại, vốn chủ sở hữu,
  lợi ích cổ đông không kiểm soát.
- Bật khi lợi thế thương mại năm gần nhất từ **10% vốn chủ công ty mẹ** (vốn chủ − lợi ích cổ đông không kiểm soát). NVL 2021: 14,6%.
- Ý nghĩa: phần trả cao hơn tài sản thuần khi mua công ty; nếu thương vụ không như kỳ vọng, khoản này có thể bị xóa sổ và làm giảm vốn chủ.
  Hiện số hai năm. Nhắc đọc thuyết minh hợp nhất kinh doanh (có thể ghi ở Thương vụ mua bán, sáp nhập).
- Thiếu dòng hoặc vốn chủ công ty mẹ không dương: không đánh giá được. Lợi thế thương mại bằng 0: không bật.
- Chỉ hiện trên trang. Hiện chưa mã nào trong 41 mã theo dõi bật.
