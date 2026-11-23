# Tồn kho: ba căn cứ kiểm kê và giá hàng hóa (chủ sở hữu duyệt 23/11/2026)

Kaizen từ tài liệu của chủ sở hữu "Dự phòng giảm giá hàng tồn kho và Phân tích Báo cáo tài chính" (mục 2: ba căn cứ kiểm kê ngày 31/12). Mục 1
và mục 3 của tài liệu (định nghĩa, case MWG 2021) đã có trong khối Tồn kho (spec 2026-11-22-ton-kho-design.md). Chỉ dùng số công khai của
VNDirect và giá hàng hóa đã có trong kho Vĩ mô, không gọi AI, không đoán số.

Áp dụng cho mã phi tài chính đang theo dõi, trừ bất động sản (tồn kho của họ là dự án). Ngưỡng trọng yếu giữ như cờ tồn kho hiện có: tồn kho
thuần từ 10% tổng tài sản.

Tỷ lệ trích lập = dự phòng giảm giá ÷ giá gốc hàng tồn kho (dòng 11490 và 11410).

## Tần suất trên số thật (đếm 23/11/2026)
Phạm vi đếm: 34 mã phi tài chính đang theo dõi, trừ bất động sản. Trong đó 22 mã có tồn kho trọng yếu (từ 10% tổng tài sản), từ Q1/2018.

| Đề xuất | Cách đếm | Tỷ lệ bật |
|---|---|---|
| 1. Bán dưới giá vốn | Lãi gộp của quý âm | 11/648 = 1,7% |
| | ... và tỷ lệ trích lập không tăng so với quý trước | 2/648 = 0,3% |
| 2. Dự phòng mỏng dần | Số ngày tồn kho tăng so cùng kỳ, tỷ lệ trích lập giảm | 183/641 = 28,5% |
| | Số ngày tăng từ 20%, tỷ lệ trích lập giảm từ 20% của mức cũ | 69/641 = 10,8% |
| | Số ngày tăng từ 30%, tỷ lệ trích lập giảm từ 20% của mức cũ | 45/641 = 7,0% |
| 3. Dự phòng dồn vào quý 4 | Quý 4 chiếm từ 50% mức tăng dự phòng cả năm | 89/185 = 48,1% |
| | Quý 4 chiếm từ 80% mức tăng dự phòng cả năm | 74/185 = 40,0% |
| | Số dư quý 4 tự lập khác số dư năm kiểm toán (lệch hơn 1 tỷ và hơn 1%) | 32/270 = 11,9% |
| 4. Giá đầu ra giảm | Giá giảm từ 10% so cùng kỳ, tỷ lệ trích lập không tăng | 3/20 = 15,0% |

Với đề xuất 4, chỉ 20 quý có đủ số để xét. Lý do là chuỗi giá trong kho Vĩ mô còn ngắn: urê, đường và cao su mỗi loại có 36 tháng, HRC mới
có 7 điểm.

## 1. Bán dưới giá vốn nhưng dự phòng không tăng (căn cứ 3)
- Bật khi lãi gộp của quý âm và tỷ lệ trích lập không tăng so với quý trước. Bán dưới giá vốn là dấu hiệu giá trị thuần có thể thu hồi đã thấp
  hơn giá ghi sổ.
- Không cần thêm ngưỡng: cờ hiếm (0,3%) và rõ nghĩa.
- Hiện trên hồ sơ mã (khối Tồn kho) và Bảng dấu hiệu, kèm số: lãi gộp của quý, tỷ lệ trích lập quý này và quý trước.

## 2. Dự phòng mỏng dần trong khi hàng tồn lâu hơn (căn cứ 2)
- Không có nguồn công khai cho tuổi hàng tồn kho, nên dùng số ngày tồn kho làm đại diện. Cách tính như cờ hiện có: tồn kho thuần ÷ giá vốn
  bốn quý × 365.
- Bật khi số ngày tồn kho tăng **từ 20%** so cùng kỳ và tỷ lệ trích lập giảm **từ 20% của mức cùng kỳ**. Theo bảng trên, cờ bật ở 10,8% số
  quý. Bản không ngưỡng bật ở 28,5%, quá thường.
- Hiện trên hồ sơ mã và Bảng dấu hiệu, kèm số ngày và tỷ lệ trích lập của hai kỳ.

## 3. Dự phòng chốt khi kiểm toán cuối năm (kiểm kê ngày 31/12)
- Dự phòng dồn vào quý 4 là việc thường gặp (từ 80% ở 40% số năm). Vì vậy phần này **không bật cờ**, chỉ hiện số trong khối Tồn kho: mức tăng
  dự phòng của cả năm và phần quý 4 chiếm, theo từng năm.
- Thêm dòng "Dự phòng giảm giá tồn kho" vào "Số đã công bố bị sửa", để ghi lại khi nguồn sửa số của một kỳ đã đóng.
- Ghi riêng mỗi năm có số dư quý 4 tự lập khác số dư trên báo cáo năm kiểm toán (lệch hơn 1 tỷ và hơn 1%; xảy ra ở 11,9% số năm). Lần đầu
  thấy chênh lệch này ở mã đang giữ thì báo một lần trong lượt báo dấu hiệu.

## 4. Giá đầu ra giảm nhưng dự phòng không đổi
- Chỉ dùng chuỗi giá đã gắn với ngành trong Chuỗi giá trị ngành, có căn cứ từ báo cáo:
  - giá bán (khâu đầu ra) cho hàng hóa thật: thép HPG – HRC, cao su GVR/PHR/DPR, phân bón DCM/DPM – urê, mía đường SBT – đường;
  - riêng tôn mạ HSG/NKG dùng HRC dù HRC là đầu vào, vì tồn kho của họ chủ yếu là HRC.
- Không áp dụng cho dịch vụ (cước tàu, khoan), vì các ngành này không có hàng tồn để bán.
- Bật khi giá giảm **từ 10%** so cùng kỳ (lấy giá cuối quý so với cuối cùng quý năm trước) và tỷ lệ trích lập không tăng so cùng kỳ.
- Chuỗi giá chưa đủ 13 tháng thì ghi "chưa đủ lịch sử giá" và không xét. Hiện HRC chưa đủ, nên HPG, HSG và NKG chưa có cờ này cho tới khi đủ
  dữ liệu.
- Hiện trên hồ sơ mã và Bảng dấu hiệu, kèm tên chuỗi giá, hai mức giá và nguồn.

## Ngoài phạm vi
- Tuổi hàng tồn kho và cơ cấu tồn kho (nguyên liệu, dở dang, thành phẩm): không có nguồn công khai.
- Lấy thêm lịch sử giá HRC: việc riêng, cần tìm nguồn công khai.
- Không khuyến nghị mua bán.

## Thứ tự
1 → 2 → 3 → 4, mỗi phần một nhánh, TDD, verify rồi merge. Các ngưỡng (20% và 20% ở mục 2, 10% ở mục 4, 1 tỷ và 1% ở mục 3) do chủ sở hữu chốt ngày 23/11/2026.
