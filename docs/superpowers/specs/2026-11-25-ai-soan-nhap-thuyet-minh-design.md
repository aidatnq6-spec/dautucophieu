# AI soạn nháp Thuyết minh TSCĐ (nhập tay) từ BCTC (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 4 của đề xuất "tự động thay nhập tay", phương án 1: cả 5 phần, giữ ngân sách 2 USD/tháng). Mở rộng C5b
([Hỏi AI về tài liệu công khai](2026-11-16-hoi-ai-tai-lieu-cong-khai-design.md)) sang các phần chữ của thuyết minh mà Vietcap và VNDirect không có. Cùng
chính sách: mỗi lần chỉ gửi **mã cổ phiếu, năm báo cáo và các đoạn trích tài liệu**; không gửi danh mục, giá vốn, danh sách theo dõi, định giá hay số
liệu cá nhân. Tác vụ `notes_extract` của `config/ai-policy.json` (tối đa 0,20 USD mỗi lần, 2 USD mỗi tháng). **AI không bao giờ tự lưu.**

## Cách dùng
Khối Thuyết minh TSCĐ (nhập tay) ở hồ sơ mã: ô link BCTC năm (https công khai, như C5) và năm báo cáo, nút **AI soạn nháp**. Một lần gọi AI cho cả
tài liệu. Bản nháp hiện theo 6 phần, mỗi dòng kèm số trang và ô chọn; chủ sở hữu sửa nếu cần, bấm **Lưu vào thuyết minh** để thêm các dòng đã chọn
vào đúng phần (dự án, thương vụ, ưu đãi thêm vào danh sách đang có; phân bổ và lãi vay vốn hóa ghi vào năm đó; khung khấu hao thay bảng hiện có).

## Đoạn gửi đi
Từ văn bản đã trích (bộ trích PDF có sẵn, không OCR, lưu đệm `data/ai-docs/`), chọn đoạn theo từ khóa của từng phần (XDCB dở dang; thời gian khấu
hao; chi phí trả trước phân bổ; hợp nhất kinh doanh, lợi thế thương mại; chi phí đi vay vốn hóa; thuế thu nhập doanh nghiệp ưu đãi, miễn giảm), mỗi
phần tối đa 2.500 từ, gộp và bỏ trùng.

## Kiểm tra trước khi hiện (`ai/notes_draft.py`)
- JSON đúng dạng; đơn vị tính (đồng, nghìn, triệu, tỷ đồng) phải có trong tài liệu, như C5b.
- **Mỗi số** (số tiền, tỷ lệ, số năm, năm) phải có nguyên văn trong đoạn của đúng trang AI ghi; trang phải là trang đã gửi. Không đạt thì bỏ dòng đó và
  ghi lý do ("số không có ở trang", "trang không được gửi"), không sửa số.
- Số tiền đổi về tỷ đồng theo đơn vị tài liệu. Quý hoàn thành chỉ điền khi đoạn ghi rõ quý và năm (Q3/2027, "quý 3 năm 2027"); chỉ có năm thì để
  trống ô quý, ghi chữ gốc để chủ sở hữu chọn. Khung khấu hao: số năm từ–đến 0–100, nhóm theo 6 nhóm có sẵn. Ưu đãi: thuế suất dưới 20%, năm hết dạng 20xx.
- Chi phí lần gọi hiện cùng bản nháp, cùng mức đã dùng tháng này.

## Không làm
Tự tìm link BCTC; đọc PDF dạng ảnh; lưu khi chưa bấm; gọi lại khi kiểm tra không đạt (một lần gọi mỗi lần bấm).
