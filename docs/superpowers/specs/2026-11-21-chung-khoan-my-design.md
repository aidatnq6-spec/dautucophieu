# Chứng khoán Mỹ (21/11/2026)

Chủ sở hữu duyệt ngày 21/11/2026 (kaizen từ FireAnt, đề xuất 6).

## Hành vi
- `macro-sync` đọc thêm 3 chuỗi ngày của FRED: `SP500` (S&P 500), `NASDAQCOM` (Nasdaq Composite), `DJIA` (Dow Jones), qua CSV FRED
  đã dùng, và lưu vào kho vĩ mô (`us_sp500`, `us_nasdaq`, `us_dow`, giữ 400 phiên). Ngày nghỉ FRED ghi "." thì bỏ qua, không lấp.
- Trang Vĩ mô có khối **Chứng khoán Mỹ**, đặt ngay trước khối Chứng khoán châu Á. Mỗi chỉ số có:
  - điểm đóng cửa và **ngày phiên** (FRED có ngày, khác với VNDirect cho châu Á);
  - thay đổi so với phiên trước;
  - thay đổi so với giá đóng cửa cuối cùng vào hoặc trước 30 ngày trước;
  - nhãn "số cũ" khi phiên cuối đã quá 7 ngày.
- Quy tắc lỗi của `macro-sync`: một chỉ số Mỹ đọc lỗi nhưng còn số trong 7 ngày là "trễ" (bước vẫn đạt); không có số trong 7 ngày là
  "quá hạn" (bước báo lỗi).

## Trong bản tin sau phiên (duyệt cùng ngày)
- Ảnh chụp phiên lưu mục `us` (số `macro-sync` đã lưu trong cùng lượt, không đọc mạng thêm).
- Tin Telegram và bản tin trên web có một dòng ngay sau dòng châu Á, ví dụ "Mỹ (FRED): S&P 500 −2,02% (phiên 19/11) · …". Mỗi chỉ số
  ghi ngày phiên của nó; chỉ số quá 7 ngày bị bỏ khỏi dòng.

## Không làm
Không thêm chỉ số châu Âu (chưa có nguồn công khai tương đương).
