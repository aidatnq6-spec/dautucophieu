# so_sanh_nganh theo quý

Chủ sở hữu duyệt ngày 27/11/2026: Claude nói được một mã so với ngành qua nhiều quý, như đường trung vị trên biểu đồ ([2026-11-27-trung-vi-nganh-theo-quy-design.md](2026-11-27-trung-vi-nganh-theo-quy-design.md)).

- `so_sanh_nganh(ma, so_quy=4)`, `so_quy` 1–8. Mọi trường hiện có giữ nguyên (quý mới nhất: trung vị, tứ phân vị, thứ hạng).
- Thêm `theo_quy`: `quy` = `so_quy` quý gần nhất mà mã có số; `chi_so` = {mã chỉ số: {"gia_tri": [...], "trung_vi": [...]}} cùng thứ tự `quy`. Trung vị như `sector_history`: cùng nhóm, chỉ mã có số ở đúng quý, không gồm mã đang xem, tối thiểu 3; dưới đó `null`.
- `luu_y` nói cách tính và thứ hạng chỉ ở quý mới nhất. Skill `/dautu-ma` (So với ngành: xu hướng 4 quý của chỉ số lệch khỏi ngành), hướng dẫn Project, mô tả công cụ sửa theo; plugin 0.24.0.
