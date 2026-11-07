# Chuỗi định giá theo tuần: P/E 4 quý gần nhất và P/B (07/11/2026)

Bước 1 của nhóm "dải phân vị định giá": nền dữ liệu cho dải phân vị P/B, P/E (bước 2), giá giả định (bước 3) và mốc giá quá khứ
(bước 4). Bước này chưa có giao diện. Chỉ dùng báo cáo tài chính công khai và giá ngày; không đọc danh mục, không gửi gì cho AI.

## Giới hạn nguồn (đã kiểm 07/11/2026)
- Vnstock 5.2 gói Cộng đồng trả **8 kỳ gần nhất** cho mỗi loại kỳ: thư viện cảnh báo "chỉ gồm 8 kỳ báo cáo gần nhất". Quý chỉ có từ
  2024-Q4; năm có từ 2018. Nguồn KBS chỉ trả 4 quý.
- Vì vậy chủ sở hữu chọn **ghép số năm với số quý**: mỗi tuần dùng số mới nhất ứng dụng có, và ghi rõ cơ sở.
- Đồng bộ báo cáo (`fundamentals-sync`) từ nay **giữ các kỳ đã lưu** khi nguồn không trả về nữa; kỳ nguồn trả lại thì thay bằng số mới.
  Dữ liệu quý sẽ dài dần theo thời gian, không cần đổi gói.

## Quy tắc "đã công bố từ ngày nào"
- Năm Y: từ 01/4 năm Y+1, như biểu đồ theo tháng đang dùng.
- Quý: 45 ngày sau ngày kết thúc quý. Đây là hạn muộn nhất theo Thông tư 96/2020/TT-BTC Điều 14: báo cáo quý 20 ngày, bản soát xét
  không quá 45 ngày. Căn cứ và mức kiểm chứng ghi ở [market-rules.md](../../decisions/market-rules.md).
- Gói Cộng đồng không có ngày công bố thật. Lấy hạn muộn nhất để tuần nào cũng chỉ dùng số đã ra.

## Chuỗi theo tuần
Mỗi tuần lấy giá đóng cửa cuối tuần (giá điều chỉnh) × số cổ phiếu hiện tại, cùng cơ sở với biểu đồ theo tháng. Giá bằng 0 thì bỏ.
- **P/E**: cơ sở "4 quý" khi đủ 4 quý liền nhau đến quý mới nhất đã công bố. Thiếu quý thì dùng báo cáo năm mới nhất đã công bố (cơ sở
  "năm") và liệt kê các quý thiếu của cửa sổ đó. Nếu quý mới nhất là quý 4 của chính năm báo cáo thì hai cách cùng 12 tháng, không ghi thiếu.
  Lỗ hoặc bằng 0 thì không có P/E, nhưng vẫn ghi mẫu số.
- **P/B**: VCSH cuối quý mới nhất đã công bố (cơ sở "quý"). Thiếu thì dùng VCSH cuối năm mới nhất đã công bố (cơ sở "năm") và ghi quý thiếu.
- Tuần không có cả hai thì không có điểm. Không nội suy, không ước lượng.
- Mỗi điểm: ngày, giá, giá trị, cơ sở, kỳ dùng, mẫu số, các quý thiếu. Kết quả có thêm danh sách tất cả quý thiếu.

## API
`GET /internal/fairvalue/weekly/{mã}`: chỉ mã trong danh sách theo dõi (mã khác trả 404). Không có báo cáo thì trả lý do "Chưa có báo cáo
tài chính"; không có giá thì trả "Chưa có lịch sử giá".

## Ngoài phạm vi
Phân vị, z, độ lệch và giao diện (bước 2); giá giả định (bước 3); mốc giá quá khứ (bước 4). Chỉ số VN-Index/VN30 đã có chuỗi ngày riêng.
