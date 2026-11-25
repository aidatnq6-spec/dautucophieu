# Tài sản cố định trong Bảng số tài chính (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026, nguyên văn. Kaizen từ bài "Tài sản cố định, BĐS đầu tư và chi phí XDCB dở dang" (khóa đọc BCTC, ví dụ HPG 2021): bảng cân đối
chưa có dòng nào về tài sản cố định, nên phần mềm không cho thấy doanh nghiệp đang mở rộng hay chỉ duy trì, tài sản cũ đến đâu, và bao nhiêu
tài sản sắp hình thành từ XDCB dở dang. Phần này gồm bước 1 (lấy dữ liệu) và bước 2 (nhóm dòng mới); hai tín hiệu XDCB ở Chất lượng báo
cáo và ghi chú thuyết minh nhập tay là các phần sau. Chỉ dữ liệu công khai, không đọc danh mục, không gọi AI.

## Nguồn (`market/statements.py`)
- Cùng API `v4/financial_statements`, mẫu chung (modelType 1). Tên dòng đã kiểm trong `v4/financial_models` ngày 25/11/2026; thêm vào `LINES`:
  - 12210 TSCĐ hữu hình (còn lại), 12220 nguyên giá, 12230 hao mòn lũy kế (số âm);
  - 12240 TSCĐ thuê tài chính (còn lại);
  - 12270 TSCĐ vô hình (còn lại), 12280 nguyên giá, 12290 hao mòn lũy kế;
  - 12400 BĐS đầu tư (còn lại), 12410 nguyên giá, 12420 hao mòn lũy kế;
  - 12460 chi phí XDCB dở dang (mẫu từ 2015) và 12300 chi phí XDCB dở dang (trước 2015).
- **XDCB một dòng từ hai mã**: kỳ nào chỉ một mã khác 0 thì lấy mã đó; cả hai bằng 0 thì là 0; cả hai khác 0 và khác nhau là xung đột
  (để trống, liệt kê cả hai như quy tắc xung đột hiện có).
- Đã đối chiếu HPG 31/12/2021 với bài học: TSCĐ hữu hình còn lại 68.744,1 tỷ (bài: 68.744), XDCB 8.289,3 tỷ (bài: 8.289,289), TSCĐ vô
  hình 536,7 tỷ (bài: 536), thuê tài chính 0 (bài: không phát sinh). Bảng HPG dựng từ số thật: 2014 lấy XDCB mã 12300 (429,5 tỷ);
  2024 XDCB ÷ TSCĐ 94,7 %, capex ÷ khấu hao 5,13 lần; 2025 sau kết chuyển Dung Quất 2: 8,0 % và nguyên giá 182.309 tỷ; không lệch ở Kiểm tra chéo. Có số năm từ 2020 và 27 quý (lượt kiểm chỉ lấy từ 2020).
- Tăng `LINES_VERSION`: mỗi mã doanh nghiệp thường lấy lại toàn bộ lịch sử một lần ở các lượt 20:00 sau (8 mã mỗi lượt như hiện nay).
- VNDirect chỉ có số dư cuối kỳ, **không có số phát sinh tăng, giảm** của thuyết minh (bài học: XDCB HPG 2021 tăng khoảng 12.000 tỷ,
  giảm 9.100 tỷ). Phần mềm không suy ra số kết chuyển từ chênh lệch số dư.

## Bảng (`valuation/statement_table.py`)
Nhóm mới **Tài sản cố định**, sau nhóm Dòng tiền, trước Quy mô và định giá; chỉ cho doanh nghiệp thường. Cột quý là số cuối quý, cột năm
là số cuối năm (số dư, không cộng 4 quý).

| Dòng | Cách tính |
|---|---|
| TSCĐ hữu hình (còn lại) | 12210 |
| Nguyên giá TSCĐ hữu hình | 12220 |
| Hao mòn lũy kế TSCĐ hữu hình | 12230 (âm) |
| TSCĐ vô hình (còn lại) | 12270 |
| BĐS đầu tư (còn lại) | 12400 |
| Chi phí XDCB dở dang | 12460 / 12300 như trên |
| Mức hao mòn TSCĐ hữu hình | \|hao mòn lũy kế\| ÷ nguyên giá (%) |
| XDCB ÷ TSCĐ hữu hình | XDCB dở dang ÷ TSCĐ hữu hình còn lại (%) |
| Capex ÷ khấu hao | \|capex\| ÷ khấu hao (lần); quý: 4 quý tới quý đó, năm: số cả năm |
| Vòng quay TSCĐ hữu hình | Doanh thu thuần ÷ TSCĐ hữu hình còn lại bình quân (lần); quý: doanh thu 4 quý ÷ bình quân cuối quý và cùng quý năm trước; năm: doanh thu năm ÷ bình quân cuối năm đó và năm trước |

- Thuê tài chính không thành dòng riêng; khác 0 thì ghi chú dưới bảng, liệt kê các kỳ (đa số mã bằng 0; HPG chỉ có 4 quý 2012).
- Ở chế độ Quý, hai dòng tính trên 4 quý ghi thêm "(4 quý)" sau tên.
- Thiếu một thành phần, khấu hao bằng 0 hoặc mẫu số không dương thì để trống, không ước lượng. Thiếu một trong 4 quý thì để trống các dòng 4 quý.
- **Kiểm tra chéo** (lệch hơn 0,5 %, cùng mục hiện có): còn lại = nguyên giá + hao mòn lũy kế, với TSCĐ hữu hình, TSCĐ vô hình và BĐS đầu tư.
  Trang liệt kê, không sửa số.
- Cột Xu hướng, biểu đồ lớn và Xem số liệu dùng như các dòng khác (tiền: cột; %, lần: đường).

## API và giao diện
- `GET /internal/fairvalue/statements/{mã}` trả thêm nhóm này; mã chưa lấy lại lịch sử thì các dòng để trống và ghi "chưa đồng bộ dòng tài sản cố định".
- Chú thích dưới bảng: ý nghĩa ngắn của từng chỉ số (capex ÷ khấu hao lớn hơn 1: đang đầu tư nhiều hơn phần hao mòn; XDCB lớn so với TSCĐ:
  tài sản sắp hình thành, khấu hao sẽ tăng khi kết chuyển), và câu "VNDirect không có số phát sinh tăng, giảm của thuyết minh".

## Không làm trong phần này
- Tín hiệu "XDCB vừa kết chuyển" và "XDCB phình kéo dài", đánh dấu biến động bất thường (ví dụ BĐS đầu tư HPG Q3/2026 về 0, nguyên giá còn 4,8 tỷ):
  phần sau, ngưỡng do chủ sở hữu chọn. (BĐS đầu tư HPG Q3/2026: nguyên giá 4,8 tỷ, hao mòn −4,8 tỷ, còn lại 0, nên Kiểm tra chéo không báo lệch.)
- Ghi chú thuyết minh nhập tay (dự án trong XDCB, khung thời gian khấu hao, ngày hoàn thành dự kiến) gắn Luận điểm.
- Tách hàng tồn kho, BĐS đầu tư, TSCĐ cho mã bất động sản.
- Ngân hàng, chứng khoán, bảo hiểm (mẫu khác).
