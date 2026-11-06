# Nhắc sổ tiết kiệm đáo hạn qua Telegram (06/11/2026)

Việc sau đầu tiên của [Sổ tài sản](2026-11-05-so-tien-gui-design.md): báo trước một ngày khi một sổ tiết kiệm sắp đến hạn, để chủ sở hữu
kịp quyết định tái tục, tất toán hay chuyển tiền. Phần mềm không tự làm việc nào trong số đó và không khuyên chọn cách nào. Chủ sở hữu
chọn (06/11/2026): một lần nhắc trước 1 ngày, tin ghi gốc và lãi.

## Khi nào gửi
- Chỉ khi "gửi theo lịch" đang bật trong Cài đặt, như các cảnh báo khác. Tắt thì lệnh không đọc sổ và không gửi gì.
- Chạy trong lượt sau giờ đóng cửa (08:30, 15:30, 20:00 và khi đăng nhập); ngày nghỉ cũng chạy.
- Mỗi sổ một lần nhắc: lượt đầu tiên kể từ ngày trước ngày đáo hạn (thường 08:30 hôm trước). Máy tắt hôm đó thì nhắc ở lượt đầu tiên sau
  đó, nhưng không quá 7 ngày sau ngày đáo hạn; muộn hơn thì không nhắc, trang vẫn báo "quá hạn, cần cập nhật".
- Lời nhắc gắn với cặp (sổ, ngày đáo hạn): sửa ngày đáo hạn (ví dụ sau khi tái tục) thì sổ được nhắc lại theo ngày mới; xóa sổ thì thôi.
- Không ghi mốc ở lần chạy đầu: sổ đang trong khoảng nhắc thì được nhắc ngay.
- Nhiều sổ cùng lượt gộp thành một tin. Gửi lỗi thì lượt sau gửi lại; chỉ đánh dấu đã nhắc sau khi tin đã đi.

## Nội dung tin
```
Sổ tiết kiệm đến hạn
• <tên ngân hàng như đã nhập> · đến hạn ngày mai 05/12/2026 · gốc 50.000.000 đ · lãi khi đáo hạn 2.030.548 đ · phong tỏa
• <…> · đến hạn hôm nay 06/12/2026 · gốc … · lãi đầu kỳ, đã nhận
• <…> · đã đến hạn 03/12/2026 (3 ngày trước) · gốc … · lãi chưa nhập
Phần mềm không tự tái tục hay tất toán. Xử lý xong, sửa ngày đáo hạn hoặc xóa sổ ở Sổ tài sản. Không phải khuyến nghị.
```
- Lãi chưa nhập ghi "lãi chưa nhập", không ước tính. Sổ trả lãi đầu kỳ ghi "lãi đầu kỳ, đã nhận". Sổ xếp theo ngày đáo hạn.

## Dữ liệu
- Sổ đọc từ kho cá nhân (`settings/deposit_book`). Tin chỉ đi tới chat Telegram của chủ sở hữu, như bản tin; không gửi gì cho AI.
- Trạng thái đã nhắc ở `data/alerts/deposits.json`: mã dòng và ngày đáo hạn, không có số tiền. Bỏ mục của sổ đã xóa hoặc đổi ngày.
- Lệnh `python -m investment_agent.cli deposit-alerts --data-dir data`, ghi một dòng vào `logs/scheduler.log` như các bước khác.

## Ngoài phạm vi
Nhắc nhiều mốc; nhắc qua kênh khác; tự đề xuất lãi suất tái tục.
