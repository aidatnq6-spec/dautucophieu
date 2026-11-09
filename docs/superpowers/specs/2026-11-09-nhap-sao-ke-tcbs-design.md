# Nhập sao kê TCBS vào Sổ giao dịch

Duyệt 09/11/2026 (chủ sở hữu). Phần mềm không đăng nhập TCBS: chủ sở hữu tự tải "Lịch sử giao dịch cổ phiếu" (.xlsx) rồi chọn file. Không gửi cho AI.

- Lấy KL khớp, giá khớp, phí, thuế, ngày GD, số hiệu lệnh của dòng "Hoàn tất". Dòng không đọc đúng được báo số dòng và bỏ qua; không tự điền phí hay thuế thiếu.
- Xem trước từng lệnh, chỉ ghi khi xác nhận. Không thêm lại: lệnh đã nhập (mã `tcbs-<số hiệu>`, kể cả đã hủy) và lệnh đã ghi tay trùng ngày, mã, loại, khối lượng, giá (mỗi lệnh ghi tay chỉ khớp một lệnh). Lệnh trước số dư đầu kỳ bị bỏ qua và ghi rõ.
- Trong một ngày, lệnh bán xếp trước lệnh mua (T+2). Toàn bộ sổ được tính lại cùng các lệnh mới: bán vượt số đang có hoặc tiền âm thì không ghi lệnh nào và nêu lệnh gây lỗi.
