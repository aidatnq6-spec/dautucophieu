# Trung vị ngành cho công ty chứng khoán

Chủ sở hữu duyệt ngày 27/11/2026: so sánh một công ty chứng khoán với các công ty chứng khoán HOSE khác, như ngân hàng ([2026-11-27-trung-vi-nganh-ngan-hang-design.md](2026-11-27-trung-vi-nganh-ngan-hang-design.md)).

## Nhóm so sánh

ICB cấp 4 "Dịch vụ đầu tư" (8777) của VNDirect: 21 mã HOSE ngày 27/11/2026 (SSI, VCI, HCM, VND, VIX, FTS, TCX, VPX…), cả 21 có đủ 5 chỉ số chứng khoán quý 2 và quý 3/2026. Không dùng cấp 2 "Dịch vụ tài chính" vì lẫn EVF (cấp 4 "Tài chính cá nhân", bộ chỉ số khác).

## Thiết kế

1. `hose_listing` lưu thêm `icb4_codes` (mã ICB cấp 4 của từng mã; một lượt gọi `industry_classification?q=industryLevel:4`). Bản lưu chưa có `icb4_codes` thì làm mới ở lượt kế tiếp. Ngành cấp 2 giữ nguyên.
2. `financial-ratios-sync` tải thêm mọi mã HOSE có cấp 4 là 8777, với `kind: "securities"`.
3. `compare_sector` nhận công ty chứng khoán: mã phải thuộc 8777 (không thì `thieu` kèm lý do); so với các mã 8777 khác có số ở đúng quý mới nhất; tối thiểu 3. Tên nhóm "Dịch vụ đầu tư (chứng khoán)", mã nhóm "8777". 5 chỉ số: các dòng `DISPLAY["securities"]` (ROAA, ROAE, biên lợi nhuận ròng, cho vay / vốn chủ, vốn chủ / tổng tài sản).
4. Bảng số tài chính của công ty chứng khoán, chế độ Quý: cột "Trung vị ngành" và chú thích như ngân hàng. `so_sanh_nganh`, skill `/dautu-ma`, hướng dẫn Project sửa theo; plugin 0.20.0.

## Không làm

- Không đổi cách các phần khác xếp EVF vào nhóm "chứng khoán".
- Không làm bảo hiểm (5 mã).
- Khi không đủ 3 mã, cột vẫn hiện, ô "—" (spec 26/11).
