# Nhắc "đừng hành động theo giá" khi ghi vàng (20/11/2026)

Chủ sở hữu chọn ngày 20/11/2026: mục 6 trong các đề xuất từ bài phân tích giá vàng. Chủ sở hữu duyệt: ngưỡng cố định ±10%; giá đo là giá của
đúng loại vàng, tạm dùng giá thế giới khi loại đó chưa đủ 30 ngày. Chỉ là lời nhắc: không chặn lưu, không nêu nên mua hay bán.

## Mức đổi 30 ngày (`domain/gold_moves.recent_move`, `price_moves`)
- Giá mới nhất so với giá gần nhất cách đó ít nhất 30 ngày; giá trước đó không được cũ hơn 37 ngày (ngày không đọc được giá), không thì
  không tính. Giá mới nhất phải còn mới: loại vàng 3 ngày (như Sổ tài sản), thế giới 7 ngày.
- Mỗi loại trong bảng giá Phú Quý dùng giá mua vào của chính nó khi đủ 30 ngày (lưu từ 14/11/2026, nên khoảng 14/12/2026); trước đó dùng
  PAXG-USD (bảng Xu hướng) và trang ghi rõ đây là giá thế giới vì giá của loại đó chưa đủ 30 ngày. Dòng không chọn loại dùng giá thế giới.
- "Chạy mạnh" là tăng hoặc giảm từ 10% trở lên (`STRONG_MOVE`).

## Nơi hiện
- Sổ tài sản: khi đang thêm hoặc sửa một dòng vàng, theo loại giá của dòng đó.
- Kế hoạch tích sản: trên ô Ghi lần mua của kế hoạch vàng, theo loại giá của kế hoạch.
- Nội dung: giá nào, tăng hay giảm bao nhiêu, trong bao nhiêu ngày (từ ngày nào đến ngày nào), và "Mua bán vàng theo tỷ trọng của Tháp tài sản
  (10–15%), không theo giá." Dưới ngưỡng hoặc không đủ số thì không hiện gì.
