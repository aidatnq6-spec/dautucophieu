# Thiết kế: trang "Nhận định" (AI đọc báo cáo vĩ mô, ngành, chiến lược)

Ngày: 26/10/2026 · Trạng thái: chờ chủ sở hữu duyệt

## Mục đích

Chủ sở hữu không có thời gian tìm và đọc báo cáo vĩ mô, ngành, chiến lược của các tổ chức tài chính. Khi có báo cáo mới, ứng dụng tự đọc rồi trả lời hai câu hỏi:

1. **Vĩ mô hiện tại và triển vọng thuận lợi hay bất lợi?**
2. **Ngành nào hưởng lợi, ngành nào bất lợi?**

Kết quả hiện trên trang mới **"Nhận định"** và được gửi qua Telegram. Kèm theo là gợi ý tham khảo nối với 50 mã theo dõi và kết luận của trang Định giá.

## Mục tiêu

- **Nguồn** (chủ sở hữu chọn, đã kiểm tra ngày 26/10/2026):
  - **ACBS:** đọc toàn văn. Lấy từ trang danh sách công khai `acbs.com.vn/trung-tam-phan-tich/bao-cao-tong-quan` (báo cáo vĩ mô, chiến lược, tổng quan). File PDF tải trực tiếp, không cần đăng nhập, `robots.txt` cho phép. Ví dụ: `acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf`, 5,2 MB.
  - **World Bank:** đọc toàn văn. Lấy qua API tài liệu chính thức `search.worldbank.org/api/v2/wds`, lọc tài liệu về Việt Nam có tính chất báo cáo kinh tế.
  - **SSI:** chỉ lấy **tiêu đề** từ các trang danh sách công khai `ssi.com.vn/khach-hang-ca-nhan/bao-cao-vi-mo`, `/bao-cao-nganh`, `/bao-cao-chien-luoc`, dùng làm tín hiệu phụ. Tải PDF của SSI phải đăng nhập, và ứng dụng **không đăng nhập thay chủ sở hữu**.
- **Khi nào đọc:** mỗi lần lịch chạy, ứng dụng kiểm tra báo cáo mới. Chỉ báo cáo chưa xử lý mới được đọc.
- **AI:** gọi qua OpenRouter, ngân sách **2 USD/tháng**. Chủ sở hữu đã đồng ý với điều kiện chỉ gửi nội dung báo cáo công khai.
- **Kết quả cho mỗi báo cáo mới:**
  - **Vĩ mô:** kết luận *hiện tại* và *triển vọng 6–12 tháng*, mỗi phần là Thuận lợi / Trung tính / Bất lợi, kèm 3–5 lý do ngắn.
  - **Ngành hưởng lợi / bất lợi:** mỗi ngành kèm lý do.
  - **Trích dẫn:** mỗi nhận định kèm câu trích nguyên văn, số trang và link gốc.
- **Bản tổng hợp trên trang "Nhận định":** gộp các báo cáo trong 60 ngày gần nhất.
  - Kết luận vĩ mô theo số nguồn đồng ý, liệt kê theo từng nguồn.
  - Danh sách ngành hưởng lợi / bất lợi, ghi rõ nguồn nào nói gì.
  - Khi các nguồn khác nhau, ghi cả hai quan điểm và không tự chọn bên.
- **Gợi ý tham khảo, ghép ngay trên máy:**
  - Mỗi ngành hưởng lợi kèm các mã thuộc ngành đó trong 50 mã theo dõi, cùng kết luận Định giá (Rẻ / Hợp lý / Đắt).
  - Ngành bất lợi mà chủ sở hữu đang nắm mã thì được đánh dấu cảnh báo.
- **Telegram:** gửi tóm tắt mỗi khi có báo cáo mới đã xử lý xong, theo cài đặt Telegram hiện có ("Gửi tự động theo lịch").

## Không làm

- Không đưa khuyến nghị mua bán hay lệnh. Không thay đổi danh sách nghiên cứu hay vùng mua hiện có.
- Không đọc toàn văn báo cáo của SSI. Không dùng VNDirect, MBS, IMF (đều trả lỗi 403). Không dùng KBSV, VCBS, Mirae trong bản này (danh sách tải qua API nội bộ hoặc JavaScript).
- Không lấy báo cáo qua trang trung gian như Vietstock hay CafeF.

## Điều không được xảy ra

- **Không gửi thông tin cá nhân cho AI.** Yêu cầu gửi đi chỉ chứa văn bản báo cáo công khai cùng hướng dẫn. Không có mã đang nắm, tỷ trọng, số tiền, danh sách theo dõi hay kết quả định giá. Có bài kiểm thử tự động bảo đảm điều này. Phần ghép với danh mục chạy trên máy.
- **Không để AI bịa.** Nhận định nào có câu trích không tìm thấy trong văn bản đã trích xuất (sau khi chuẩn hóa khoảng trắng và dấu câu) thì bị loại. Nếu cả báo cáo không còn nhận định hợp lệ, ghi "không đọc được nhận định đáng tin" và không gửi Telegram.
- **Không vượt ngân sách.** Hết ngân sách tháng thì ngừng đọc báo cáo mới, trên trang ghi rõ lý do.
- **Không đăng nhập** bằng tài khoản của chủ sở hữu ở bất kỳ nguồn nào.
- **Không trình bày như lời khuyên đầu tư.**

## Ràng buộc

- **Cổng AI dùng lại phần đã có** trong `ai/openrouter.py`: chính sách, ngân sách, chỉ dùng endpoint không lưu dữ liệu (ZDR) và không thu thập dữ liệu.
  - Cần một chính sách AI **đã duyệt**: `config\ai-policy.json` với `status: approved` và `monthly_usd: 2`.
  - Model do chủ sở hữu duyệt. Người lập trình đề xuất 1–2 model rẻ, đọc tiếng Việt tốt, hỗ trợ ZDR, kèm giá thực tế lúc đề xuất.
- **Chủ sở hữu tự làm:** tạo tài khoản OpenRouter, đặt giới hạn chi tiêu cho key, tắt tùy chọn cho phép dùng dữ liệu để huấn luyện, và lưu `OPENROUTER_API_KEY` vào `.env.local` ở thư mục gốc. Chưa có key thì trang ghi "Chưa cấu hình AI", không có lỗi nào khác.
- **Trích văn bản PDF:** dùng thư viện Python thuần như `pypdf` (thêm vào dependencies). PDF dạng ảnh không có chữ thì ghi "không trích được văn bản" và bỏ qua, không OCR.
- **Tải về:** User-Agent riêng của ứng dụng, tôn trọng `robots.txt`, mỗi lần chạy tối đa vài tệp, có khoảng nghỉ giữa các lần tải.
- **Chạy trên máy chủ sở hữu, theo lịch hiện có.** Dữ liệu lưu trong `data\`.

## Quyết định của người viết (chủ sở hữu có thể đổi)

1. **Hai bước, AI chỉ ở bước đầu:**
   - Bước 1: AI trích từ **mỗi báo cáo** một JSON có cấu trúc (kết luận vĩ mô, ngành, lý do, câu trích, trang).
   - Bước 2: **tổng hợp nhiều báo cáo làm bằng code trên máy**, không gọi AI thêm. Cách này rẻ, lặp lại được và dễ kiểm tra.
2. **Tên ngành chuẩn hóa về ICB cấp 2**, cùng danh sách trang Định giá đang dùng (`data\industries.json`). AI phải chọn trong danh sách đóng đó, nên ghép được với 50 mã theo dõi. Ngành ngoài danh sách thì ghi "khác" và không ghép.
3. **Tiêu đề SSI** chỉ hiện như "SSI vừa ra báo cáo: …" kèm link. Không suy ra kết luận, không gửi cho AI, và không tính vào số phiếu tổng hợp.
4. **Giới hạn mỗi lần chạy:** tối đa 3 báo cáo mới; mỗi báo cáo cắt ở khoảng 60 trang đầu. Phần dư để lần chạy sau.
5. **Lần chạy đầu** chỉ lấy báo cáo trong 60 ngày gần nhất, để không tốn ngân sách cho báo cáo cũ.
6. **Lưu trữ:**
   - mỗi báo cáo một tệp `data\insights\reports\<nguồn>-<id>.json` (nguồn, link, ngày, văn bản đã trích, kết quả AI đã kiểm tra, chi phí);
   - bản tổng hợp tính khi mở trang;
   - không lưu PDF gốc.
7. **Ngôn ngữ:** câu trích giữ nguyên ngôn ngữ gốc của báo cáo (tiếng Anh với World Bank), để kiểm tra khớp được với văn bản. Kết luận và lý do luôn viết bằng tiếng Việt.
8. **Định dạng Telegram:** tiêu đề báo cáo, kết luận vĩ mô, tối đa 5 ngành hưởng lợi và 5 ngành bất lợi kèm mã liên quan và kết luận Định giá, cùng link gốc.

## Để người lập trình quyết định

- **Cách đọc từng nguồn:**
  - danh sách ACBS: mẫu đường dẫn `trung-tam-phan-tich/chi-tiet/...`, rồi tìm PDF trong trang chi tiết;
  - bộ lọc tài liệu World Bank (loại tài liệu, ngôn ngữ);
  - trang tiêu đề SSI: mẫu đường dẫn `analysis-center/report/download/<slug>`.
- Lược đồ JSON của bước 1, lời nhắc (prompt) và cách chuẩn hóa khi kiểm tra câu trích.
- Tên module, API, cách chia hàm, bố cục chi tiết của trang.

## Tiêu chí hoàn thành

- Có báo cáo mới từ ACBS hoặc World Bank thì lần chạy kế tiếp tạo bản tóm tắt đã kiểm tra trích dẫn, hiện trên trang "Nhận định" và gửi Telegram nếu đã bật.
- Có kiểm thử cho:
  - phát hiện báo cáo mới và bỏ qua báo cáo đã xử lý;
  - trích văn bản PDF;
  - loại nhận định có câu trích không khớp văn bản;
  - **yêu cầu gửi AI không chứa dữ liệu cá nhân**;
  - dừng khi hết ngân sách hoặc chưa có key;
  - tổng hợp nhiều nguồn, kể cả khi các nguồn khác ý;
  - ghép ngành với mã và kết luận Định giá;
  - định dạng Telegram;
  - trang hiển thị và không cuộn ngang trên điện thoại.
- `verify.ps1` đạt.
- Chạy thật với một báo cáo ACBS sau khi chủ sở hữu có key, đối chiếu vài câu trích với PDF gốc.
