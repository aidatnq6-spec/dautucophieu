# Quy tắc thị trường dùng trong ứng dụng

Tra cứu ngày 2026-10-25. Số liệu máy đọc: `config/market-rules-hose.json` (ghim digest) và `config/trading-calendar-hose-2026.json`. Mỗi con số ghi căn cứ và mức kiểm chứng; khi quy định đổi, tạo phiên bản cấu hình mới thay vì sửa tại chỗ.

## Thông số và mức kiểm chứng

| Thông số | Giá trị | Căn cứ | Mức kiểm chứng |
|---|---|---|---|
| Lô chẵn (khớp lệnh) | 100 cổ phiếu; tối đa 500.000/lệnh | Quy chế giao dịch HOSE 352/QĐ-SGDHCM ngày 30/6/2021, Điều 8 khoản 1 | Văn bản gốc 2021; tài liệu DNSE 04/2025 xác nhận giữ nguyên khi vận hành KRX (05/5/2025) |
| Lô lẻ | 1–99 cổ phiếu, chỉ lệnh LO | Quy chế niêm yết và giao dịch 22/QĐ-HĐTV ngày 16/3/2026 của SGDCK Việt Nam (hiệu lực từ ngày ký), Điều 34 | Văn bản gốc hiện hành (đọc qua luatvietnam.vn) |
| Bước giá cổ phiếu | < 10.000: 10 đ; 10.000–49.950: 50 đ; ≥ 50.000: 100 đ | 352/QĐ-SGDHCM Điều 8 khoản 4 | Như lô chẵn |
| Biên độ ngày | ±7% giá tham chiếu; trần làm tròn xuống, sàn làm tròn lên theo bước giá | 352/QĐ-SGDHCM Điều 9; công thức tại 22/QĐ-HĐTV/2026 Điều 32 | Như lô chẵn. Trường hợp đặc biệt (ngày đầu niêm yết, sau tạm ngừng ≥ 25 phiên, ngày không hưởng quyền…) theo Phụ lục III — **chưa đọc được**, ứng dụng không tính các trường hợp này |
| Chu kỳ thanh toán | T+2 | Tài liệu công ty chứng khoán (VNDirect, BSC); văn bản gốc Thông tư 119/2020/TT-BTC (sửa đổi bởi 18/2025/TT-BTC, hiệu lực 05/5/2025) | **Chỉ nguồn thứ cấp** — chưa đối chiếu điều khoản gốc |
| Thuế bán chứng khoán | 0,1% giá chuyển nhượng từng lần | Luật Thuế TNCN 109/2025/QH15, hiệu lực 01/7/2026, Điều 13 | Nội dung luật trích qua trang pháp luật; nghị định hướng dẫn đang dự thảo |
| Thuế cổ tức | 5% thu nhập từ đầu tư vốn | Luật 109/2025/QH15, Điều 12 | Như trên |
| Phí môi giới | Theo biểu phí của công ty chứng khoán của bạn | Nhập trong Cài đặt | Không có mức mặc định |

## Lịch nghỉ giao dịch 2026

Theo Thông báo 2294/TB-SGDHCM ngày 09/12/2025 và bản cập nhật Tết Dương lịch ngày 25/12/2025 (13 ngày nghỉ trong tuần): 01–02/01; 16–20/02 (Tết Nguyên đán); 27/04 (Giỗ Tổ, nghỉ bù); 30/04–01/05; 31/08–02/09. Thứ Bảy làm bù 10/01 và 22/08 **không giao dịch**. Đọc qua bản đăng lại của CafeF, Vietstock, Thư viện Pháp luật; chưa mở được bản gốc trên hsx.vn.

Lịch năm sau: khi HOSE công bố (thường tháng 12), tạo `config/trading-calendar-hose-<năm>.json` mới. Lịch tự động dùng `data\trading-calendar.json` nếu bạn tạo riêng, nếu không thì dùng file của năm hiện tại trong `config\`.

## Ứng dụng dùng các quy tắc thế nào

- Phí, thuế bán, thuế cổ tức trong **sổ giao dịch** vẫn là số thực tế trên chứng từ; tỷ lệ trong cấu hình chỉ dùng để ước tính.
- Ngày thanh toán của từng lệnh vẫn lấy từ sao kê. Tiền có thể mua dùng số bạn xác nhận cho đúng ngày, nếu không thì dùng ngày thanh toán đã ghi; lệnh bán thiếu ngày thanh toán làm tiền khả dụng ở trạng thái "chưa rõ". Ứng dụng không tự suy T+2.
- Khuyến nghị mua đề xuất số tiền và **gợi ý** số lượng theo lô chẵn (hoặc lô lẻ khi chưa đủ 100 cổ phiếu), đã tính phí của bạn. Số lượng vẫn cần bạn xác nhận với công ty chứng khoán trước khi đặt lệnh.
- Cổ tức, cổ phiếu thưởng, tách/gộp ghi theo chứng từ; quyền mua, đổi mã, sáp nhập bị chặn phân tích cho đến khi hỗ trợ.

## Còn phải kiểm chứng

1. Phụ lục III của Quy chế 22/QĐ-HĐTV/2026: thông số chính thức hiện hành (lô, bước giá, biên độ, biên độ đặc biệt, giờ giao dịch).
2. Điều khoản thời hạn thanh toán trong Thông tư 119/2020 sau sửa đổi 18/2025.
3. Bản gốc thông báo lịch nghỉ 2026 trên hsx.vn.
4. Nghị định hướng dẫn Luật Thuế TNCN 2025 về chứng khoán khi ban hành.

## Nguồn

- [Quyết định 22/QĐ-HĐTV 2026 — Quy chế niêm yết và giao dịch chứng khoán](https://luatvietnam.vn/chung-khoan/quyet-dinh-22-qd-hdtv-2026-ban-hanh-quy-che-niem-yet-va-giao-dich-chung-khoan-430733-d1.html)
- [Quyết định 22/QĐ-HĐTV 2025 (bị thay thế)](https://luatvietnam.vn/chung-khoan/quyet-dinh-22-qd-hdtv-2025-ban-hanh-quy-che-niem-yet-va-giao-dich-chung-khoan-399805-d1.html)
- [Quy chế giao dịch HOSE 352/QĐ-SGDHCM (bản PDF do MBS đăng)](https://www.mbs.com.vn/files/uploads/2025/04/352_qd-sgdhcm_quy-che-giao-dich-ck-tai-hsx.pdf)
- [DNSE — Cập nhật quy định giao dịch trên hệ thống KRX, 04/2025](https://cdn.dnse.com.vn/dnse-news/2023/10/DNSE_Cap-nhat-quy-dinh-giao-dich-sau-KRX_2025.pdf)
- [CafeF — HOSE thông báo lịch nghỉ giao dịch năm 2026](https://cafef.vn/du-lieu/hose-2678210/hose-thong-bao-lich-nghi-giao-dich-nam-2026.chn)
- [Vietstock — HOSE cập nhật lịch nghỉ Tết Dương lịch 2026](https://vietstock.vn/2025/12/hose-thong-bao-ve-viec-cap-nhat-lich-nghi-giao-dich-tet-duong-lich-nam-2026-830-1384826.htm)
- [Thư viện Pháp luật — Luật Thuế TNCN 109/2025/QH15](https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Luat-Thue-thu-nhap-ca-nhan-2025-so-109-2025-QH15-665870.aspx)
- [Thư viện Pháp luật — Thông tư 18/2025/TT-BTC](https://thuvienphapluat.vn/van-ban/Chung-khoan/Thong-tu-18-2025-TT-BTC-sua-doi-Thong-tu-119-2020-TT-BTC-dang-ky-luu-ky-bu-tru-chung-khoan-654990.aspx)
- [BSC — Chu kỳ thanh toán T+2](https://www.bsc.com.vn/tin-tuc/tin-chi-tiet/94965-chu-ky-thanh-toan-t2-la-gi-khi-nao-tien-va-co-phieu-ve-tai-khoan/)
