# Năm tài chính: Tổng kết năm, Mục tiêu năm sau, Việc cuối năm (chủ sở hữu duyệt 22/11/2026)

Trang mới **Năm tài chính** trong nhóm cá nhân. Dữ liệu cá nhân, chỉ chạy trên máy, không gửi AI. Mọi số lấy từ phần đã có; thiếu thì ghi
thiếu kèm lý do, không ước lượng.

## 1. Tổng kết năm (chọn năm; năm đang chạy ghi "tính đến ngày …")
- **Danh mục cổ phiếu:** lợi suất năm nối từ các tháng của Hiệu suất (cùng phương pháp, đã trừ tiền nộp/rút), so với VN-Index cùng kỳ;
  giá trị danh mục phiên cuối năm trước và phiên mới nhất. Sổ giao dịch bắt đầu sau 01/01 thì tính từ ngày bắt đầu sổ và ghi rõ.
- **Tiền vào, ra:** tổng nộp, tổng rút trong năm (Sổ giao dịch); so với Góp vốn đều (số tháng × mức hằng tháng) nếu đã đặt.
- **Cổ tức và lãi đã chốt:** cổ tức tiền đã nhận, thuế đã khấu trừ, lãi/lỗ đã chốt trong năm.
- **Thu chi cả năm:** cộng các tháng đã xong của Thu chi hằng tháng; tháng chưa nhập thì kể tên, không lấp; tỷ lệ tiết kiệm của các tháng có số.
- **Tháp tài sản:** cơ cấu hiện tại so với khoảng mục tiêu. **Không có số đầu năm 2026**: phần mềm chưa từng lưu ảnh chụp tổng tài sản.
  Từ nay lưu **ảnh chụp cuối mỗi tháng** (chỉ tổng theo tầng và tổng tài sản, trong kho cá nhân) để từ năm 2027 so được đầu năm với cuối năm.

## 2. Mục tiêu năm sau (bạn nhập; kho cá nhân `settings/year_goals_<năm>`)
- Ba mục tiêu, mục nào cũng có thể bỏ trống: **tiền góp cả năm**, **tỷ lệ tiết kiệm**, **tổng tài sản cuối năm**.
- Mỗi tháng: đã đạt bao nhiêu so với mục tiêu, và so với **tiến độ đều theo thời gian** (ví dụ hết tháng 3 là 25%). Đây là so sánh, không
  phải dự báo.
- Việc tài chính hôm nay (Telegram) thêm một dòng đầu mỗi tháng khi chậm hơn tiến độ đều quá 10 điểm; không chậm thì không có dòng.

## 3. Việc cuối năm (từ 01/12 đến 31/12)
- Danh sách cố định; việc nào kiểm tự động được thì tự đánh dấu, còn lại bạn tự tích:
  - Rà luận điểm các mã đang giữ (tự động: còn mã nào chưa rà trong 90 ngày).
  - Cân lại Tháp tài sản (tự động: còn tầng nào ngoài khoảng).
  - Lịch giao dịch HOSE năm sau đã có (tự động).
  - Diễn tập khôi phục trong 30 ngày qua (tự động).
  - Đặt mục tiêu năm sau (tự động: đã lưu).
  - Đối chiếu cổ tức và thuế khấu trừ cả năm với chứng từ công ty chứng khoán (tự tích).
  - Nhập Thu chi tháng 12 (tự tích; nhắc lại đầu tháng 1).
- Lưu dấu tích ở `settings/year_end_<năm>`. Việc tài chính hôm nay nhắc ngày 01/12 và 20/12 nếu còn việc chưa xong.

## Ngoài phạm vi
- Không dự báo cuối năm, không khuyến nghị mua bán, không tính thuế thu nhập cá nhân.

## Đã làm, đợt 1 (22/11/2026): Việc cuối năm và ảnh chụp cuối tháng
- Trang `/year` trong nhóm Tài sản. Danh sách mở từ 01/12 đến 31/01 (tháng 1 vẫn là danh sách của năm vừa hết). Việc tự kiểm không đọc
  được thì ghi "chưa kiểm được" và tính là còn việc, không bao giờ tính là xong.
- Rà luận điểm: mọi mã đang giữ có luận điểm đang mở, viết hoặc sửa trong 90 ngày. Diễn tập: đạt và trong 30 ngày.
- Nhắc là một phần của Việc tài chính hôm nay, một lần vào hoặc sau 01/12, 20/12, 05/01; chỉ ghi đã nhắc khi gửi được.
- Ảnh chụp `settings/wealth_snapshots`: mỗi ngày ghi đè tháng đang chạy (tổng và số tiền từng tầng của Tháp tài sản), nên mỗi tháng giữ ngày
  cuối cùng được ghi. Chạy trong lượt Việc tài chính hôm nay, nên chỉ chạy khi đang bật gửi tự động.

## Đã làm, đợt 2 (22/11/2026): Tổng kết năm
- Chọn năm nay hoặc năm trước. Năm đang chạy ghi "tính đến ngày …". Mỗi phần đọc riêng; phần không đọc được ghi lý do, các phần khác vẫn hiện.
- Lợi suất: nhân dồn các tháng của Hiệu suất trong năm (đã trừ nộp, rút), VN-Index cùng cách. Giá trị: phiên cuối năm trước (hoặc phiên đầu
  của sổ nếu sổ bắt đầu trong năm, có ghi chú) và phiên cuối trong năm.
- Nộp, rút theo ngày trong năm; cổ tức tiền, thuế khấu trừ, lãi/lỗ đã chốt là sổ dựng lại đến 31/12 trừ sổ đến 31/12 năm trước.
- Góp vốn đều: các tháng của năm đã qua ngày góp; Thu chi: các tháng đã xong, kể tên tháng chưa nhập.
- Tháp tài sản: cơ cấu hiện tại so với mục tiêu; tổng đầu năm (ảnh chụp 12 năm trước) và cuối năm khi có. Năm 2026 ghi rõ không có số đầu năm.

## Đã làm, đợt 3 (22/11/2026): Mục tiêu năm
- Đặt cho năm nay hoặc năm sau (từ tháng 11 mở sẵn năm sau). Tiền góp, tổng tài sản là số đồng nguyên dương; tỷ lệ tiết kiệm trên 0 và dưới 100%.
- Tiến độ đều = số ngày đã qua của năm / số ngày của năm. Tiền góp: nộp trừ rút trong năm. Tổng tài sản: quãng đường từ ảnh chụp tháng 12
  năm trước đến mục tiêu; không có ảnh chụp thì không tính, ghi lý do. Tỷ lệ tiết kiệm: tỷ lệ các tháng Thu chi đã xong so với mục tiêu.
- "Chậm" khi kém tiến độ đều hơn 10 điểm (tỷ lệ tiết kiệm: dưới mục tiêu). Một dòng trong Việc tài chính hôm nay mỗi tháng, từ ngày 1,
  chỉ khi có mục chậm; ghi đã nhắc khi gửi được (`settings/year_goals_reminded_<năm>`).
