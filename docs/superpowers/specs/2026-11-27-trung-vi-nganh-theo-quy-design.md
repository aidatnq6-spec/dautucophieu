# Trung vị ngành theo quý trên biểu đồ Bảng số tài chính

Chủ sở hữu chọn ngày 27/11/2026 (cách A): thấy một mã so với ngành qua nhiều quý, không chỉ quý mới nhất.

| | Cách | Được | Mất |
|---|---|---|---|
| **A (chọn)** | Đường trung vị ngành nét đứt, cùng màu, trên biểu đồ khi chọn vẽ một chỉ số | Thấy xu hướng ngay; bảng không đổi | Biểu đồ thêm đường |
| B | Bảng "So với ngành qua các quý" dưới biểu đồ | Rõ số, có thứ hạng | Phải đọc bảng; trang dài |
| C | Dòng "Trung vị ngành" dưới mỗi chỉ số trong bảng | Xem và vẽ được như mọi dòng | Bảng dài gấp đôi phần chỉ số |

## Thiết kế

- Mỗi quý của bảng chỉ số, trung vị tính như cột "Trung vị ngành" hiện nay (`market/sector_compare`): cùng nhóm (ICB cấp 2; công ty chứng khoán ICB cấp 4 Dịch vụ đầu tư), chỉ các mã có số ở đúng quý đó, không gồm mã đang xem, tối thiểu 3; dưới 3 thì quý đó không có điểm (đường đứt khúc, không nối qua).
- Route `/fairvalue/ratios/{mã}`: `sector.history` = {mã chỉ số: [trung vị theo đúng thứ tự `quarters`]}, chỉ cho các chỉ số có cột trung vị.
- Biểu đồ: chỉ số đang vẽ có trung vị thì thêm đường nét đứt cùng màu, tên "Trung vị ngành"; chỉ ở chế độ Quý. Di chuột vào một quý hiện cả hai số. Chú thích biểu đồ nói đường nét đứt là trung vị ngành của từng quý.
- Không đổi bảng, cột trung vị quý mới nhất, `so_sanh_nganh`.
