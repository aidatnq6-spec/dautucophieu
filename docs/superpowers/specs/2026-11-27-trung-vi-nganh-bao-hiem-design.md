# Trung vị ngành cho bảo hiểm

Chủ sở hữu duyệt ngày 27/11/2026: như ngân hàng ([2026-11-27-trung-vi-nganh-ngan-hang-design.md](2026-11-27-trung-vi-nganh-ngan-hang-design.md)), nhóm so là cả 5 mã HOSE ngành ICB cấp 2 "Bảo hiểm" (BIC, BMI, BVH, MIG, PGI), gồm cả BVH (phần lớn nhân thọ) dù khó so với phi nhân thọ: bỏ BVH thì chỉ còn 3 mã khác và quý nào một mã chưa có số (BIC quý 3/2026) thì không có trung vị.

- `financial-ratios-sync` tải thêm mọi mã HOSE ngành "Bảo hiểm" (`kind: "insurance"`); lỗi của mã không theo dõi không làm bước báo lỗi.
- `compare_sector` nhận bảo hiểm: 5 chỉ số `DISPLAY["insurance"]` (tỷ lệ kết hợp, biên lợi nhuận ròng, ROAA, ROAE, vốn chủ / tổng tài sản), so với các mã bảo hiểm khác có số ở đúng quý, tối thiểu 3.
- Bảng số tài chính của bảo hiểm, chế độ Quý: cột "Trung vị ngành"; chú thích thêm "nhóm gồm cả bảo hiểm nhân thọ (BVH) và phi nhân thọ, tỷ lệ kết hợp và biên khó so trực tiếp".
- `so_sanh_nganh`, skill `/dautu-ma`, hướng dẫn Project sửa theo; plugin 0.23.0.
