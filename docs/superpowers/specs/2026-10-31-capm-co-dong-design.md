# Gợi ý lợi suất yêu cầu theo CAPM; cổ đông lớn và ban lãnh đạo

Ngày: 31/10/2026 · Trạng thái: chủ sở hữu chọn làm (bản gọn của sheet "WACC" trong Excel phân tích doanh nghiệp)

## CAPM

Chi phí vốn chủ tham khảo: **Ke = Rf + β × ERP**.

- **Rf**: lợi suất trái phiếu Chính phủ 10 năm của Việt Nam, giá trị mới nhất đã lưu (`vn10y`, Vĩ mô).
- **β**: beta của mã do VNDirect công bố (API công khai `v4/ratios/latest`, mã `BETA`), cả danh sách theo dõi trong một lượt gọi mỗi lần chạy lịch, lưu `data/beta.json`. Thị trường chung: β = 1.
- **ERP**: phần bù rủi ro vốn cổ phần — chủ sở hữu tự nhập trong Cài đặt (ví dụ theo bảng quốc gia của Damodaran, như cách làm trong Excel), lưu ở kho cá nhân (`settings/capm`). Chưa nhập thì không tính.

Hiện ở Cài đặt (cạnh "Lợi suất yêu cầu": Ke thị trường = Rf + ERP) và trên trang từng mã (Ke theo β của mã), kèm ngày của từng số và so với lợi suất yêu cầu đang đặt. Chỉ là gợi ý để tham khảo; phần mềm không tự đổi lợi suất yêu cầu. Thiếu Rf hoặc β thì ghi lý do.

## Cổ đông lớn và ban lãnh đạo

Nguồn: Vnstock gói Cộng đồng, `Company(source="VCI").shareholders()` và `.officers()` (kiểm tra 31/10/2026: FPT có 67 cổ đông, 9 người trong ban lãnh đạo, kèm tỷ lệ, số cổ phiếu, ngày cập nhật). Đọc khi mở trang mã, lưu đệm `data/company/<MÃ>.json`, đọc lại sau 30 ngày; nguồn lỗi thì hiện bản đã lưu kèm ngày, chưa có bản nào thì ghi lý do.

Trang mã hiện 10 cổ đông lớn nhất (tên, loại, tỷ lệ, số cổ phiếu, ngày cập nhật) và ban lãnh đạo (tên, chức vụ, tỷ lệ sở hữu). Dữ liệu công bố công khai của doanh nghiệp; không gửi cho AI.
