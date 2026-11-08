# Tra cứu, nhập và xuất cho Nhật ký và Sổ giao dịch

Duyệt 08/11/2026 (chủ sở hữu), lấy ý tưởng từ file HTML nhật ký đầu tư cũ của chủ sở hữu, bản đó lưu trong `localStorage` nên dễ mất.

## Tra cứu

- Nhật ký: lọc theo mã, lệnh, cảm xúc, loại tài sản, từ khóa (lý do, ghi chú cảm xúc, ghi chú thêm; không phân biệt dấu), từ ngày đến ngày; mới nhất theo ngày quyết định lên trước.
  Dòng tóm tắt: số mục, thay đổi giá trung bình từ lúc ghi (chỉ các mục có giá), tổng lãi/lỗ ghi tay của mục nhập từ file cũ. Không cộng giá trị mua với bán.
- Nhật ký chia trang 50 mục (08/11/2026, sau khi nhập 621 mục cũ); số mục, trung bình và Xuất Excel luôn tính trên toàn bộ kết quả lọc.
- Sổ giao dịch: lọc theo mã, loại, từ ngày đến ngày.
- Xuất Excel (Excel 2003 XML, mọi ô có kiểu, nên lý do mở đầu bằng "=" vẫn là chữ) theo kết quả đang lọc; làm ngay trên trình duyệt.

## Nhập từ nhật ký cũ

Nhận file Excel mà trang HTML cũ xuất ra, hoặc CSV cùng cột (phẩy hoặc chấm phẩy, số kiểu Việt Nam). Xem trước rồi mới lưu.

- Không đoán: ngày không tồn tại, ngày tương lai, lệnh không rõ, số không đọc được, thiếu giá trị, mã không hợp lệ thì báo số dòng và bỏ dòng đó (trang cũ tự ghi ngày hôm nay).
- Tài sản khác cổ phiếu có tên tự do được giữ dưới mã thay thế (BDS, BTC, TIENGUI, TRAIPHIEU, VANG, KHAC), tên gốc lưu cùng mục.
- Mã mục sinh từ nội dung dòng, nên nhập lại không trùng; hai dòng giống hệt vẫn là hai mục.
- Mục nhập vào có ngày của file, không có bối cảnh thị trường và không nhắc xem lại theo giá. Chỉ vào Nhật ký, không vào Sổ giao dịch: file cũ không có phí, thuế và lãi/lỗ là số ghi tay.
- Dữ liệu cá nhân: chỉ đi giữa trình duyệt, máy chủ nội bộ và kho của chủ sở hữu, không gửi AI.

## Hậu kiểm lệnh cũ (08/11/2026, chủ sở hữu duyệt)

Lệnh mua, bán cổ phiếu đã nhập có khối riêng trong Hậu kiểm quyết định, không gộp với lệnh trong Sổ giao dịch. Mỗi lệnh đo sau 3, 6, 12 tháng bằng giá đóng cửa đã điều chỉnh của đúng
ngày đó, so với VN-Index, như lệnh trong sổ. Thói quen: giá sau 6 tháng của lệnh bán khi đang lãi và khi đang lỗ (theo lãi/lỗ ghi tay; 0 hoặc trống không xếp nhóm vì trang cũ lưu ô trống
thành 0), mua đuổi và các lần mua khác; nhóm dưới 5 quan sát không kết luận. Không tính tỷ lệ chốt lãi/lỗ theo Odean và các lần giữ khi lỗ, vì cần vị thế mà file cũ không dựng lại được.
Mã không có chuỗi giá đã lưu được liệt kê, không ước lượng.

Cảnh báo sụt giảm dẫn lý do của quyết định mới nhất theo ngày, không theo thứ tự lưu.
