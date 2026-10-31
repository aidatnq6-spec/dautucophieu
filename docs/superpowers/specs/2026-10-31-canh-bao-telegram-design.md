# Cảnh báo qua Telegram: giao dịch nội bộ và mức giá (31/10/2026)

Chủ sở hữu đồng ý làm hai cảnh báo cho mã đang nắm và danh sách theo dõi. Gửi qua Telegram như bản tin, chỉ khi "gửi theo lịch" đang bật
trong Cài đặt. Không dữ liệu nào gửi cho AI.

## Giao dịch nội bộ mới
- Mã đang nắm (theo sổ giao dịch). Nguồn: danh sách thông báo HOSE qua VNDirect, như mục trên trang mã (lưu 1 ngày).
- Chạy trong lượt sau giờ đóng cửa (08:30, 15:30, 20:00). Lần đầu với một mã chỉ ghi mốc, không gửi. Thông báo mới trong 30 ngày
  được gửi một lần, kèm loại, khối lượng (theo nguồn) và link; thông báo cũ hơn 30 ngày mới xuất hiện thì ghi nhận, không gửi.
- Gửi lỗi thì lần sau gửi lại. Trạng thái ở `data/alerts/insider.json` (chỉ thông báo công khai).

## Cảnh báo giá
- Chủ sở hữu đặt mức ≥ hoặc ≤ cho VNINDEX, VN30 hoặc mã trong danh sách theo dõi trên tab Xu hướng (cổ phiếu: nghìn đồng; chỉ số: điểm).
  Chưa có cho biến vĩ mô. Tối đa 50 cảnh báo. Lưu trong kho cá nhân (`settings/price_alerts`, ghi có phiên bản).
- Trang đọc số kiểu Việt (56,3; 1.800) và hiện mức đã hiểu trước khi lưu; API chỉ nhận số dạng chuẩn.
- Tác vụ Windows `InvestmentAgent-Alerts` chạy `price-alerts` mỗi 5 phút từ 09:00 đến 15:05. Ngoài phiên, hoặc không có cảnh báo
  đang chờ, lệnh không gọi nguồn nào. Trong phiên: một lượt bảng giá cho các mã cần, nến phút cho chỉ số cần.
- Mỗi cảnh báo báo một lần, ghi giờ và giá đã báo; "Bật lại" để chờ tiếp. Không có giá (chưa khớp) thì không báo. Gửi lỗi thì vẫn chờ.

## Ổn định kiểm thử
- `verify.ps1`: bước nào trượt thì lưu toàn bộ đầu ra vào `logs/verify-<bước>.log`, in các dòng lỗi; test e2e trượt ghi thêm một dòng
  vào `logs/e2e-failures.log` để theo dõi test nào trượt thất thường. Playwright giữ trace và ảnh của test trượt.
