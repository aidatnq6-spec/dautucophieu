# Khối ngoại cho Claude (công cụ MCP `khoi_ngoai`)

Chủ sở hữu duyệt ngày 27/11/2026: như `tu_doanh` ([2026-11-27-tu-doanh-mcp-design.md](2026-11-27-tu-doanh-mcp-design.md)), đọc kho `data/foreign/` ([2026-11-27-ngoai-tu-doanh-20-phien-design.md](2026-11-27-ngoai-tu-doanh-20-phien-design.md)).

- `khoi_ngoai(so_phien=60, ma=None)`, `so_phien` 1–250: cùng khoảng phiên, `phien_thieu` (gồm phiên VNDirect trả mọi mã bằng 0), `chua_hoi`, `cham_phien`, `so_phien`/`so_phien_hoi` như `tu_doanh`.
- Toàn sàn = tổng các mã cổ phiếu (như dòng Khối ngoại của bản tin); không có `phien_khong_khop`.
- Không có `ma`: 10 mã mua ròng, 10 mã bán ròng mạnh nhất theo giá trị. Có `ma`: từng phiên của mã và tổng; phiên không có dòng của mã là không giao dịch, khác phiên thiếu.
- `tu_doanh` và `khoi_ngoai` dùng chung một phần cộng dồn. Hướng dẫn Project, skill `/dautu-thitruong` (dòng khối ngoại 60 phiên) sửa theo; plugin 0.22.0.
