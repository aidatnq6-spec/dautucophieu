# Bảng đèn chỉ báo sớm

Duyệt 09/11/2026 (chủ sở hữu). Khối trên trang từng mã, sau Bảng số tài chính.

- Chủ sở hữu chọn tối đa 12 chỉ báo cho mỗi mã: vĩ mô và hàng hóa đã lưu (Dẫn dắt), chỉ số của chính mã (Kết quả), P/E, P/B, EV/EBITDA (Định giá), và đặt hai ngưỡng. Phần mềm không tự đặt ngưỡng. Tốt lớn hơn Xấu là càng cao càng tốt, ngược lại là càng thấp càng tốt.
- Lấy số mới nhất kèm kỳ. Chuỗi vĩ mô quá hạn của chính nó hoặc chưa có số thì không tô màu và ghi lý do kèm hạn: chỉ số vĩ mô theo hạn của trang Vĩ mô, chuỗi của Chuỗi giá trị theo hạn ở đó (crack 14 ngày, tồn kho quần áo Mỹ 110), giá hàng hóa theo tháng 120 ngày (chủ sở hữu chọn 21/11/2026). Crack spread dùng số đại diện crack 3-2-1 Mỹ (21/11/2026).
- `lights-check` chạy cuối lượt sau phiên: lần đầu chỉ ghi nhớ màu; đổi màu thì báo Telegram một lần, gửi lỗi thì lượt sau báo lại. Thiếu số tạm thời không tính là đổi màu.
- Ngưỡng lưu ở kho cá nhân `settings/lights_<MÃ>`; không gửi AI.
