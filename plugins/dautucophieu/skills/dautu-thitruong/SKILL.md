---
name: dautu-thitruong
description: "Bảng nhanh thị trường từ dữ liệu công khai trên máy — VN-Index, P/E và P/B của VN-Index và VN30, chỉ số châu Á, giá vàng, OMO, tự doanh, khối ngoại. Dùng khi người dùng gõ /dautu-thitruong hoặc hỏi thị trường hôm nay thế nào."
argument-hint: "(không cần)"
---

# Bảng nhanh thị trường

## Lấy dữ liệu (server dautucophieu-cong-khai, gọi song song được)

1. `gia_ngay` với ma "VNINDEX", so_phien 20.
2. `dinh_gia_chi_so`: VNINDEX pe, VNINDEX pb, VN30 pe, VN30 pb, mỗi chuỗi so_diem 20.
3. `chi_so_chau_a`, `gia_vang`, `omo` với so_phien 5.
4. `tu_doanh` và `khoi_ngoai`, mỗi công cụ so_phien 60.

## Trình bày

1. **VN-Index**: phiên mới nhất trong kho, điểm đóng, khối lượng; thay đổi so với phiên trước và so với 20 phiên trước, ghi rõ hai phiên dùng để tính.
2. **Định giá**: bảng P/E, P/B mới nhất của VN-Index và VN30, kèm thấp nhất và cao nhất trong 20 điểm.
3. **Châu Á**: tên, giá, % thay đổi như trong kho.
4. **Vàng**: giá mua/bán từng loại, đơn vị và thời điểm.
5. **OMO**: các phiên gần nhất, khối lượng và lãi suất.
6. **Tự doanh và khối ngoại 60 phiên**: với mỗi bên, tổng mua, bán, ròng toàn sàn (tỷ đồng), 5 mã mua ròng và 5 mã bán ròng mạnh nhất; ghi phiên đầu, phiên cuối, số phiên thiếu và số phiên chậm.
7. **Thiếu**: mục nào trả `thieu` thì ghi lý do nguyên văn; phiên trống giữa các ngày thì nói là thiếu, không lấp.
8. **Nguồn** và thời điểm lấy.

## Quy tắc

- Không đoán số, không nội suy, không dự báo, không khuyến nghị mua bán.
- Không nhắc tới danh mục hay giao dịch của người dùng.
