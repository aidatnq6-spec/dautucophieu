# Cùng chiều cho Claude (công cụ MCP `cung_chieu`)

Chủ sở hữu duyệt ngày 27/11/2026: dùng lại phép tính "Cùng chiều 20 phiên" của Bản tin ([2026-11-27-ngoai-tu-doanh-cung-chieu-design.md](2026-11-27-ngoai-tu-doanh-cung-chieu-design.md)).

- `cung_chieu(so_phien=20, so_ma=5)`, `so_phien` 1–250, `so_ma` 1–20: khoảng kết thúc ở phiên mới nhất cả `data/foreign` và `data/proprietary` có số; phiên một bên thiếu bị bỏ ở cả hai và được đếm; số phiên chậm so với phiên HOSE gần nhất đã đóng cửa.
- Trả `cung_mua_rong`, `cung_ban_rong`: mỗi mã có ròng khối ngoại, ròng tự doanh (đồng), xếp theo tổng hai bên. Không đánh dấu mã theo dõi.
- `/dautu-thitruong` thêm dòng cùng chiều 20 phiên; hướng dẫn Project, mô tả công cụ; plugin 0.25.0.
