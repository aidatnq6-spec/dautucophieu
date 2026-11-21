# Thống kê lịch sử (21/11/2026)

Chủ sở hữu duyệt ngày 21/11/2026 (kaizen từ FireAnt Quant AI). Trang mới **Thống kê lịch sử** trong nhóm "Vĩ mô & thị trường".

## Nguyên tắc chung
- Mỗi phiên quá khứ được xếp theo trạng thái **đã biết ngay hôm đó** (không dùng số của tương lai), rồi xem VN-Index H phiên sau.
  H chọn được: 20, 60, 120, 250 phiên.
- Mỗi nhóm ghi: số mẫu, **số khoảng không chồng lấn** (các ngày cách nhau ít nhất H phiên, chọn từ sớm nhất), trung bình, trung vị,
  tỷ lệ tăng, và thống kê t **chỉ trên các khoảng không chồng lấn**. Các khoảng của những ngày liền nhau gối lên nhau, nên t trên mọi
  mẫu phóng đại bằng chứng.
- Cột "Độ tin cậy" nói thẳng: dưới 5 khoảng độc lập là "rất ít"; |t| dưới 2 là "chưa rõ khác 0".
- Chỉ mô tả quá khứ; không dự báo, không khuyến nghị. Kết quả giữ trong bộ nhớ 1 giờ.

## Mua ở mức P/E này thì sau đó thường ra sao?
- P/E VN-Index (VNDirect, từ 12/2017). Mỗi ngày xếp theo vị trí P/E so với 5 năm trước chính ngày đó (cần ít nhất 250 phiên), vào 5
  nhóm 20%: rẻ nhất, rẻ, giữa, đắt, đắt nhất. Khác FireAnt (chia theo toàn bộ lịch sử), để không dùng số của tương lai; vì vậy khoảng
  P/E của các nhóm gối lên nhau và được ghi kèm.
- Biểu đồ chấm (một ngày trong năm) P/E lúc đó so với VN-Index H phiên sau, đường xu hướng bình phương nhỏ nhất và R²; vạch dọc là P/E
  hôm nay. Nhóm của hôm nay tô đậm.

## Kiểm tra ngưỡng Đèn tín hiệu rủi ro vĩ mô
- Bốn đèn có lịch sử dài: giá dầu (từ 1986), USD rộng (từ 2006), lợi suất Mỹ 10 năm, P/E VN-Index. Mức của mỗi ngày tính bằng chính
  hàm của Đèn tín hiệu với ngưỡng đã duyệt; một phiên VN-Index lấy mức của ngày đo gần nhất trong 7 ngày trước nó.
- Bảng theo mức Bình thường / Cảnh báo / Nguy hiểm và "Mọi lúc"; mức hôm nay tô đậm; ghi "có từ …".
- Kết quả đầu tiên (21/11/2026, H = 60): đèn dầu đỏ đi kèm VN-Index **tăng** trung bình 11,2% (28 khoảng độc lập); đèn USD đỏ đi kèm
  −5,7% (11 khoảng). Chủ sở hữu tự quyết có chỉnh ngưỡng hay không.

## Chưa làm (nhánh sau)
- Lịch sử dài của lợi suất Mỹ 10 năm (hiện từ 04/2025) và các chuỗi vĩ mô Việt Nam theo tháng của World Bank (CPI, sản xuất công
  nghiệp, tỷ giá, xuất khẩu, từ 2010), để làm bảng trạng thái 2×2 như FireAnt.
- Lãi suất trong nước: chưa có nguồn lịch sử công khai (NHNN từ chối, IMF lỗi 502 lúc kiểm); thiếu thì ghi thiếu, không thay thế.
