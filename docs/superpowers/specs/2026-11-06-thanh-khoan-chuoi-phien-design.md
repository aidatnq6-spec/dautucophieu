# Thanh khoản so với nền, chuỗi phiên và biên độ trong phiên (06/11/2026)

Chủ sở hữu đồng ý làm 1 + 2 (06/11/2026), sau khi đọc một bài phân tích phiên chỉ nói "dòng tiền thận trọng", "tiến gần 1.750 nhưng không
giữ được" mà không có số. Thêm vào ảnh chụp phiên (`data/brief/<phiên>.json`), trang Bản tin và tin Telegram 15:30 những con số kiểm chứng
được. Không nhận định, không kết luận mua bán, không gửi gì cho AI.

## VN-Index trong phiên (mục `index_session`)
- Nguồn: kho giá ngày của VN-Index (`data/prices/VNINDEX`, vnstock nguồn KBS, `market-sync --index` mỗi lượt). Đã đối chiếu 06/11/2026:
  khối lượng là khớp lệnh (khớp bảng giá cả sàn, 672–673 triệu cp phiên 05/11); cao/thấp khớp bộ đệm biểu đồ 48/49 phiên.
- **Biên độ**: cao, thấp, đóng cửa; đóng cửa cách đỉnh và cách đáy bao nhiêu điểm. KBS tính cả mức tham chiếu lúc mở cửa vào cao/thấp, nên
  trang ghi chú "cao/thấp theo KBS, có thể gồm mức tham chiếu đầu phiên".
- **Chuỗi phiên**: số phiên liên tiếp cùng chiều tính đến phiên này (so giá đóng cửa từng phiên theo lịch giao dịch), và mức thay đổi cộng dồn
  so với giá đóng cửa trước chuỗi (điểm và %). Phiên đứng giá thì ghi "đứng giá". Thiếu nến một phiên trong chuỗi hoặc hết dữ liệu thì ghi
  "ít nhất n phiên" và không ghi mức cộng dồn.
- **Khối lượng khớp lệnh**: so với phiên trước (%) và với trung bình 20 phiên trước đó (lần). Thiếu nến phiên nào trong 20 phiên thì ghi
  "thiếu n phiên", không tính trung bình. Có sẵn trước bản tin 15:30.

## Giá trị HOSE công bố (mục `hose_liquidity`)
- Nguồn: API thống kê của HOSE (như mục HOSE hiện có; robots.txt của api.hsx.vn trả 404). Giá trị gồm cả giao dịch thỏa thuận.
- Phiên này so với phiên trước (%) và với trung bình 20 phiên trước đó (lần). Trung bình = tổng HOSE trả cho khoảng 20 phiên ÷ 20; đã kiểm
  tra tổng của khoảng ngày đúng bằng cộng từng ngày (04–06/11/2026: 52.949,47 tỷ). Thêm 2 lần gọi mỗi lượt.
- HOSE thường công bố muộn: chưa có thì ghi "HOSE chưa công bố" (tin 15:30 thường chưa có; trang có sau lượt 20:00).

## Ngành
- "x/y ngành tăng" đếm từ mức tăng trung bình theo ngành của bảng giá cả sàn đã có.

## Lan tỏa (thay cho đóng góp điểm theo mã, 06/11/2026)
- Không có nguồn công khai hợp lệ cho điểm đóng góp từng mã: vnstock có `Insights().sentiment.contribution` nhưng không thuộc gói Cộng đồng;
  Vietstock cần token và reCAPTCHA; SSI iBoard, CafeF không công bố API cho mục này; tự tính cần free-float và giới hạn tỷ trọng chưa có
  nguồn. Chủ sở hữu chọn thay bằng số đo lan tỏa.
- Trung bình cộng và trung vị mức thay đổi của mọi mã HOSE có giao dịch trong phiên (bảng giá cả sàn, chỉ cổ phiếu), cùng trọng số, đặt cạnh
  mức thay đổi của VN-Index (theo vốn hóa). Ngược dấu thì ghi "ngược chiều"; không nhận định gì thêm. Có trên trang và tin 15:30.

## Bảng kiểm "Thị trường phục hồi" (06/11/2026)
- Bốn điều kiện, mỗi điều kiện kèm số: (1) VN-Index đóng cửa trên MA20 (trung bình giá đóng cửa 20 phiên gồm phiên này, kho giá);
  (2) khối lượng khớp lệnh ≥ trung bình 20 phiên trước; (3) số mã tăng > số mã giảm; (4) trung bình cộng các mã (Lan tỏa) > 0.
- Hiện "x/4 điều kiện đạt"; điều kiện thiếu số (ví dụ ảnh chụp cũ, thiếu nến) ghi "chưa có số" và không tính là đạt hay chưa. Bằng nhau
  thì chưa đạt, trừ khối lượng (≥ như nhãn).
- Trên trang Bản tin và một dòng trong tin 15:30. Là phép đếm trên số liệu, không phải khuyến nghị mua bán.

## Ngoài phạm vi
Đóng góp điểm theo mã (chưa có nguồn công khai hợp lệ, xem trên); VN30 (kho giá chưa có nến ngày VN30).
