# Bảng đèn chỉ báo sớm

Duyệt 09/11/2026 (chủ sở hữu). Khối trên trang từng mã, sau Bảng số tài chính.

- Chủ sở hữu chọn tối đa 12 chỉ báo cho mỗi mã: vĩ mô và hàng hóa đã lưu (Dẫn dắt), chỉ số của chính mã (Kết quả), P/E, P/B, EV/EBITDA (Định giá), và đặt hai ngưỡng. Phần mềm không tự đặt ngưỡng. Tốt lớn hơn Xấu là càng cao càng tốt, ngược lại là càng thấp càng tốt.
- Lấy số mới nhất kèm kỳ. Chuỗi vĩ mô cũ hơn 120 ngày hoặc chưa có số thì không tô màu và ghi lý do. Crack spread chưa có nguồn nên chưa có trong danh sách.
- `lights-check` chạy cuối lượt sau phiên: lần đầu chỉ ghi nhớ màu; đổi màu thì báo Telegram một lần, gửi lỗi thì lượt sau báo lại. Thiếu số tạm thời không tính là đổi màu.
- Ngưỡng lưu ở kho cá nhân `settings/lights_<MÃ>`; không gửi AI.
