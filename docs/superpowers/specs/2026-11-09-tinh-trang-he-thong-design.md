# Tình trạng hệ thống

Duyệt 09/11/2026 (chủ sở hữu). Phần tự động chỉ đáng tin khi biết lúc nó ngừng chạy; trước đây kết quả chỉ nằm trong `logs/scheduler.log`.

Sự cố gồm: một bước lỗi từ 2 lần liên tiếp; dữ liệu quá hạn dù các bước báo thành công (giá VN-Index 6 ngày theo phiên cuối; vĩ mô, sự kiện 3; báo cáo cơ bản, chỉ số ngành 4; Báo cáo VNDirect 9 (làm mới mỗi mã sau 7 ngày, thêm 2; chủ sở hữu duyệt 21/11/2026); xu hướng 6; thuyết minh Vietcap 10 ngày, theo tệp mới nhất);
lịch sau phiên không xong trong 2 ngày; chưa diễn tập, diễn tập hỏng, hoặc lần gần nhất quá 14 ngày.

- `health-check` chạy cuối lịch sau phiên và trong tác vụ cảnh báo, để lịch sau phiên ngừng vẫn phát hiện được. Chỉ khi có thay đổi mới đọc Firestore và gửi Telegram: mỗi sự cố báo một lần, hồi phục báo một lần; gửi không được thì lần sau báo lại.
- `backup-drill` mỗi tuần khôi phục bản sao lưu mới nhất vào thư mục tạm, kiểm checksum, đọc được bản xuất cá nhân, rồi xóa; chỉ giữ số tệp và loại lỗi. Không ghi vào Firestore hay `data/`.
- Chỉ đọc tên bước và mã thoát từ nhật ký, không đọc nội dung bước in ra. Trang Cài đặt có khối Tình trạng hệ thống.
- Giới hạn: máy tắt thì không có gì chạy và không báo được. Kỳ nghỉ dài có thể báo giá quá hạn một lần.

## Từng chỉ số vĩ mô và lỗi tạm thời (duyệt 21/11/2026)
- Mỗi chỉ số vĩ mô tự động có số mới nhất đã quá hạn của chính nó là một sự cố riêng (mã `macro:<chỉ số>`), có tên, ngày số mới nhất và hạn. Thư mục Vĩ mô có thể mới trong khi một chuỗi đã cũ hàng tháng. Chỉ số chưa có số nào (vừa thêm) và chỉ số nhập tay (đã có nhắc riêng) không tính.
- `macro-sync`:
  - Lỗi máy chủ (429, 5xx) được ghi là `ServerError` và hỏi lại sau 30 giây như lỗi quá thời gian; kể cả trang OMO. Lỗi 404 hay lỗi khác vẫn là kết quả cuối.
  - Bước chỉ thoát lỗi khi có nguồn **quá hạn**: chỉ số hỏng mà không còn số nào trong hạn của nó, OMO hỏng mà không có phiên nào trong 7 ngày, hoặc một nguồn khác hỏng. Nguồn hỏng nhưng số vẫn còn trong hạn là `late`: vẫn in ra, bước thoát 0.
  - Nhắc lỗi nguồn vẫn đếm số lượt lỗi liên tiếp của từng nguồn như cũ.
- Khi nguồn có số tháng mới nhất nhưng để trống số cùng kỳ năm trước (FRED để trống CPI Mỹ tháng 10/2025 vì Mỹ không công bố), tháng đó không tính được mức tăng so cùng kỳ và **không được lấp**. Phần mềm ghi tháng thiếu vào `data/macro/_gaps.json`; trang Vĩ mô và sự cố quá hạn của chỉ số nêu rõ lý do.
- `macro-sync` đọc các chỉ số theo nhóm máy chủ nguồn: các nhóm chạy song song (tối đa 6), chỉ số cùng một máy chủ vẫn đọc lần lượt;
  lãi suất thực đọc sau cùng vì dùng hai chuỗi vừa tải. Khoảng 58 giây còn khoảng 20 giây một lượt (21/11/2026).
- Hạn của Cung tiền M2 Việt Nam: 100 ngày (trước là 80), vì NHNN công bố chậm 2–3 tháng (chủ sở hữu duyệt 21/11/2026).
