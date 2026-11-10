# Sổ cho thuê căn hộ

Chủ sở hữu duyệt ngày 10/11/2026. Ở Hồ sơ & rủi ro, thẻ Tài sản. Lưu ở `settings/rental_book`; nằm trong bản sao lưu mã hóa; không gửi cho AI.

- Mỗi phòng: tên, khách thuê (trống là phòng trống), liên hệ, giá thuê mỗi tháng, ngày thu hằng tháng, ngày bắt đầu và hết hợp đồng, tiền cọc (để trống thì bằng 1 tháng tiền thuê, theo cách chủ sở hữu đang làm), môi giới và hoa hồng, ghi chú.
- Mỗi lần thu tiền là một dòng: phòng, tiền thuê của tháng nào, số tiền, ngày thu. Một tháng có thể thu nhiều lần.
- Mỗi phòng có “theo dõi thu tiền từ tháng” (phòng mới: tháng nhập; sửa được). Tiền thu trước mốc này nằm ở file Excel của chủ sở hữu, nên tháng chưa ghi trước mốc không bị coi là nợ (sửa 10/11/2026 sau khi chủ sở hữu báo nợ sai).
- Tháng tính từ ngày bắt đầu hợp đồng hiện tại (không trước mốc theo dõi) đến tháng này (tối đa 24 tháng, không quá ngày hết hợp đồng): đã thu, thu thiếu, chưa thu, hoặc chờ (trước ngày thu). Ngày thu lớn hơn số ngày của tháng thì lấy ngày cuối tháng.
- Tổng: tiền thuê mỗi tháng của các phòng có khách, đã thu trong năm, khách còn nợ, tiền cọc đang giữ, số phòng có khách và phòng trống.
- Nhắc ở Việc cần xem và Telegram (một lần cho mỗi phòng và tháng, hoặc mỗi ngày hết hợp đồng): quá ngày thu mà tháng này chưa thu đủ; hợp đồng hết hạn trong 30 ngày.
- Không ảnh hưởng Tháp tài sản hay Bất động sản và khoản vay.
