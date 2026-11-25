# Doanh thu, giá vốn: sửa số, biên gộp 4 năm, giảm trừ (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 và 2 của đề xuất). Kaizen từ bài "Doanh thu, giá vốn và lãi gộp" (HPG 2021, HAG 2017–Q1/2022): theo dõi
chuỗi biên gộp nhiều năm và nhận ra điều chỉnh hồi tố vào giá vốn. Đối chiếu VNDirect: HPG 2021 doanh thu thuần 149.680, giá vốn 108.571, lãi gộp
41.108, biên gộp 27,5% (bài ghi 28,03%: bài tính sai); HAG biên gộp 2017–2021: 35,8 / 44,1 / 11,0 / 6,5 / 24,2% (khớp), Q1/2022 36,1% (bài 36,2%).
Doanh thu, giá vốn theo mảng chỉ có trong thuyết minh. Dữ liệu công khai, không gọi AI.

## 1. Số đã công bố bị sửa: thêm doanh thu, giá vốn, lãi gộp
Bổ sung [Số đã công bố bị sửa](2026-11-22-phai-thu-ho-to-design.md): ngoài LNST công ty mẹ, LNTT, vốn chủ, các khoản dự phòng, nay theo dõi cả
**doanh thu thuần, giá vốn hàng bán, lợi nhuận gộp** của kỳ đã đóng (cùng ngưỡng: vượt cả 1% và 1 tỷ). Cùng cách hiện ở hồ sơ mã và cùng một dòng
nhắc Telegram cho mã đang giữ. Chỉ bắt các lần sửa từ nay, trong hai năm mỗi lượt đọc lại.

## 2. Bảng số tài chính, nhóm Doanh thu
- **Biên gộp so với trung bình 4 năm trước** (điểm %): biên gộp năm đó − trung bình biên gộp 4 năm liền trước; quý: biên gộp 4 quý tới quý đó −
  trung bình của 4 khung 4 quý kết thúc cùng quý các năm trước. Thiếu một năm: để trống. HAG 2019: −19,2 điểm; HPG 2022: −9,9 điểm.
- **Giảm trừ ÷ doanh thu bán hàng** (chiết khấu, giảm giá, hàng bán bị trả lại). HPG 2021: 0,8%; HAG 2021: 4,1%.

## 3. Dấu hiệu "Biên gộp lệch mạnh" (bổ sung 25/11/2026, chủ sở hữu duyệt bước 3, ngưỡng 10 điểm %)
- Chất lượng báo cáo, sau "Lỗ lũy kế, vốn chủ dưới vốn góp". Từ doanh thu thuần và lãi gộp đã có trong bản ghi cơ bản.
- Bật khi biên gộp năm gần nhất lệch (cao hơn hoặc thấp hơn) trung bình biên gộp 4 năm liền trước từ **10 điểm %**. Hiện biên gộp 5 năm. Nhắc
  đọc thuyết minh giá vốn: giá nguyên liệu, thay đổi cơ cấu mảng, điều chỉnh hồi tố (HAG 2019: −19,2 điểm).
- Thiếu một năm hoặc doanh thu không dương: không đánh giá được. Thử 42 mã: 3 mã bật. Chỉ hiện trên trang.

## 4. Doanh thu, giá vốn theo mảng nhập tay (bổ sung 25/11/2026, chủ sở hữu duyệt bước 4)
- Khối Thuyết minh TSCĐ (nhập tay), khóa `segments`: kỳ (năm hoặc quý, tối đa 15 kỳ) → các mảng (tối đa 12): tên, doanh thu, giá vốn (tỷ đồng),
  theo thuyết minh doanh thu và giá vốn hàng bán (HPG 2021: thuyết minh 31, 32).
- Phần mềm tính lãi gộp, biên gộp từng mảng, **% đóng góp vào tổng lãi gộp** (chỉ khi tổng lãi gộp dương; mảng lỗ gộp có tỷ trọng âm), tổng và
  biên gộp chung; đối chiếu tổng với doanh thu thuần và giá vốn của báo cáo đã lưu cùng kỳ (thuyết minh thường ghi doanh thu trước giảm trừ, nên
  lệch dương ở doanh thu được ghi chú "có thể chưa trừ các khoản giảm trừ"). Ghi phần khác không gửi `segments` thì giữ nguyên.
