---
name: dautu-ma
description: "Tóm tắt một mã cổ phiếu HOSE từ dữ liệu công khai trên máy — hồ sơ, giá, kết quả kinh doanh, EPS, cổ tức, sự kiện, cổ đông, giao dịch nội bộ. Dùng khi người dùng gõ /dautu-ma <MÃ> hoặc nhờ tóm tắt nhanh một mã."
argument-hint: "<MÃ> (ví dụ FPT)"
---

# Tóm tắt một mã: $ARGUMENTS

Mã là phần người dùng gõ sau lệnh, viết hoa. Không có mã thì hỏi lại, không tự chọn.

## Lấy dữ liệu (server dautucophieu-cong-khai, gọi song song được)

1. `thong_tin_ma`: niêm yết HOSE, ngành ICB, VN30/VN100.
2. `gia_ngay` với so_phien 20.
3. `bao_cao_tai_chinh` với ky "quy", so_ky 8 (đủ để so cùng kỳ năm trước); thêm ky "nam", so_ky 3.
4. `chi_so_tai_chinh` với so_ky 4: ROAE, ROIC, biên lợi nhuận, nợ vay/vốn chủ, khả năng trả lãi… theo tên ở ten_chi_so.
5. `eps_co_tuc` với so_ky 8.
6. `su_kien_doanh_nghiep`, `co_dong_ban_lanh_dao`, `giao_dich_noi_bo`.
7. `dinh_gia_ma`: vốn hoá, P/E, P/B do VNDirect công bố; `so_sanh_nganh`: vị trí của mã trong ngành ICB.
9. `thuyet_minh` 4 quý: khoản nào làm doanh thu, chi phí tài chính hay nợ vay đổi lớn.
8. `lich_su_gia` từ 3 năm trước: giá cuối tháng, đã điều chỉnh khi kho có (dieu_chinh), kèm các đợt thưởng hay phát hành.

## Trình bày (tiếng Việt, gọn, bảng khi có nhiều số)

1. **Hồ sơ**: ngành, nhóm chỉ số.
2. **Giá**: phiên mới nhất trong kho, giá đóng, cao/thấp 20 phiên. Thay đổi % chỉ tính từ hai giá trong kho và ghi rõ hai phiên dùng để tính.
   Giá 3 năm (cuối tháng): nêu cao, thấp kèm tháng. Giá đã điều chỉnh thì được tính % thay đổi 1 và 3 năm (ghi hai tháng dùng để tính); giá chưa điều chỉnh mà có đợt thưởng hay phát hành ở giữa thì không tính % qua đợt đó và ghi rõ lý do.
3. **Kết quả kinh doanh**: 4 quý gần nhất kèm cùng kỳ năm trước, và 3 năm gần nhất với các dòng có trong kho (doanh thu, lợi nhuận, dòng tiền…). Số gốc là đồng; đổi sang tỷ đồng khi trình bày và ghi đơn vị.
4. **So với ngành**: các chỉ số mà mã nằm ngoài khoảng tứ phân vị 25–75% của ngành, kèm trung vị, số doanh nghiệp và quý so.
   **Định giá**: vốn hoá, P/E, P/B từ `dinh_gia_ma` kèm ngày. Nếu canh_bao_loi_nhuan_ngoai_ban_hang của `bao_cao_tai_chinh` vượt ngưỡng thì nêu tỷ lệ, kỳ và nói P/E dựa nhiều vào lợi nhuận không từ bán hàng. Thiếu thì ghi thiếu; nếu tự tính thì ghi rõ là tự tính và công thức.
5. **EPS, cổ tức, số cổ phiếu lưu hành**; nếu có shares_check thì nêu hai nguồn đang lệch.
6. **Sự kiện**: sắp tới trước, rồi gần đây nhất.
7. **Cổ đông lớn** (tối đa 5) và **giao dịch nội bộ** gần nhất.
8. **Thiếu**: mỗi công cụ trả `thieu` thì ghi tên mục và lý do nguyên văn.
9. **Nguồn**: nguồn và thời điểm lấy của từng nhóm số.

## Quy tắc

- Không đoán số: không nội suy, không ước lượng, không lấp chỗ trống bằng kiến thức có sẵn hay nguồn ngoài.
- Lợi nhuận cho EPS, P/E là npat_parent (LNST công ty mẹ). equity là vốn chủ GỒM cổ đông không kiểm soát: vốn chủ công ty mẹ = equity − minority_equity cùng kỳ. Xem pham_vi và ten_dong mà công cụ trả về.
- Chỉ nói một kỳ "không có trong kho" khi công cụ trả `thieu` cho đúng kỳ đó; kỳ chỉ nằm ngoài số kỳ đã xin thì gọi lại với so_ky lớn hơn.
- Cổ tức cổ đông nhận lấy từ dividends của `eps_co_tuc`; dòng dividends_paid của BCTC có thể gồm tiền trả cho cổ đông không kiểm soát.
- Điều gì chỉ là suy đoán thì ghi "Suy luận:" ở đầu câu.
- Không khuyến nghị mua bán, không đặt giá mục tiêu.
- Không hỏi, nhắc hay suy đoán danh mục, giá vốn, danh sách theo dõi của người dùng.
