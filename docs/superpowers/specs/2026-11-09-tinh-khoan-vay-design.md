# Tính khoản vay

Duyệt 08/11/2026 (chủ sở hữu), theo cách tính của refi.vn/cong-cu-tinh-khoan-vay (đã kiểm: khớp đến từng đồng với hai ví dụ). Viết riêng, không chép giao diện hay thương hiệu.

Trang `/loan`. Tính trên trình duyệt, không lưu, không gửi đi đâu.

- Nhập khoản vay, hoặc giá trị bất động sản × tỉ lệ vay (phần còn lại là cần trả trước; số giữa vòng tròn chỉ gồm gốc, lãi, phí trả ngân hàng như refi.vn, dòng riêng ghi tổng tiền bỏ ra gồm trả trước); thời hạn; lãi ưu đãi, thời gian ưu đãi, lãi sau ưu đãi.
- Dư nợ giảm dần: gốc chia đều. Trả đều hàng tháng: khoản trả cố định, tính lại khi lãi suất đổi. Lãi mỗi tháng = dư nợ × lãi năm ÷ 12; ghi rõ là ước tính vì ngân hàng thường tính theo ngày.
- Ân hạn nợ gốc: chỉ trả lãi, gốc chia cho số tháng còn lại. Trả hết trước hạn: cuối tháng đã chọn trả nốt dư nợ sau kỳ đó, phí tính trên phần trả nốt; hiện số tiết kiệm đã trừ phí.
- Thanh toán tháng đầu, vòng tròn cần trả trước, gốc, lãi; In; bảng từng kỳ; Xuất Excel.
- Không làm: "Theo ngân hàng" (không có nguồn lãi vay đáng tin), "Hỗ trợ lãi suất" (chưa rõ cách áp dụng), họ tên trên bảng in.
