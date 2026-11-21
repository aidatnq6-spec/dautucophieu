# Dòng tiền & kỹ thuật, Hiệu suất theo kỳ (21/11/2026)

Chủ sở hữu duyệt ngày 21/11/2026 (kaizen từ FireAnt, đề xuất 3 + 4). Chỉ dùng dữ liệu công khai đã lưu; không gọi nguồn mới.

## Dòng tiền & kỹ thuật (trang Theo dõi)
Mỗi mã trong danh sách theo dõi (`data/market-symbols.txt`) có một dòng. Mã đang nắm xếp trước và có nhãn "đang nắm".
- **Giá và % phiên:** giá đóng cửa gần nhất và mức thay đổi so với phiên trước (chuỗi giá đóng cửa đã lưu).
- **KL/TB20:** khối lượng phiên chia cho trung bình 20 phiên trước đó, từ nến ngày. Cần ít nhất 21 phiên, và nến cuối phải cùng ngày với giá
  đóng cửa cuối; nếu không thì ghi "chưa đủ".
- **Trong phiên:** vị trí giá đóng cửa giữa giá thấp và giá cao của phiên.
- **Khối ngoại:** giá trị ròng của phiên (tỷ đồng) từ ảnh chụp phiên, và số phiên liên tiếp cùng chiều (gom hoặc xả). Chỉ hiện khi ảnh chụp
  cùng ngày với giá đóng cửa cuối.
- **Vùng 52 tuần:** vị trí giá giữa đáy và đỉnh 52 tuần, **theo giá đóng cửa** (lịch sử dài chỉ có giá đóng cửa). Cần lịch sử từ 365 ngày.
- **Lọc nhanh (đếm số mã):**
  - Khối lượng đột biến: từ 2 lần trung bình 20 phiên.
  - Vượt đỉnh 52 tuần: giá đóng cửa cao hơn mọi giá đóng cửa trong 52 tuần trước.
  - Thủng đáy 52 tuần: giá đóng cửa thấp hơn mọi giá đóng cửa trong 52 tuần trước.
  - Cắt lên / cắt xuống MA20, MA50: phiên trước ở dưới (hoặc trên) đường trung bình, phiên này vượt lên (hoặc xuống).
  - Khối ngoại gom / xả: cùng chiều ít nhất 5 phiên liên tiếp.
- Thiếu dữ liệu thì ghi "chưa đủ", không ước lượng.

## Hiệu suất theo kỳ (trang Chuỗi giá trị)
Mỗi chuỗi trong `config/value-chains.json` có một dòng.
- **1 tuần, 1 tháng, 3 tháng, 1 năm:** giá đóng cửa cuối so với giá đóng cửa cuối cùng vào hoặc trước ngày bắt đầu kỳ (7, 30, 91, 365 ngày).
- **Từ đầu năm:** so với giá đóng cửa cuối của năm trước.
- **Cách tính của chuỗi:** bình quân đều các mã có số, ghi số mã được tính trên tổng số mã. Không trọng số vốn hóa, vì không có vốn hóa đã lưu
  cho mọi mã.
- **Mã bị bỏ:** mã không có giá đóng cửa trong 10 ngày gần nhất bị bỏ và nêu tên ("giá cũ"); mã chưa có giá cũng nêu tên.
- **Các cột khác:**
  - Hôm nay: số mã tăng, giảm, đứng giá so với phiên trước.
  - Vùng 52 tuần: trung vị vị trí của các mã giữa đáy và đỉnh năm.
  - Mạnh nhất 1 tháng: mã tăng nhiều nhất trong 1 tháng.

## Không làm
Không khuyến nghị mua bán, không gửi Telegram, không gửi dữ liệu cho AI. Mã đang nắm chỉ dùng để sắp xếp và đánh dấu trên trang.
