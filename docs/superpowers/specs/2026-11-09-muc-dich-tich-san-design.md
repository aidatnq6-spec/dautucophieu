# Mục đích từng khoản tiền và Kế hoạch tích sản

Chủ sở hữu duyệt ngày 09/11/2026. Ở Hồ sơ & rủi ro. Dữ liệu cá nhân, không gửi cho AI. Cả hai chỉ hiển thị thêm: không đổi Sổ tài sản, Tháp tài sản, số tiền dành cho cổ phiếu hay Dòng tiền thụ động.

## Mục đích từng khoản tiền
- Lưu ở `settings/money_purposes`: danh sách mục đích do chủ sở hữu đặt tên (không có sẵn), mỗi mục đích có thể đánh dấu "xem như đã chi", và mỗi dòng của Sổ tài sản gắn tối đa một mục đích.
- Giá trị từng dòng lấy đúng như Sổ tài sản: sổ tiền gửi theo gốc, chứng chỉ quỹ theo NAV, vàng theo giá mua vào; dòng chưa có giá thì theo vốn đã mua và ghi rõ.
- Hiện tổng theo mục đích, phần chưa gắn, tổng Sổ tài sản, phần xem như đã chi và phần còn lại là của mình. Chỉ tính các dòng trong Sổ tài sản; cổ phiếu và tiền trong tài khoản chứng khoán không thuộc phép tính này.

## Kế hoạch tích sản
- Lưu ở `settings/accumulation`: các kế hoạch (vàng theo số chỉ mỗi tháng, chứng chỉ quỹ theo số tiền mỗi tháng; ngày 1 đến 28; tháng bắt đầu; loại giá vàng hoặc mã quỹ, không bắt buộc) và từng lần mua (ngày, tiền bỏ ra, số chỉ hoặc số đơn vị).
- Mỗi tháng từ tháng bắt đầu là đã mua, thiếu, chưa mua, hoặc đang chờ (tháng hiện tại trước ngày mua); có chuỗi tháng liên tục.
- Giá vốn bình quân = tổng tiền ÷ tổng số lượng các lần đã ghi. Giá trị hiện tại theo giá mua vào công khai hoặc NAV mới nhất; không có giá thì không tính và nói rõ vì sao.
- Nhắc: Telegram tối đa một lần mỗi kế hoạch mỗi tháng, từ ngày mua trong tháng khi tháng đó chưa đủ, theo lượt chạy lịch; đồng thời hiện ở Việc cần xem. Không nói nên mua hay không.
- Lần mua không tự cộng vào Sổ tài sản. **Cộng vào Sổ tài sản** (chủ sở hữu duyệt 09/11/2026): nút ở từng lần mua, hỏi xác nhận rồi cộng tiền vào vốn đã mua và số chỉ, số đơn vị vào số lượng của dòng được chọn, hoặc tạo dòng mới mang tên kế hoạch; Tháp tài sản tính lại theo Sổ.
  - Chỉ chọn được dòng cùng loại giá vàng hoặc cùng mã quỹ. Sổ và dấu "đã cộng" ghi trong một giao dịch nên mỗi lần mua chỉ cộng được một lần.
  - Sổ chưa có dữ liệu thì không cộng, vì tạo Sổ lần đầu sẽ làm các lớp khác của Tháp về 0. Số lượng quá 2 chữ số thập phân thì từ chối, không làm tròn. Xóa lần mua đã cộng không tự trừ ở Sổ, có báo khi xóa.
