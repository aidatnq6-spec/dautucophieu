# Khối Tồn kho: giá gốc, dự phòng, số ngày tồn kho và dự phòng đi vào lợi nhuận (chủ sở hữu duyệt 22/11/2026)

Kaizen từ tài liệu của chủ sở hữu "Hàng tồn kho và phân tích báo cáo tài chính" (MWG, HPG). Chỉ số liệu công khai của VNDirect, không gọi AI,
không đoán số. Mã phi tài chính đang theo dõi. VNDirect (kiểm 22/11/2026): 11410 giá gốc hàng tồn kho, 11490 dự phòng giảm giá (âm), 11400 giá
thuần (MWG 2021: 29.850,1 / −682,8 / 29.167,2 tỷ, khớp tài liệu). Cơ cấu tồn kho (nguyên vật liệu, dở dang, thành phẩm) và số cửa hàng không có
nguồn công khai: ngoài phạm vi.

## 1. Khối Tồn kho trên hồ sơ mã
- Đồng bộ thêm 11410 (`inventory_gross`) và 11490 (`inventory_provision`); bộ dòng lên phiên bản mới nên mỗi mã đọc lại toàn bộ lịch sử một
  lần, như các lần thêm dòng trước.
- Theo quý (bảng 8 quý như mọi bảng, tóm tắt đọc 12 quý): giá gốc, dự phòng giảm giá, giá thuần, **mức bao phủ** = dự phòng ÷ giá gốc, và
  **tồn kho thuần ÷ tổng tài sản**. Thiếu dòng thì để trống; quý chưa có 11410 (trước khi đồng bộ lại) cũng để trống, không suy từ giá thuần.

## 2. Tồn kho tăng nhanh hơn sức bán
- **Số ngày tồn kho** = tồn kho thuần cuối quý ÷ giá vốn bốn quý gần nhất × 365; so với cùng kỳ năm trước và trung vị ngành (các mã theo dõi
  cùng ngành, quý mới nhất của mỗi mã), như số ngày thu tiền.
- Cờ "Tồn kho tăng nhanh hơn giá vốn" khi tồn kho thuần tăng so cùng kỳ nhanh hơn giá vốn bốn quý tăng so cùng kỳ **từ 20 điểm %** và số ngày
  tồn kho tăng so cùng kỳ. Giá vốn bốn quý không dương: không tính.
- Bảng dấu hiệu trên Ngành theo quý thêm cột "Tồn kho tăng nhanh hơn giá vốn" kèm số.
- Giới hạn ghi rõ: không đo được theo từng chuỗi, từng cửa hàng như phân tích MWG; mã bất động sản có tồn kho là dự án, số ngày tồn kho ít ý
  nghĩa nên với ngành Bất động sản không bật cờ (vẫn hiện số).

## 3. Dự phòng giảm giá tồn kho đi vào lợi nhuận
- Mỗi quý: thay đổi số dư dự phòng giảm giá (cuối quý trừ cuối quý trước, giá trị tuyệt đối) so với LNTT của quý.
- Cờ "Hoàn nhập dự phòng tồn kho lớn" khi số dư giảm từ **20% LNTT** (LNTT dương); cờ "Trích thêm dự phòng tồn kho lớn" khi số dư tăng từ
  **20% LNTT** (hàng đang mất giá). LNTT không dương: ghi số tiền, không tỷ lệ.
- Luôn ghi kèm: số dư giảm có thể do hoàn nhập (làm tăng lợi nhuận) hoặc do hàng đã bán, đã hủy (dự phòng được dùng); nguồn công khai không
  tách được, cần xem thuyết minh.

## Thứ tự
1 → 2 → 3, mỗi phần một nhánh, TDD, verify rồi merge.

## Đã làm (22/11/2026)
- Phần 1: dòng `inventory_gross`, `inventory_provision` (bộ dòng phiên bản 6); `inventory_view`; mục Tồn kho trên hồ sơ mã. Đồng bộ lại toàn
  bộ 41 mã ngay sau khi merge: cả 41 mã có giá gốc và dự phòng.
- Phần 2: `inventory_pace`; dòng số ngày tồn kho trong mục Tồn kho; cột "Tồn kho tăng nhanh hơn giá vốn" trên Bảng dấu hiệu. Chạy thử 22/11:
  12/41 mã bật cờ, trong đó có mã tồn kho rất nhỏ (cảng, vận tải 10–20 ngày): cần chủ sở hữu quyết ngưỡng trọng yếu.
- Phần 3: `inventory_provision_flow`; dòng trong mục Tồn kho, nhãn "Hoàn nhập dự phòng tồn kho lớn" hoặc "Trích thêm dự phòng tồn kho lớn".
- Ngưỡng trọng yếu (chủ sở hữu duyệt 22/11/2026): cờ "Tồn kho tăng nhanh hơn giá vốn" chỉ bật khi tồn kho thuần từ **10% tổng tài sản**;
  dưới ngưỡng vẫn hiện số và ghi "không ghi cờ"; thiếu tổng tài sản thì không đọc được (không bật cờ). Chạy thử: 12 còn 8 mã.
