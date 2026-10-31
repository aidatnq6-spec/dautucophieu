# Chất lượng báo cáo: F-Score và dấu hiệu cần xem kỹ

Ngày: 31/10/2026 · Trạng thái: chủ sở hữu đã chọn làm cả ba phần (tải thêm số liệu, F-Score, dấu hiệu riêng lẻ)

## Mục tiêu

Với mỗi mã theo dõi phi tài chính, trang Định giá và hồ sơ mã cho thấy: điểm F-Score (Piotroski, 0–9) của năm tài chính gần nhất, từng tiêu chí đạt hay không, và vài dấu hiệu bất thường trong báo cáo kèm số thật. Đây là **dấu hiệu cần xem kỹ**, không phải kết luận gian lận, không phải khuyến nghị.

## Nguồn và giới hạn (kiểm tra 31/10/2026 với FPT)

- Vnstock 5.2 gói Cộng đồng: kết quả kinh doanh 20 dòng, bảng cân đối 21 dòng, lưu chuyển tiền tệ chỉ 7 dòng tổng (có lưu chuyển tiền thuần từ hoạt động kinh doanh, **không có khấu hao**), 8 năm.
- Vì thiếu khấu hao, **không tính M-Score (Beneish) 8 biến**; không dùng biến thể tự chế. Ngưỡng trung bình của nghiên cứu Beneish chưa kiểm chứng được nên không dùng.
- Sự kiện phát hành cổ phiếu có tên loại: "Cổ phiếu thưởng", "Trả Cổ tức bằng Cổ phiếu" (không huy động vốn); "Quyền mua CP cho Cổ đông hiện hữu", "Phát hành riêng lẻ", "Phát hành cho CBCNV" (huy động/pha loãng).

## Số liệu tải thêm

Mỗi mã lưu thêm theo năm (`annual`): doanh thu thuần, lãi gộp, chi phí bán hàng, chi phí quản lý, lợi nhuận sau thuế (hợp nhất), tổng tài sản, tài sản ngắn hạn, nợ ngắn hạn, nợ dài hạn, phải thu ngắn hạn, lưu chuyển tiền thuần từ hoạt động kinh doanh; và các đợt phát hành cổ phiếu theo loại. Thêm một lượt gọi lưu chuyển tiền tệ mỗi mã.

Cập nhật dày hơn trong các tháng có hạn nộp báo cáo (1, 2, 4, 5, 7, 8, 10, 11): mã quá 3 ngày thì làm mới, tối đa 17 mã mỗi tối (đủ 50 mã trong 3 ngày); các tháng khác giữ 7 ngày, 8 mã. Khi quý mới nhất của một mã đổi, ghi ngày phát hiện; trang Định giá gắn nhãn "Quý mới" trong 7 ngày.

## F-Score

Năm Y = năm tài chính gần nhất có đủ số liệu; so với Y−1 (và Y−2 cho tài sản đầu kỳ):

1. ROA > 0 (lợi nhuận Y / tổng tài sản đầu kỳ)
2. Dòng tiền kinh doanh > 0
3. ROA tăng so với năm trước
4. Dòng tiền kinh doanh > lợi nhuận
5. Nợ dài hạn / tổng tài sản giảm (nguồn chỉ có tổng nợ dài hạn, không tách vay)
6. Tài sản ngắn hạn / nợ ngắn hạn tăng
7. Không phát hành cổ phiếu huy động vốn trong năm Y (thưởng, cổ tức bằng cổ phiếu không tính; ESOP tính)
8. Biên lãi gộp tăng
9. Vòng quay tài sản (doanh thu / tài sản đầu kỳ) tăng

Thiếu số cho tiêu chí nào thì tiêu chí đó "không đánh giá được"; điểm ghi "x/n tiêu chí đánh giá được". Cần ít nhất 7 tiêu chí mới xếp mức: 8–9 mạnh, 0–2 yếu, còn lại trung bình (mốc của Piotroski).

Không áp dụng cho ngân hàng, dịch vụ tài chính, bảo hiểm (cấu trúc báo cáo khác).

## Dấu hiệu cần xem kỹ (quy tắc của ứng dụng, không phải ngưỡng nghiên cứu)

- **Lãi nhưng dòng tiền kinh doanh âm:** ít nhất 2 trong 3 năm gần nhất.
- **Phải thu tăng nhanh hơn doanh thu:** năm gần nhất, tăng trưởng phải thu cao hơn tăng trưởng doanh thu từ 20 điểm % trở lên.
- **Lợi nhuận dồn tích lớn:** tổng (lợi nhuận − dòng tiền kinh doanh) 3 năm gần nhất lớn hơn 10% tổng tài sản cuối kỳ.

Mỗi dấu hiệu hiện số thật của các năm liên quan. Không gộp thành một điểm.

## Giao diện

- Bảng Định giá: cột "F-Score" (ví dụ "7/9", nhãn mạnh/trung bình/yếu, hoặc "—" kèm lý do); nhãn "Quý mới".
- Chi tiết mã (Định giá và hồ sơ mã): mục "Chất lượng báo cáo" liệt kê 9 tiêu chí với số liệu, và các dấu hiệu cần xem kỹ.

## Ngân hàng, chứng khoán, bảo hiểm: Điểm sức khỏe (bổ sung 31/10/2026)

F-Score không hợp với cấu trúc báo cáo của ba nhóm này, và báo cáo miễn phí của Vnstock thiếu nợ xấu, dự phòng, tỷ lệ kết hợp. Dùng chỉ số ngành theo quý từ API công khai của VNDirect (`v4/ratios`, robots.txt cho phép), một lượt gọi mỗi mã trong lịch chạy (`financial-ratios-sync`), lưu ở `data/financial-ratios/`.

So quý gần nhất có đủ số liệu với cùng quý năm trước (quý mới công bố dở thì dùng quý đủ gần nhất):

- Ngân hàng (7): ROAA dương; ROAA tăng; tỷ lệ nợ xấu giảm; tỷ lệ nợ quá hạn giảm; bao phủ nợ xấu tăng; NIM tăng; vốn chủ / tổng tài sản tăng.
- Chứng khoán (6): ROAA dương; ROAA tăng; biên lợi nhuận ròng tăng; vốn chủ / tổng tài sản tăng; cho vay / vốn chủ giảm; không phát hành cổ phiếu huy động vốn trong 12 tháng.
- Bảo hiểm (6): ROAA dương; ROAA tăng; tỷ lệ kết hợp giảm; biên lợi nhuận ròng tăng; vốn chủ / tổng tài sản tăng; không phát hành cổ phiếu huy động vốn trong 12 tháng.

Gọi là "Điểm sức khỏe", không phải F-Score; là bộ tiêu chí của ứng dụng, không có mốc nghiên cứu nên không xếp mạnh/yếu. Thiếu số thì tiêu chí "không đánh giá được". Cột trên bảng Định giá đổi tên thành "Chất lượng".
