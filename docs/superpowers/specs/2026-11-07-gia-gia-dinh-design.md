# Giá giả định (07/11/2026)

Bước 3 của nhóm "dải phân vị định giá", dựng trên [dải phân vị](2026-11-07-dai-phan-vi-dinh-gia-design.md). Bạn nhập một mức giá, ứng dụng
cho biết P/B và P/E ở giá đó, phân vị trong từng khung, và chuyện gì xảy ra 12 tháng sau các lần trước bội số về mức đó. Chỉ dữ liệu công
khai, không đọc danh mục, không gọi AI, không phải dự báo hay khuyến nghị.

## Bội số tại giá giả định (`valuation/what_if.py`)
- Bội số = giá × số cổ phiếu hiện tại ÷ mẫu số của tuần mới nhất trong chuỗi theo tuần (lợi nhuận 4 quý hoặc năm; vốn chủ cuối quý hoặc
  năm). Ghi cơ sở và kỳ dùng, lợi nhuận hoặc vốn chủ trên mỗi cổ phiếu, và mức chênh so với giá đóng cửa tuần mới nhất.
- Mẫu số không dương (lỗ, vốn âm) thì không có bội số và ghi lý do.
- Phân vị: % số tuần trong khung có bội số ≤ mức giả định, cùng các khung và cùng ngưỡng 52 tuần như dải phân vị.

## Các đợt trước và kết quả 12 tháng
- Một đợt bắt đầu ở tuần đầu tiên bội số ≤ mức giả định sau khi đã ở trên mức đó (tuần không có số cũng cắt chuỗi). Chuỗi bắt đầu khi đã ở
  dưới mức thì không tính, vì không biết giá về vùng từ lúc nào.
- Đợt mới phải cách lần vào trước ít nhất 365 ngày, để kết quả 12 tháng không chồng nhau.
- Kết quả: giá đóng cửa tuần (đã điều chỉnh) ở tuần đầu tiên từ 365 ngày sau, trễ tối đa 14 ngày; xa hơn hoặc chưa tới thì đợt đó "chưa đủ
  12 tháng" và không tính. Lỗ sâu nhất: giá đóng cửa tuần thấp nhất tới lúc đó so với giá vào, bằng 0 nếu chưa từng thấp hơn.
- **Ngưỡng mẫu: 5 đợt.** Dưới 5 đợt đã có kết quả thì chỉ ghi "Có lãi x/y đợt — chưa đủ mẫu để tính tỉ lệ (cần ít nhất 5 đợt)", không hiện
  tỉ lệ và trung vị. Từ 5 đợt trở lên mới có tỉ lệ có lãi và trung vị. Luôn ghi số đợt, số đợt chưa đủ 12 tháng, kết quả tệ nhất, lỗ sâu
  nhất, và bảng từng đợt.
- Giới hạn ghi trên trang: giá đóng cửa tuần nên không thấy mức giảm trong tuần; chỉ lịch sử của chính mã đang niêm yết (mã đã hủy niêm yết
  không có trong mẫu).

## API và giao diện
- `GET /internal/fairvalue/whatif/{mã}/{giá}`: giá là số nguyên đồng, từ 1 đến 10.000.000 (ngoài khoảng trả 422); chỉ mã trong danh sách
  theo dõi. Trả cả `pe` và `pb`. Proxy web không chuyển query string, nên giá nằm trong đường dẫn.
- Trong khối Dải phân vị: các nút Tắt · Tự gõ giá · −5% · −10% · −15% · −20% (so với giá đóng cửa tuần mới nhất, làm tròn 10 đồng). Thẻ kết
  quả theo chỉ số đang chọn (P/B hoặc P/E); vạch nét đứt "giả định" trên biểu đồ dải.

## Ngoài phạm vi
Mốc giá quá khứ (bước 4).
