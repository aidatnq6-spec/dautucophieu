# P/E, P/B so với lịch sử trên Bảng số tài chính

Chủ sở hữu duyệt ngày 26/11/2026: hiện P/E và P/B của mã so với chính lịch sử của nó, cạnh thẻ P/E · P/B · EV/EBITDA của Bảng số tài chính.

## Cách tính (dùng chung với công cụ MCP `dinh_gia_lich_su`, `market/valuation_history.py`)

Mỗi giá đóng cửa trong `index-history/` (cuối tháng từ 2018): vốn hóa = giá chưa điều chỉnh × số cổ phiếu của quý đã công bố (45 ngày sau khi kết thúc quý), nhân thêm các đợt thưởng hay cổ tức cổ phiếu có ngày không hưởng quyền sau cuối quý; P/E = vốn hóa ÷ LNST công ty mẹ 4 quý; P/B = vốn hóa ÷ vốn chủ công ty mẹ. Bỏ tháng thiếu quý và P/E khi lỗ 4 quý. Trung vị, không dùng trung bình.

## Route

`GET /fairvalue/statements/{mã}` trả thêm `own_history`: `{"date", "pe": {"now", "median_3y", "median_5y", "lower_3y"}, "pb": {...}}`, chuỗi rỗng thành null; không có dữ liệu thì `own_history: null`.

## Giao diện

- Hai thẻ cạnh "P/E · P/B · EV/EBITDA": "P/E so với lịch sử" và "P/B so với lịch sử", mỗi thẻ: giá trị hiện tại (tự tính, ngày cuối của chuỗi) · trung vị 3 năm · trung vị 5 năm; dòng nhỏ: "x/n tháng trong 3 năm thấp hơn".
- Thẻ chỉ hiện khi có trung vị; chú thích dưới bảng nói số tự tính, cách tính và ngày cuối của chuỗi (có thể cũ hơn giá trên thẻ P/E hiện tại).

## Làm mới (27/11/2026)

`index-history/` trước chỉ được dựng một lần bằng lệnh `index-history`, nên điểm hiện tại ngày càng cũ. Lượt 20:00 nay chạy `index-history-sync --limit 60` (`market/index_history.refresh_history`): mã chưa có trước, rồi mã lấy cách đây 7 ngày trở lên, cũ nhất trước; 406 mã HOSE xong trong khoảng một tuần, hai lượt gọi VNDirect mỗi mã. Mã tải lỗi giữ bản cũ và được báo. Chạy trước 15:00 thì không giữ giá của phiên đang giao dịch. Lệnh `index-history` vẫn dùng để dựng lại chuỗi VN-Index trước 2018. Tới hết 04/12/2026, giới hạn là 120 mã mỗi đêm để vòng làm mới đầu tiên xong trong khoảng 4 đêm; từ 05/12 trở về 60.
