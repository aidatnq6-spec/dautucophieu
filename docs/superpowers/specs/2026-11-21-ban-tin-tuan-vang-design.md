# Bản tin tuần: mục Vàng trong tuần (21/11/2026)

Chủ sở hữu chọn ngày 21/11/2026: thêm mục VÀNG TRONG TUẦN vào Bản tin tuần, gồm giá và chênh lệch SJC; dòng chênh lệch SJC so với thế giới
chuyển từ mục Chuỗi liên thị trường sang mục này, để không lặp. Chỉ giá công khai: không nêu lượng vàng đang giữ, không gọi AI, không dự báo.

## Nội dung
- Tuần là thứ Sáu của tuần vừa qua (`week_of`) so với thứ Sáu trước đó, như các số khác của bản tin.
- Vàng thế giới: XAU/USD (gold-api.com, chuỗi `xau_usd`). Vàng miếng SJC: giá mua vào của Phú Quý (`gold-price-history.json`).
  Mỗi dòng: giá ở ngày thứ Sáu, mức đổi so với thứ Sáu trước, mỗi số kèm ngày của chính nó.
- Số của một ngày là số đã lưu gần nhất vào hoặc trước ngày đó, cách ngày đó không quá 3 ngày. Quá 3 ngày hay chưa có thì không lấy
  số cũ hơn: dòng ghi "chưa có số" kèm ngày bắt đầu lưu, hoặc ngày của số gần nhất.
- Chênh lệch SJC: dòng hiện có (giá bán SJC so với giá thế giới quy đổi theo tỷ giá bán Vietcombank, lúc soạn bản tin), thêm số của
  thứ Sáu trước từ chuỗi `sjc_gap_pct` (cùng cách tính), theo cùng quy tắc 3 ngày. Không có thì không ghi phần tuần trước.
- Mục Chuỗi liên thị trường chỉ còn câu tóm tắt chuỗi.

## Không làm
- Không thêm ngưỡng hay lời nhận định; không đổi trang Vĩ mô hay Nhắc giá vàng.
