# Hai dấu hiệu XDCB dở dang ở Chất lượng báo cáo (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 và chọn ngưỡng (phương án khuyến nghị của cả hai). Phần sau của [Tài sản cố định](2026-11-25-tai-san-co-dinh-design.md),
từ bài "Tài sản cố định, BĐS đầu tư và chi phí XDCB dở dang" (ví dụ HPG, Dung Quất 2). Hai dấu hiệu thêm vào cuối danh sách "Dấu hiệu cần xem kỹ"
của [Chất lượng báo cáo](2026-10-31-chat-luong-bao-cao-design.md), cùng cách hiện (số thật các năm, quy tắc của ứng dụng, không gộp điểm).
Chỉ doanh nghiệp thường. Chỉ dữ liệu công khai, không gọi AI. Không vào Bảng dấu hiệu phải thu, nhắc Telegram hay bản tin tuần.

## Nguồn
- Bản ghi cơ bản (`market/fundamentals_vndirect.py`, mục `annual`) lấy thêm từ báo cáo VNDirect đã lưu: XDCB dở dang, TSCĐ hữu hình còn
  lại, nguyên giá TSCĐ hữu hình, khấu hao (lưu chuyển tiền tệ). Có sau lần làm mới bản ghi cơ bản kế tiếp của từng mã (lượt 20:00).
- VNDirect chỉ có số dư cuối năm, không có số phát sinh tăng, giảm hay kết chuyển của thuyết minh; hai dấu hiệu đọc từ số dư.

## XDCB dở dang phình kéo dài
- Bật khi XDCB dở dang tăng **3 năm liên tiếp** (năm Y > Y−1 > Y−2 > Y−3) và năm Y từ **20%** TSCĐ hữu hình còn lại năm Y.
- Ý nghĩa: dự án có thể chậm, hoặc chi phí đang giữ ở tài sản thay vì ghi vào chi phí; đọc thuyết minh XDCB. Dự án lớn đúng tiến độ cũng bật.
- Hiện XDCB 4 năm và tỷ lệ với TSCĐ năm Y. Thiếu một năm hoặc TSCĐ năm Y không dương: không đánh giá được.

## XDCB dở dang vừa kết chuyển
- Bật khi cả ba cùng đúng: XDCB năm Y−1 từ **10%** TSCĐ hữu hình còn lại năm Y−1; XDCB năm Y giảm từ **50%** so với Y−1; nguyên giá TSCĐ
  hữu hình tăng ít nhất **một nửa** phần XDCB giảm (để không nhầm với bán, huỷ dự án).
- Ý nghĩa: dự án đã đưa vào dùng, khấu hao các kỳ sau sẽ tăng. Hiện XDCB hai năm, mức giảm, mức tăng nguyên giá và khấu hao hai năm.
- Thiếu XDCB, nguyên giá hai năm hoặc TSCĐ năm Y−1 không dương: không đánh giá được.

## Đối chiếu (25/11/2026, báo cáo VNDirect đã lưu)
- HPG: 2023 và 2024 bật "phình kéo dài" (36,3 %, 94,7 % TSCĐ); 2025 tắt, bật "vừa kết chuyển" (63.656 → 10.721 tỷ, −83,2 %; nguyên giá +74.162
  tỷ; khấu hao 6.916 → 8.471 tỷ).
- 41 mã doanh nghiệp thường, năm gần nhất: "phình kéo dài" bật 6, "vừa kết chuyển" bật 2, 1 mã thiếu số.
