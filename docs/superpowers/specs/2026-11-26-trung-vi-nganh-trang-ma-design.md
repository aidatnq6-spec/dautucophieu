# Trung vị ngành trên Bảng số tài chính

Chủ sở hữu duyệt ngày 26/11/2026: cạnh 12 dòng "Chỉ số tài chính (VNDirect)" của doanh nghiệp thường, thêm một cột trung vị của các doanh nghiệp cùng ngành.

## Cách tính (dùng chung với công cụ MCP `so_sanh_nganh`, `market/sector_compare.py`)

- Ngành ICB cấp 2 từ `data/hose-listing.json`; chỉ số từ `data/financial-ratios-general/`.
- Quý: quý mới nhất của mã. Chỉ các doanh nghiệp cùng ngành có số ở đúng quý đó; không gồm mã đang xem; cần ít nhất 3 doanh nghiệp, không thì để "—".
- Số giữ nguyên như VNDirect; trung vị là phép tính thống kê trên các số đó.

## Route

`GET /fairvalue/ratios/{mã}` của doanh nghiệp thường trả thêm `sector`: `{"name", "quarter", "peers", "medians": {mã chỉ số: trung vị hoặc null}, "counts": {mã chỉ số: số doanh nghiệp}}`. Không có ngành hay không đủ số thì `sector: null` hoặc trung vị null. Mã tài chính không có trường này.

## Giao diện

- Chế độ Quý, khi có `sector`: thêm cột "Trung vị ngành Qx/yy" sau các cột quý (và sau cột dự báo nếu có), trước "Xu hướng". Chỉ 12 dòng chỉ số VNDirect có số, cùng định dạng với dòng đó; các dòng báo cáo tài chính để trống.
- Chú thích: trung vị các doanh nghiệp cùng ngành ICB cấp 2 trên HOSE (tên ngành) có số ở quý đó, không gồm mã này, n doanh nghiệp; không có nghĩa là tốt hay xấu.

Từ 27/11/2026 ngân hàng cũng có cột này, so với các ngân hàng HOSE: [2026-11-27-trung-vi-nganh-ngan-hang-design.md](2026-11-27-trung-vi-nganh-ngan-hang-design.md).
