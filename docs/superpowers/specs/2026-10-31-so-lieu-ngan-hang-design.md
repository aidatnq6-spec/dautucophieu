# Số liệu ngân hàng nhập tay: nợ nhóm 1–5, CASA, CAR

Ngày: 31/10/2026 · Trạng thái: chủ sở hữu chọn làm cả nhập tay và đọc từ báo cáo PDF

## Vì sao nhập tay

Đã kiểm tra ngày 31/10/2026, không nguồn miễn phí, hợp lệ nào cho tự động nợ nhóm 1–5, CASA, CAR:

- VNDirect `v4/ratios`: có NPL, bao phủ, LDR, NIM; không có CASA, CAR, nhóm nợ. Mục "Thuyết minh - Ngân hàng" (modelType 104) không trả số. Tin `financialstatement` chỉ có bản giải trình lợi nhuận, không có toàn văn báo cáo.
- TCBS: chặn bằng Cloudflare. Vietcap: chỉ trả lời khi giả danh trang của họ — không dùng.
- Vnstock gói Cộng đồng: `ratio()` bị khóa; gói trả phí là quyết định của chủ sở hữu.

Số này nằm trong thuyết minh báo cáo tài chính quý (nhóm nợ, tiền gửi) và báo cáo thường niên / công bố Basel II (CAR) — cách chủ sở hữu đang làm trong Excel.

## Dữ liệu

Mỗi ngân hàng theo dõi, mỗi quý (ví dụ `2026-Q3`), đơn vị tỷ đồng: nợ nhóm 1, 2, 3, 4, 5; tiền gửi không kỳ hạn; tiền gửi ký quỹ; tiền gửi của khách hàng; CAR (%). Ô nào để trống thì là thiếu, không suy ra. Lưu ở kho cá nhân (`settings/bank_figures_<MÃ>`, có lịch sử phiên bản) kèm nguồn: nhập tay, hoặc đường dẫn PDF và số trang của từng số.

Chỉ số tính ra: NPL = (nhóm 3+4+5) / tổng nhóm 1–5; tỷ lệ nợ nhóm 2; CASA = (không kỳ hạn + ký quỹ) / tiền gửi khách hàng (công thức trong Excel của chủ sở hữu); CAR như nhập.

## Điền sẵn từ báo cáo PDF

Chủ sở hữu dán đường dẫn PDF công khai của báo cáo (trang nhà đầu tư của ngân hàng). Phần mềm tải về (chỉ `https`, không địa chỉ nội bộ, tối đa 30 MB), đọc chữ từng trang (pypdf, không OCR), tìm các dòng theo nhãn ("Nợ đủ tiêu chuẩn" … "Nợ có khả năng mất vốn", "Tiền gửi không kỳ hạn", "Tiền gửi ký quỹ", "Tiền gửi của khách hàng", "tỷ lệ an toàn vốn") và **điền sẵn vào form kèm số trang**; chủ sở hữu xem lại rồi lưu. Không dùng AI, không đổi chính sách AI. PDF dạng ảnh hoặc không tìm thấy nhãn thì báo rõ, để nhập tay. Số đọc được là gợi ý cho tới khi chủ sở hữu bấm lưu.

## Điểm sức khỏe ngân hàng

Khi một ngân hàng đã có số nhập tay, Điểm sức khỏe thêm hai tiêu chí, so quý gần nhất có số với cùng quý năm trước: **CASA tăng**, **tỷ lệ nợ nhóm 2 giảm**. Ngân hàng chưa có số nhập tay thì giữ 7 tiêu chí như cũ (không bị hạ mức vì thiếu ô nhập).

## Giao diện

Trang hồ sơ mã ngân hàng: mục "Số liệu ngân hàng (nhập tay)" — bảng theo quý (nhóm nợ, NPL, nợ nhóm 2, CASA, CAR, nguồn), form nhập/sửa một quý, ô dán đường dẫn PDF để điền sẵn, nút xóa một quý.

## Thử trên báo cáo thật (31/10/2026)

Đã đọc thử báo cáo tài chính hợp nhất quý 1, 2, 3/2026 ("bản tra cứu") và báo cáo công bố tỷ lệ an toàn vốn bán niên 2026, năm 2025 của Techcombank (trang nhà đầu tư `techcombank.com`, robots.txt cho phép): đủ 8 ô từ báo cáo tài chính, CAR hợp nhất từ báo cáo an toàn vốn; NPL, nợ nhóm 2 tính ra khớp cột % trong báo cáo. Ba điều chỉnh từ lần thử:

- đơn vị đọc được từ dòng tiêu đề cột ("triệu đồng triệu đồng"), không chỉ "Đơn vị: …";
- nợ nhóm 1–5 chỉ lấy trong mục "chất lượng nợ cho vay" (cùng trang có thể có bảng chất lượng tiền gửi, cấp tín dụng cho TCTD khác với cùng nhãn); tiền gửi chỉ lấy trong mục thuyết minh "Tiền gửi của khách hàng" có đánh số;
- chữ trong PDF được chuẩn hóa NFC (có file lưu chữ Việt dạng tổ hợp); CAR đọc được từ bảng "Riêng lẻ | Hợp nhất" (lấy hợp nhất).

CAR không có trong báo cáo tài chính quý; một quý có thể điền từ hai file, mỗi ô giữ file và trang nguồn của nó.

## Thử với 9 ngân hàng theo dõi (31/10/2026)

| Mã | Nguồn | Kết quả |
|---|---|---|
| TCB | `techcombank.com` (robots cho phép) | Đọc đủ 8 ô từ báo cáo quý 1–3/2026 "bản tra cứu", CAR từ báo cáo an toàn vốn |
| EIB | `eximbank.com.vn` → `media.eximbank.com.vn` | Báo cáo quý là bản scan dạng ảnh: không có chữ, nhập tay. Máy chủ file thiếu chứng chỉ trung gian: tải bằng kho chứng chỉ của hệ điều hành (vẫn xác minh) |
| MBB | `mbbank.com.vn` | robots.txt trả 403 — không lấy |
| BID | `bidv.com.vn` | Có lớp kiểm tra chống bot bằng JavaScript — không vượt, không lấy |
| ACB, VCB, CTG, STB, SHB | trang nhà đầu tư (robots cho phép, SHB trả 403 cho trang danh sách) | Chưa tìm được đường dẫn PDF 2026 tự động (danh sách tải bằng JavaScript/API riêng). Chủ sở hữu dán đường dẫn từ trình duyệt; nếu là PDF có chữ, bộ đọc dùng được, nếu lệch định dạng thì để trống ô và báo |
