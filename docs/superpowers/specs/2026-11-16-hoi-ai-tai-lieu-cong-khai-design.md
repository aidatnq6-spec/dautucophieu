# Thiết kế C5: Hỏi AI về tài liệu công khai

Ngày: 16/11/2026 · Trạng thái: chủ sở hữu đã duyệt ngày 16/11/2026 (làm cả C5a và C5b)

## Mục đích

AI đọc **một tài liệu công khai của một mã** và làm một trong hai việc:

1. **Hỏi đáp tài liệu** (C5a). Chủ sở hữu dán link tài liệu và hỏi một câu. Ví dụ: "Thuyết minh 38 nói gì về phải thu bên liên quan?", "BCTC quý 3 giải thích biên gộp giảm thế nào?". AI trả lời kèm số trang trích dẫn.
2. **Đề xuất dòng cho Sổ phải thu bên liên quan** (C5b). Chủ sở hữu dán link BCTC năm của một mã. AI trích các khoản phải thu bên liên quan thành bản nháp có đúng các cột của sổ: đối tượng, số dư, bảo đảm, lãi, hạn thu, số trang. Chủ sở hữu đọc, sửa rồi mới lưu. Phần mềm không bao giờ tự lưu.

Các việc khác để giai đoạn sau, mỗi việc một spec riêng: dư nợ bất động sản và chiết khấu bộ chứng từ của ngân hàng; cập nhật chuỗi giá trị từ báo cáo ACBS mới.

## Thay đổi quy tắc AI (cần chủ sở hữu duyệt)

Quy tắc hiện hành, duyệt ngày 26/10/2026: AI chỉ đọc báo cáo vĩ mô, ngành, chiến lược công khai. Không gửi danh mục, danh sách theo dõi hay định giá. Ngân sách 2 USD/tháng.

Đề xuất sửa:

- **Mở rộng loại tài liệu được đọc:** thêm tài liệu công khai của doanh nghiệp. Gồm BCTC và thuyết minh, nghị quyết ĐHCĐ, báo cáo thường niên, công bố thông tin, và báo cáo phân tích công khai về doanh nghiệp đó.
- **Mỗi lần hỏi, gửi đi đúng ba thứ:** mã cổ phiếu đang hỏi, đoạn văn bản trích từ tài liệu, và câu hỏi đã qua bộ lọc. Gửi mã cổ phiếu cho thấy bạn đang quan tâm mã đó. Đây là điểm mới so với quy tắc cũ, nên cần bạn đồng ý rõ ràng.
- **Không bao giờ gửi:**
  - danh mục, số lượng, giá vốn, lãi lỗ;
  - danh sách theo dõi;
  - định giá của ứng dụng;
  - số liệu cá nhân, tên sổ, tên tài khoản;
  - bất kỳ số tiền nào bạn tự nhập.
- **Giữ nguyên:** ngân sách 2 USD/tháng; tối đa 0,20 USD mỗi lần; nhà cung cấp không lưu dữ liệu (ZDR, `data_collection: deny`).

## Bộ lọc câu hỏi (chạy trên máy, trước khi gửi)

Phần mềm chặn gửi, và nói rõ lý do, khi câu hỏi:

- **chứa số tiền**, gồm số có đơn vị (đ, đồng, nghìn, triệu, tỷ, USD) hoặc số có từ 4 chữ số liền nhau. Năm (2019–2030) và số hiệu thuyết minh ngắn vẫn được phép;
- **chứa cụm từ về bản thân**: "tôi", "mình", "của tôi", "danh mục", "đang nắm", "đang giữ", "giá vốn", "lãi lỗ của", "tài khoản", "sổ tiết kiệm";
- **chứa tên** một sổ, tài khoản hoặc khoản vay trong dữ liệu cá nhân. Việc so khớp chỉ diễn ra trên máy; danh sách tên không bao giờ được gửi đi;
- **chứa mã cổ phiếu khác** với mã của trang đang hỏi.

Câu hỏi dài tối đa 300 ký tự. Bộ lọc thà chặn nhầm còn hơn để lọt; khi bị chặn, bạn viết lại câu hỏi.

## Tài liệu

- Chỉ nhận link **https công khai**, dùng lại `check_public_https`. Phần mềm tự tải, tôn trọng robots.txt, không đăng nhập. Tệp tối đa 20 MB và 300 trang.
- Trích chữ bằng bộ trích PDF đã có. PDF dạng ảnh không có chữ thì báo "không trích được văn bản" và dừng, không OCR.
- Văn bản cắt thành từng đoạn theo trang. Chỉ gửi các đoạn liên quan nhất, chọn bằng từ khóa trên máy: tối đa khoảng 12.000 từ mỗi lần. Mỗi đoạn kèm số trang.
- Văn bản đã trích được lưu đệm trong `data/ai-docs/` theo link, để hỏi lại không phải tải lại. Không lưu PDF gốc.

## Kiểm tra câu trả lời

- **C5a:** câu trả lời phải trích số trang có trong các đoạn đã gửi. Mọi con số trong câu trả lời phải xuất hiện nguyên văn trong các đoạn đó. Không đạt thì thử sửa một lần; vẫn không đạt thì báo "AI trả lời không kiểm chứng được" và không hiện câu trả lời.
- **C5b:** mỗi dòng đề xuất phải có số dư và số trang khớp nguyên văn với văn bản. Dòng không khớp bị bỏ, kèm ghi chú. Phần mềm không tự điền số. Cờ bảo đảm, lãi và hạn thu chỉ được điền khi văn bản nói rõ; nếu không, để "Không rõ".
- Mọi câu trả lời đều ghi "AI tóm tắt, có thể sai: đối chiếu trang gốc", kèm link tới đúng trang.

## Giao diện

- Trang mã có khung **"Hỏi AI về tài liệu"**, gồm:
  - ô link tài liệu, ô câu hỏi, nút gửi;
  - dòng "Đã dùng X / 2 USD tháng này";
  - câu trả lời kèm trích dẫn trang.
- Khung **Phải thu bên liên quan** có thêm nút **"AI đề xuất từ BCTC"**: nhập năm và link tài liệu, AI trả về bản nháp và điền sẵn vào ô nhập. Bạn sửa rồi bấm "Lưu năm" như khi nhập tay.
- Khi chưa có key, hết ngân sách, hoặc bộ lọc chặn: khung nói rõ lý do và không gửi gì.

## Không làm

- Không cho AI đọc dữ liệu cá nhân, kể cả khi bạn dán vào câu hỏi: bộ lọc chặn.
- Không cho AI tự lưu hay sửa bất kỳ dữ liệu nào.
- Không dùng AI để đưa khuyến nghị mua bán. Câu trả lời chỉ tóm tắt tài liệu.
- Không OCR, không đăng nhập vào nguồn nào.

## Kiểm thử

- **Bộ lọc:** mỗi loại bị chặn có test riêng (số tiền, cụm từ về bản thân, tên sổ, mã khác). Thêm test cho các câu được phép, có năm và số thuyết minh.
- **Payload:** test khẳng định gói gửi đi chỉ có mã, câu hỏi và các đoạn trích. Không có trường cá nhân nào, giống cách `payloads.py` đang làm.
- **Kiểm tra câu trả lời:** số không khớp văn bản, trang không có trong các đoạn đã gửi, và JSON sai đều bị loại.
- **Gọi mô hình:** dùng mô hình giả trong test. Chạy thật một lần với một BCTC công khai sau khi bạn duyệt, rồi đối chiếu vài câu trả lời với PDF gốc.
