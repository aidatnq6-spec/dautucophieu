# Đánh giá nguồn dữ liệu trả phí — FiinQuant và FiinGroup Datafeed

Tra cứu 25/10/2026 từ trang công khai; chưa liên hệ nhà cung cấp, chưa đăng ký, chưa mua. Mục tiêu: tìm nguồn đáp ứng yêu cầu thiết kế mà Vnstock không đạt (10 năm, giá gốc + hệ số điều chỉnh, BCTC 40 quý có ngày công bố, sự kiện quyền, quyền lưu cục bộ).

## FiinQuant (thư viện Python cho cá nhân)

| Yêu cầu | Thông tin công khai | Đánh giá |
|---|---|---|
| Giá ngày ≥ 10 năm | Gói Cơ bản và Nâng cao: 10 năm; Chuyên nghiệp: 15 năm; gói dùng thử 1 năm, 33 mã | Có thể đạt từ gói Cơ bản |
| Giá gốc / điều chỉnh | Không nêu | Cần hỏi |
| BCTC 10 năm, 40 quý | Trang giá liệt kê chỉ số tài chính, lịch sử P/E/P/B theo độ sâu 1/3/5/10 năm, nhưng không ghép rõ với gói; danh mục dữ liệu của thư viện Python chỉ có giá, sổ lệnh, dòng tiền, khối ngoại, chỉ số kỹ thuật | **Chưa xác nhận** thư viện có BCTC |
| Ngày công bố, bản sửa | Không nêu | Cần hỏi |
| Sự kiện quyền, cổ tức | Không nêu | Cần hỏi |
| Giới hạn gọi | Cơ bản: 200.000 lệnh/tháng, 720/phút | Đủ cho 50 mã |
| Giá | Trang không hiển thị giá theo gói; **đăng ký trực tuyến đang tạm dừng**, cần liên hệ | Chưa có báo giá |
| Quyền sử dụng | Có liên kết Điều khoản sử dụng, chưa đọc được nội dung | Cần đọc trước khi mua |

Ngoài ra FiinQuant có máy chủ MCP cho trợ lý AI (ra mắt 06/2026), tách biệt với thư viện Python.

## FiinGroup API Datafeed (doanh nghiệp)

Trang sản phẩm mô tả: Price Feed, Corporate Reference Data, Corporate Financials, Corporate Actions Data, Ratio Datafeed, cập nhật ngay khi nguồn công bố. Đây là nhóm dữ liệu khớp nhất với yêu cầu, nhưng không công bố giá hay gói cho cá nhân; phải liên hệ bán hàng. Lần khảo sát trước trang này trả lỗi 503.

## Kết luận tạm thời

- FiinQuant có thể giải quyết **độ sâu giá 10 năm** ở gói Cơ bản, nhưng chưa có bằng chứng về BCTC, ngày công bố, sự kiện quyền.
- FiinGroup Datafeed có đúng nhóm dữ liệu cần, có thể ở mức giá doanh nghiệp.
- Chưa đủ thông tin để đề xuất mua. Bước tiếp theo là gửi câu hỏi dưới đây; tôi không liên hệ thay bạn.

## Câu hỏi gửi nhà cung cấp (bạn gửi qua kênh liên hệ của FiinQuant/FiinGroup)

1. Gói nào cho phép lấy qua API/Python: giá ngày 10 năm cho toàn bộ cổ phiếu HOSE, kèm **giá chưa điều chỉnh và hệ số điều chỉnh** (hoặc lịch sự kiện để tự điều chỉnh)?
2. BCTC theo quý và năm từ 2015: có bản hợp nhất và riêng, **ngày công bố** của từng báo cáo, và lịch sử các bản điều chỉnh/kiểm toán lại không?
3. Sự kiện doanh nghiệp: cổ tức tiền/cổ phiếu, phát hành thêm, tách/gộp, chuyển sàn, đổi mã — có ngày GDKHQ, ngày chốt, ngày thanh toán, tỷ lệ?
4. Số cổ phiếu lưu hành theo từng thời điểm (để tính EPS, P/B đúng kỳ)?
5. Điều khoản cho cá nhân: được lưu dữ liệu cục bộ, tính chỉ số, gửi phần tóm tắt dẫn xuất cho dịch vụ AI, và chia sẻ bản tin cá nhân trong nhóm Telegram riêng không?
6. Giá theo tháng/năm (gồm VAT), hạn mức lượt gọi, số thiết bị, và có gói dùng thử với dữ liệu BCTC không?

## Nguồn

- [FiinQuant — Giá & chi phí](https://fiinquant.vn/Pricing)
- [FiinQuant — Danh sách dữ liệu hiện có](https://docs.fiinquant.vn/tai-lieu-ki-thuat/danh-sach-du-lieu-hien-co)
- [FiinGroup — ra mắt FiinQuantMCP](https://fiingroup.vn/vi/news-fg/fiingroup-ra-mat-fiinquantmcp-dua-du-lieu-chung-khoan-viet-nam-vao-ky-nguyen-ai-id3052741.html)
- [FiinGroup — Stock Data Solutions (API Datafeed)](https://fiingroup.vn/en/stock-data-solutions-api-datafeed-microsite.html)
