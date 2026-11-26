---
name: dautu-ma
description: Tóm tắt một mã cổ phiếu HOSE từ dữ liệu công khai trên máy — hồ sơ, giá, kết quả kinh doanh, EPS, cổ tức, sự kiện, cổ đông, giao dịch nội bộ. Dùng khi người dùng gõ /dautu-ma <MÃ> hoặc nhờ tóm tắt nhanh một mã.
argument-hint: <MÃ> (ví dụ FPT)
---

# Tóm tắt một mã: $ARGUMENTS

Mã là phần người dùng gõ sau lệnh, viết hoa. Không có mã thì hỏi lại, không tự chọn.

## Lấy dữ liệu (server dautucophieu-cong-khai, gọi song song được)

1. `thong_tin_ma`: niêm yết HOSE, ngành ICB, VN30/VN100.
2. `gia_ngay` với so_phien 20.
3. `bao_cao_tai_chinh` với ky "quy", so_ky 4; thêm ky "nam", so_ky 3.
4. `chi_so_tai_chinh` với so_ky 4.
5. `eps_co_tuc` với so_ky 8.
6. `su_kien_doanh_nghiep`, `co_dong_ban_lanh_dao`, `giao_dich_noi_bo`.

## Trình bày (tiếng Việt, gọn, bảng khi có nhiều số)

1. **Hồ sơ**: ngành, nhóm chỉ số.
2. **Giá**: phiên mới nhất trong kho, giá đóng, cao/thấp 20 phiên. Thay đổi % chỉ tính từ hai giá trong kho và ghi rõ hai phiên dùng để tính.
3. **Kết quả kinh doanh**: 4 quý và 3 năm gần nhất với các dòng có trong kho (doanh thu, lợi nhuận, dòng tiền…). Số gốc là đồng; đổi sang tỷ đồng khi trình bày và ghi đơn vị.
4. **EPS, cổ tức, số cổ phiếu lưu hành**; nếu có shares_check thì nêu hai nguồn đang lệch.
5. **Sự kiện**: sắp tới trước, rồi gần đây nhất.
6. **Cổ đông lớn** (tối đa 5) và **giao dịch nội bộ** gần nhất.
7. **Thiếu**: mỗi công cụ trả `thieu` thì ghi tên mục và lý do nguyên văn.
8. **Nguồn**: nguồn và thời điểm lấy của từng nhóm số.

## Quy tắc

- Không đoán số: không nội suy, không ước lượng, không lấp chỗ trống bằng kiến thức có sẵn hay nguồn ngoài.
- Không khuyến nghị mua bán, không đặt giá mục tiêu.
- Không hỏi, nhắc hay suy đoán danh mục, giá vốn, danh sách theo dõi của người dùng.
