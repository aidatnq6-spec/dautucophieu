# Quy tắc thị trường dùng trong sổ

Trạng thái: **chưa kiểm chứng từ nguồn chính thức** (2026-10-25). Không có bộ quy tắc T+, lô giao dịch, biên độ hay thuế/phí nào được cấu hình trong mã.

## Đang áp dụng

- Phí, thuế bán và thuế cổ tức là số thực tế người dùng nhập theo chứng từ công ty chứng khoán. Không có tỷ lệ mặc định.
- Ngày thanh toán (`settlement_date`) là dữ liệu của từng giao dịch, lấy từ sao kê; mã không suy ra ngày T+ từ ngày giao dịch.
- Tiền có thể mua (`domain/settlement.py`):
  1. Số người dùng xác nhận cho đúng ngày đó, không vượt tiền kế toán trên sổ.
  2. Nếu không có: tiền kế toán trừ tiền bán chưa đến ngày thanh toán đã ghi.
  3. Có lệnh bán thiếu ngày thanh toán: tiền có thể mua là `unknown`, không lạc quan coi toàn bộ tiền bán là dùng được.
- Số lượng có thể bán: cổ phiếu đã về tài khoản, trừ lệnh mua chưa đến ngày thanh toán đã ghi; cổ phiếu thưởng/cổ tức cổ phiếu chờ về không được bán. Lệnh mua thiếu ngày thanh toán làm số lượng ở trạng thái `unknown`.
- Khuyến nghị (Task 20) chỉ đề xuất số tiền; số lượng phải được người dùng xác nhận vì quy tắc lô chưa được kiểm chứng.

## Sự kiện quyền

- Cổ tức tiền: ghi quyền (phải thu) tại ngày không hưởng quyền với số lượng đủ điều kiện người dùng nhập; khi nhận tiền chỉ chuyển phải thu thành tiền, chênh lệch dự kiến/thực nhận ghi thành điều chỉnh có truy vết. Thu nhập chỉ ghi một lần.
- Cổ phiếu thưởng/cổ tức cổ phiếu: tăng số lượng chờ về, giữ nguyên tổng giá vốn; số thực nhận và tiền thanh toán phần lẻ ghi theo chứng từ.
- Tách/gộp cổ phiếu: sự kiện `share_split` với tỷ lệ rõ; kết quả lẻ bị từ chối để người dùng nhập theo chứng từ.
- Quyền mua, đổi mã, sáp nhập: `unsupported_action` đánh dấu mã bị chặn; phân tích phụ thuộc mã đó không được phát hành cho đến khi hỗ trợ.
- Không dùng giá điều chỉnh để định giá tài sản thực tế rồi cộng cổ tức lần nữa.

## Cần làm trước khi bật quy tắc tự động

Đối chiếu quy chế giao dịch và thanh toán hiện hành của HOSE/VSDC (chu kỳ thanh toán, lô chẵn/lô lẻ, bước giá, biên độ) và quy định thuế đối với chuyển nhượng chứng khoán/cổ tức; ghi đường dẫn chính thức, ngày hiệu lực và phiên bản vào file này. Không dùng mức nhớ từ hội thoại làm quy định hiện hành.
