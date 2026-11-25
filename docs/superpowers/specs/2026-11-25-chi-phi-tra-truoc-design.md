# Chi phí trả trước trong Bảng số tài chính và Chất lượng báo cáo (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 và 2 của đề xuất; ngưỡng trọng yếu 10% LNTT). Kaizen từ bài "Chi phí trả trước ngắn hạn, dài hạn"
(ví dụ HPG 2021, thuyết minh 17.1): chi phí đã trả tiền nhưng ghi thành tài sản rồi phân bổ dần là "nguồn" chi phí của các năm sau, và tăng nhanh
hơn doanh thu có thể là đưa chi phí vào tài sản để đẩy lợi nhuận. Chỉ doanh nghiệp thường, dữ liệu công khai, không gọi AI.

## Nguồn (`market/statements.py`)
- Thêm dòng (tên kiểm trong `v4/financial_models` ngày 25/11/2026): 11510 chi phí trả trước ngắn hạn, 12610 chi phí trả trước dài hạn
  (bảng cân đối), 31160 tăng, giảm chi phí trả trước (lưu chuyển tiền tệ, âm khi số dư tăng). Khác "trả trước cho người bán" (11320).
- Đối chiếu HPG 31/12/2021: ngắn hạn 296,7 tỷ (bài: 296), dài hạn 3.171,4 tỷ (bài: 3.171).
- Tăng `LINES_VERSION` lên 9: mỗi mã lấy lại lịch sử một lần (hoặc chạy `statements-sync --all`).
- VNDirect không có số phân bổ trong năm của thuyết minh (HPG 2021: 425 tỷ); phần mềm không suy ra.
- Dòng 31160 chỉ là phần vận hành: HPG 2021 số dư tăng 1.681 tỷ nhưng dòng tiền ghi −814 tỷ (phần còn lại qua đầu tư, mua công ty), nên
  không dùng làm kiểm tra chéo.

## Bảng số tài chính
Nhóm **Chi phí trả trước**, sau Tài sản cố định: ngắn hạn; dài hạn; tổng; tổng ÷ tổng tài sản (%); tổng ÷ LNTT (lần; quý: LNTT 4 quý tới quý
đó, năm: LNTT năm; LNTT không dương thì để trống); tăng, giảm chi phí trả trước trên lưu chuyển tiền tệ (tỷ, số của kỳ). Số dư là cuối kỳ.
Ghi chú "Chưa đồng bộ" như nhóm Tài sản cố định cho bản ghi trước phiên bản 9.

## Dấu hiệu "Chi phí trả trước tăng nhanh hơn doanh thu" (Chất lượng báo cáo, sau hai dấu hiệu XDCB)
- Bản ghi cơ bản lấy thêm chi phí trả trước ngắn hạn và dài hạn theo năm.
- Bật khi năm gần nhất: tổng chi phí trả trước (ngắn + dài hạn) tăng nhanh hơn doanh thu từ **20 điểm %** (cùng mốc dấu hiệu phải thu), và
  phần tăng thêm từ **10% LNTT** năm đó (doanh nghiệp lỗ trước thuế: chỉ cần điều kiện tăng nhanh hơn).
- Hiện tổng hai năm (ngắn, dài hạn), mức tăng so với doanh thu, phần tăng thêm so với LNTT. Nhắc đọc thuyết minh: khoản gì được đưa vào
  (sửa chữa lớn, tiền thuê đất, chi phí trước hoạt động) và phân bổ bao nhiêu năm.
- Thiếu một dòng hoặc năm trước bằng 0: không đánh giá được.
- Thử trên 41 mã theo dõi, năm 2025: 6 mã bật.
- Chỉ hiện trên trang (không vào Bảng dấu hiệu phải thu, Telegram, bản tin tuần).
