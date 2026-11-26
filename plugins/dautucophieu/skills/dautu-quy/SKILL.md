---
name: dautu-quy
description: "So sánh hai đến bốn quỹ mở trên Fmarket từ dữ liệu công khai trên máy: NAV, phí, lợi nhuận công bố, lịch sử NAV và danh mục quỹ đã công bố. Dùng khi người dùng gõ /dautu-quy <QUỸ1> <QUỸ2> … hoặc nhờ so sánh vài quỹ mở."
argument-hint: "<QUỸ1> <QUỸ2> [QUỸ3] [QUỸ4] (ví dụ ABEF DCDS)"
---

# So sánh quỹ mở: $ARGUMENTS

Các mã quỹ là những từ người dùng gõ sau lệnh, viết hoa, từ 2 đến 4 quỹ.
- Không có mã nào: gọi `quy_mo` không kèm ma, đưa danh sách quỹ theo loại (cổ phiếu, trái phiếu, cân bằng…) rồi hỏi người dùng chọn. Không tự chọn quỹ.
- Chỉ có 1 mã thì hỏi thêm. Có hơn 4 mã thì lấy 4 mã đầu và nói rõ.
- Mã không có trong danh sách (công cụ trả `thieu`): ghi lại và so các quỹ còn lại, nếu vẫn còn ít nhất 2 quỹ.

## Lấy dữ liệu (server dautucophieu-cong-khai, gọi song song được)

Với từng quỹ: `quy_mo` với ma là mã quỹ, so_ngay 30.

## Trình bày

1. **Bảng tổng quan**, mỗi quỹ một cột: tên, loại, công ty quản lý, NAV/đơn vị mới nhất kèm ngày, phí (%).
2. **Lợi nhuận công bố** (theo Fmarket, %): 1, 3, 6, 12, 36 tháng, từ đầu năm, bình quân năm 3 năm. Ô nào Fmarket để trống thì ghi "thiếu". Đây là số Fmarket công bố, không phải số tự tính.
3. **NAV trong kho**: NAV đầu và cuối của lịch sử có trong kho, ghi rõ hai ngày và thay đổi % giữa hai ngày đó. Lịch sử ngắn hoặc các quỹ có khoảng ngày khác nhau thì nói rõ là không so trực tiếp được.
4. **Danh mục đã công bố** (ghi kỳ công bố của từng quỹ):
   - tỷ trọng theo loại tài sản (cổ phiếu, trái phiếu, tiền…);
   - 5 cổ phiếu tỷ trọng lớn nhất và 3 ngành lớn nhất;
   - cổ phiếu mà từ hai quỹ trở lên cùng nắm, kèm tỷ trọng ở từng quỹ;
   - quỹ trái phiếu: các trái phiếu lớn nhất nếu có trong kho.
5. **Khác biệt chính**: 3 đến 5 gạch đầu dòng, chỉ nêu điều số trong các bảng cho thấy (phí cao hay thấp hơn, danh mục tập trung hơn, loại tài sản khác nhau). So quỹ khác loại (ví dụ cổ phiếu với trái phiếu) thì nói rõ là khác khẩu vị rủi ro, không so lợi nhuận trực tiếp.
6. **Thiếu**: mục nào thiếu thì ghi quỹ, mục và lý do nguyên văn.
7. **Nguồn**: Fmarket, thời điểm lấy NAV (lay_luc) và thời điểm lấy danh mục (danh_muc_lay_luc).

## Quy tắc

- Không đoán số, không nội suy, không lấy số từ kiến thức có sẵn hay nguồn ngoài.
- Mọi phép tính chỉ dùng số trong kho và ghi rõ ngày hoặc kỳ dùng để tính.
- Không xếp hạng quỹ, không khuyến nghị mua bán hay chuyển đổi quỹ, không dự báo lợi nhuận.
- Không dùng hay nhắc tới điểm quỹ do ứng dụng tự chấm; công cụ cũng không trả điểm này.
- Không hỏi, nhắc hay suy đoán quỹ người dùng đang nắm, giá vốn hay danh mục của họ.
