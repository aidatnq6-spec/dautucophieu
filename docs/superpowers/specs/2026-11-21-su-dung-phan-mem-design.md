# Sử dụng phần mềm (21/11/2026)

Chủ sở hữu duyệt ngày 21/11/2026 (kaizen giao diện, đề xuất 1).

## Vì sao
Muốn biết trang nào dùng nhiều để ưu tiên cải tiến, và bắt sớm chỗ bắt đầu chậm. Trước đây phần mềm không ghi gì về việc này.

## Hành vi
- **Lượt mở trang:**
  - Mỗi lần chuyển trang, web báo cho backend đường dẫn của trang. Chỉ lấy đoạn đầu, ví dụ `/research/HPG` được tính là
    `/research`. Đường dẫn không phải trang thường thì bị từ chối.
  - Backend đếm theo trang và theo ngày (giờ Việt Nam), giữ 90 ngày, trong `data/usage/visits.json`.
- **Yêu cầu chậm:**
  - Mọi yêu cầu tới backend được đo thời gian. Yêu cầu chậm từ 1 giây trở lên được ghi vào `data/usage/slow.json`, giữ 200 lần
    gần nhất.
  - Đường dẫn được che: chỉ giữ các chữ thường (tên khu vực). Đoạn khác (mã cổ phiếu, số tiền, mã số) thành `*`.
  - Không tính `/health` và chính các yêu cầu của trang này.
- **Hiển thị:** trang Cài đặt có khối "Sử dụng phần mềm".
  - Bảng lượt mở trong 30 ngày, 7 ngày và hôm nay, theo tên trên menu, sắp theo 30 ngày.
  - Bảng yêu cầu chậm gộp theo đường dẫn đã che: số lần và lần lâu nhất.
  - Ngày bắt đầu ghi.
- Ghi lỗi (không ghi được tệp) không làm hỏng yêu cầu hay trang.

## Không làm
- Không gửi dữ liệu này ra ngoài máy, không gửi cho AI.
- Không ghi nội dung trang, số liệu cá nhân, mã cổ phiếu hay số tiền.
