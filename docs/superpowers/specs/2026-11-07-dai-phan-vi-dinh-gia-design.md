# Dải phân vị P/B, P/E (07/11/2026)

Bước 2 của nhóm "dải phân vị định giá", dựng trên [chuỗi định giá theo tuần](2026-11-07-chuoi-dinh-gia-tuan-design.md). Chủ sở hữu chọn
**giữ cả hai** (07/11/2026): biểu đồ theo tháng với trung vị ± độ lệch chuẩn vẫn như cũ; dải phân vị đặt ngay bên dưới, ở mọi chỗ có biểu
đồ đó (chi tiết mã trên trang Định giá và hồ sơ mã). Chỉ mã cổ phiếu, không có cho VN-Index, VN30. Chỉ dữ liệu công khai, không gọi AI.

## Tính toán (`valuation/bands.py`)
- Ba khung: 3 năm, 5 năm, toàn bộ chuỗi. Khung tính lùi từ tuần mới nhất. Chuỗi không với tới đầu khung (lệch quá 7 ngày) thì không
  vẽ khung đó và ghi "Chuỗi chỉ có từ MM/YYYY, chưa đủ N năm". Gói Cộng đồng chỉ có báo cáo từ 2018, nên không có khung 7 năm.
- Khung cần ít nhất 52 tuần có số; thiếu thì ghi "Chỉ có n tuần có số, cần ít nhất 52". Tuần không có số (lỗ, vốn âm) được đếm
  riêng, không lấp.
- Mỗi khung: P10, P20, P50, P70, P80, P95 (nội suy tuyến tính giữa hai giá trị gần nhất, cách "type 7" thông dụng); thấp nhất, cao nhất;
  trung bình, độ lệch chuẩn tổng thể; z = (hôm nay − TB) / độ lệch chuẩn; skew Fisher–Pearson; hạng hôm nay = % số tuần ≤ hôm nay; số tuần
  theo từng cơ sở ("4 quý", "quý", "năm"). Độ lệch chuẩn bằng 0 thì không có z, skew. Tuần mới nhất không có số thì không có hạng, z.
- API: `GET /internal/fairvalue/weekly/{mã}` trả thêm `bands.pe`, `bands.pb`.

## Giao diện (`percentile-bands.tsx`)
- Tiêu đề "{mã} · P/B hôm nay x — đứng ở đâu trên 3 khung", nút chuyển P/B và P/E (mặc định P/B).
- Mỗi khung một thanh: ≤ P10 xanh đậm, P10–P20 xanh, P20–P50 xanh nhạt, P50–P70 xám, P70–P95 hồng; vạch đậm là hôm nay. Khung không vẽ
  được thì ghi lý do ngay trên hàng đó.
- Bảng: khung, từ, số tuần, hạng hôm nay, z, các phân vị, TB, skew.
- Dòng dưới: "x/n khung đang ≤ P20 · y/n khung ≤ P10"; khi có khung skew > 1 thì nhắc đọc theo phân vị; số tuần theo từng cơ sở và số quý
  thiếu ở nguồn.
- Không kết luận mua bán.

## Ngoài phạm vi
Giá giả định (bước 3), mốc giá quá khứ (bước 4).
