# Tình trạng hệ thống

Duyệt 09/11/2026 (chủ sở hữu). Phần tự động chỉ đáng tin khi biết lúc nó ngừng chạy; trước đây kết quả chỉ nằm trong `logs/scheduler.log`.

Sự cố gồm: một bước lỗi từ 2 lần liên tiếp; dữ liệu quá hạn dù các bước báo thành công (giá VN-Index 6 ngày theo phiên cuối; vĩ mô, sự kiện 3; báo cáo, chỉ số ngành 4; xu hướng 6; thuyết minh Vietcap 10 ngày, theo tệp mới nhất);
lịch sau phiên không xong trong 2 ngày; chưa diễn tập, diễn tập hỏng, hoặc lần gần nhất quá 14 ngày.

- `health-check` chạy cuối lịch sau phiên và trong tác vụ cảnh báo, để lịch sau phiên ngừng vẫn phát hiện được. Chỉ khi có thay đổi mới đọc Firestore và gửi Telegram: mỗi sự cố báo một lần, hồi phục báo một lần; gửi không được thì lần sau báo lại.
- `backup-drill` mỗi tuần khôi phục bản sao lưu mới nhất vào thư mục tạm, kiểm checksum, đọc được bản xuất cá nhân, rồi xóa; chỉ giữ số tệp và loại lỗi. Không ghi vào Firestore hay `data/`.
- Chỉ đọc tên bước và mã thoát từ nhật ký, không đọc nội dung bước in ra. Trang Cài đặt có khối Tình trạng hệ thống.
- Giới hạn: máy tắt thì không có gì chạy và không báo được. Kỳ nghỉ dài có thể báo giá quá hạn một lần.
