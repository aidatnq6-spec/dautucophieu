# Nợ vay trong Bảng số tài chính (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 của đề xuất). Kaizen từ bài "Các khoản vay ngắn hạn, dài hạn" (ví dụ HPG 2021, thuyết minh 24): vay
ngắn hạn tài trợ vốn lưu động, vay dài hạn tài trợ dự án; cần xem lãi suất, khả năng trả lãi, và tiền gửi so với vay ngắn hạn (HPG vay rẻ gửi lại).
Doanh nghiệp thường, dữ liệu công khai, không gọi AI.

## Nguồn
- Đã có: vay và nợ ngắn hạn (13110), dài hạn (13340), chi phí lãi vay (22510), tiền, đầu tư tài chính ngắn hạn. Đối chiếu HPG 31/12/2021: 43.747,6 và
  13.464,9 tỷ (bài: 43.747, 13.464); đầu năm dài hạn 17.343,2 (bài: 17.343), ngắn hạn 36.798,5 (bài ghi 36.079,8: chưa xác định nguồn lệch).
- Thêm dòng lưu chuyển tiền tệ (tên kiểm trong `v4/financial_models` ngày 25/11/2026): 33300 tiền vay nhận được, 33400 tiền chi trả nợ gốc vay
  (âm), 31100 lãi, lỗ chênh lệch tỷ giá chưa thực hiện. `LINES_VERSION` lên 11 (lấy lại lịch sử một lần).
- VNDirect không có lãi suất từng khoản, cơ cấu theo loại tiền, nợ dài hạn đến hạn trả, ngân hàng, tài sản đảm bảo (chỉ có trong thuyết minh).
- Không làm dấu hiệu "lãi vay vốn hóa": HPG 2021–2025 tiền lãi đã trả (31170) chỉ chênh chi phí lãi vay vài chục tỷ, kể cả khi đang xây Dung Quất 2.

## Bảng
Nhóm **Nợ vay**, sau Chi phí trả trước, trước Quy mô và định giá:
- **Vay ngắn hạn**, **Vay dài hạn** (số dư cuối kỳ); **Tỷ trọng vay ngắn hạn** = ngắn hạn ÷ (ngắn + dài hạn).
- **Lãi suất vay bình quân** = chi phí lãi vay ÷ nợ vay bình quân cuối kỳ và cùng kỳ năm trước (quý: lãi vay 4 quý). HPG 2021: 2.526 ÷ 55.677 = 4,5%.
- **Khả năng trả lãi (ICR)** = EBIT ÷ chi phí lãi vay (lần; quý: 4 quý). HPG 2021: 15,7 lần.
- **(Tiền + đầu tư tài chính ngắn hạn) ÷ vay ngắn hạn** (lần).
- **Vay thuần trong kỳ (dòng tiền)** = tiền vay nhận được + tiền trả nợ gốc (số của kỳ).
- **Lãi, lỗ tỷ giá chưa thực hiện (dòng tiền)**: tham khảo.
- Thiếu thành phần, lãi vay bằng 0 hoặc mẫu số không dương: để trống. Ghi chú "Chưa đồng bộ" cho bản ghi trước phiên bản 11.

## Dấu hiệu "Khả năng trả lãi thấp" (bổ sung 25/11/2026, chủ sở hữu duyệt bước 2, ngưỡng dưới 3 lần)
- Chất lượng báo cáo, sau "Lợi thế thương mại lớn". Bản ghi cơ bản lấy thêm chi phí lãi vay theo năm.
- ICR = (LNTT + chi phí lãi vay) ÷ chi phí lãi vay năm gần nhất; bật khi **dưới 3 lần**, hoặc EBIT không dương. Hiện ICR hai năm.
- Không có lãi vay (0 hoặc thiếu dòng): không đánh giá được, ghi lý do. Thử 40 mã có lãi vay, năm gần nhất: 4 mã bật.
- Chỉ hiện trên trang.

## Các khoản vay nhập tay (bổ sung 25/11/2026, chủ sở hữu duyệt bước 3)
- Khối Thuyết minh TSCĐ (nhập tay), khóa `loans` (tối đa 30) và `debt_notes`. Mỗi khoản: bên cho vay (bắt buộc), loại tiền (VND, USD, EUR, JPY, CNY,
  khác), kỳ hạn (ngắn, dài hạn), dư nợ (tỷ đồng quy đổi theo thuyết minh, bắt buộc), lãi suất từ–đến (%/năm, 0–100), lãi suất cơ sở thả nổi và biên
  độ, năm đáo hạn, tài sản đảm bảo, ghi chú. `debt_notes`: kỳ báo cáo đã đọc, nợ dài hạn đến hạn trả trong 12 tháng (HPG 2021: 6.200), mức đồng Việt
  Nam mất giá giả định (trên 0 đến 100%).
- Phần mềm cộng theo loại tiền, kỳ hạn, năm đáo hạn ("chưa ghi năm" riêng); lãi suất theo loại tiền là **khoảng** thấp nhất–cao nhất và danh sách
  lãi suất thả nổi (không lấy trung bình); đối chiếu tổng với vay ngắn + dài hạn của VNDirect ở kỳ đã đọc (tỷ lệ phần bạn đã ghi); **kịch bản tỷ
  giá** = dư nợ ngoại tệ (khác VND) × mức mất giá bạn giả định, so với LNTT kỳ đó, ghi rõ "kịch bản, không phải dự báo".
- HPG 2021 (bài): VND ngắn hạn 12.998 (2,4–6,5%), USD ngắn hạn 6.357 (1,2–2,3%), HSBC 503 đến 2024; USD dài hạn Libor + 2,05%.
- Ghi phần khác không gửi `loans`, `debt_notes` thì giữ nguyên.
