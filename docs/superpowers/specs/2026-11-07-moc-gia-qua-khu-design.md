# Mốc giá quá khứ (07/11/2026)

Bước 4, cuối cùng, của nhóm "dải phân vị định giá": bản rút gọn của bảng "vùng mua giả định" mà chủ sở hữu gửi kèm. Giữ các mốc giá có thật trong
lịch sử của mã. **Bỏ** dự phóng thời gian (kiểu "26 tháng → 11/2027"), xác suất thắng 12 tháng, bảng kiểm điều kiện và lịch sử gộp nhiều mã.
Chỉ dữ liệu công khai, không đọc danh mục, không gọi AI.

## Tính toán (`valuation/milestones.py`)
- Giá đóng cửa cuối mỗi tuần (giá điều chỉnh, đồng); giá 0 bị bỏ.
- Tách nhịp (zigzag) theo **ngưỡng do chủ sở hữu chọn: 10, 15 hoặc 20%** (API nhận 5–30, mặc định trên trang là 15). Một đỉnh hay đáy chỉ được
  xác nhận khi giá đã đi ngược đủ ngưỡng từ đó; cực trị của nhịp đang chạy chưa được xác nhận.
- Đỉnh: đỉnh xác nhận gần nhất khi nhịp đang giảm; mức cao nhất của nhịp khi đang tăng; giá cao nhất nếu chưa có nhịp nào.
- Chỉ liệt kê mốc **từ tuần đầu có P/B** (như khung "Toàn bộ" của dải phân vị). P/B, P/E theo số liệu hôm nay cho một mức giá từ trước khi
  có báo cáo là vô nghĩa (HPG 2008: P/B 0,03). Đáy cũ hơn thấp hơn giá hôm nay được đếm, không liệt kê. Không có chuỗi P/B thì dùng toàn bộ
  lịch sử giá.
- Các dòng, cao xuống thấp: giá hiện tại; mọi đáy đã xác nhận thấp hơn giá hôm nay; đáy của nhịp đang giảm nếu thấp hơn giá hôm nay (ghi
  "chưa xác nhận"); giá tại P/B thấp nhất (P/B thấp nhất theo tuần × vốn chủ trên mỗi cổ phiếu hôm nay).
- Mỗi dòng: % giảm từ đỉnh; số đợt chỉnh đã hoàn tất (đỉnh → đáy xác nhận, trong cùng khoảng) sâu hơn mức đó, ghi k/n; P/B và P/E tại giá đó
  theo mẫu số tuần mới nhất (không có khi thiếu hoặc không dương); chênh so với giá tại P/B thấp nhất.

## API và giao diện
- `GET /internal/fairvalue/milestones/{mã}/{ngưỡng %}`: chỉ mã trong danh sách theo dõi; ngưỡng ngoài 5–30 trả 422.
- Khối "Mốc giá quá khứ" dưới dải phân vị, ở mọi chỗ có biểu đồ P/E, P/B của mã (không có cho chỉ số). Tiêu đề ghi giá, % giảm từ đỉnh và
  tháng của đỉnh; nút 10% · 15% · 20%; bảng các mốc; chú thích ghi quy tắc tách nhịp, khoảng liệt kê, số đáy cũ bỏ qua, cách tính P/B tại
  mốc, và "không dự phóng bao lâu nữa giá về, không tính xác suất".
