# Bộ lọc tín hiệu cho mã theo dõi

Ngày: 01/11/2026 · Trạng thái: chủ sở hữu chọn "làm luôn với các mặc định hợp lý"; các lựa chọn dưới đây là quyết định của người làm.

## Mục tiêu
Thu hẹp 50 mã theo dõi bằng nhiều tín hiệu đã có cùng lúc (ví dụ "Rẻ + chất lượng mạnh + MACD tuần vừa cắt lên"), lưu bộ lọc, và nhắn
Telegram khi có mã mới lọt vào. Chỉ thu hẹp danh sách để xem, không khuyến nghị.

## Tiêu chí (trong một tiêu chí chọn nhiều giá trị = "hoặc"; giữa các tiêu chí = "và")
| Tiêu chí | Giá trị | Nguồn đã có |
|---|---|---|
| Định giá | Rẻ / Hợp lý / Đắt | Định giá tham khảo (kết luận theo ngưỡng trong Cài đặt) |
| Chất lượng | Mạnh / Trung bình / Yếu | F-Score (phi tài chính) hoặc Điểm sức khỏe (ngân hàng, chứng khoán, bảo hiểm) |
| MACD ngày / MACD tuần | Trên tín hiệu / Dưới tín hiệu | Bảng Xu hướng (lập sau 15:30) |
| MACD tuần vừa cắt lên | Có | Bảng Xu hướng: tuần đổi từ dưới lên trên so với phiên trước |
| RSI ngày | Quá bán (≤30) / Trung tính / Quá mua (≥70) | Bảng Xu hướng |
| Chuỗi giá trị | Thuận / Trung tính / Ngược | Chuỗi giá trị đã duyệt; mã thuộc nhiều chuỗi khớp nếu một chuỗi khớp |
| Khối ngoại 20 phiên | Mua ròng / Bán ròng | Tổng khối ngoại ròng của mã trong 20 ảnh chụp phiên gần nhất |
| Sự kiện 14 ngày tới | Có / Không | Lịch sự kiện (cổ tức, phát hành, đại hội) |
| Đang nắm | Có / Không | Sổ giao dịch |

- Một mã thiếu dữ liệu cho tiêu chí đang dùng thì **không khớp**, và được đếm riêng "thiếu dữ liệu" kèm tên tiêu chí — không coi là đạt.
- Khối ngoại theo mã chưa từng được lưu: từ bản này ảnh chụp phiên (`data/brief/`) lưu thêm khối ngoại ròng của từng mã HOSE. Tiêu chí
  này "chưa đủ 20 phiên" cho đến khi đủ; không lấy nguồn khác bù.

## Bộ lọc đã lưu và Telegram
- Lưu tối đa 20 bộ lọc ở kho cá nhân (`settings/screens`): tên, tiêu chí, có nhắn Telegram hay không.
- Sau mỗi lượt sau giờ đóng cửa (sau Xu hướng và ảnh chụp phiên), với bộ lọc bật nhắn: mã **mới lọt vào** so với lần trước thì nhắn một tin
  (chỉ khi "gửi theo lịch" đang bật). Lần đầu chỉ ghi mốc. Mã rời bộ lọc không nhắn. Danh sách mã khớp lần trước lưu ở
  `data/alerts/screens.json` (chỉ mã cổ phiếu công khai).
- Tin nhắn liệt kê mã mới và giá trị các tiêu chí của mã; kết bằng "Chỉ để thu hẹp danh sách. Không phải khuyến nghị."

## Giao diện
Trang Theo dõi: mục "Bộ lọc tín hiệu" — chọn tiêu chí, bảng kết quả (mỗi mã kèm giá trị từng tiêu chí), số mã thiếu dữ liệu, lưu/xóa bộ
lọc, bật/tắt nhắn. Không gửi gì cho AI.
