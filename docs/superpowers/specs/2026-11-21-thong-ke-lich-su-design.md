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

## Lịch sử vĩ mô dài (nguồn đã kiểm 21/11/2026)
- **World Bank, Global Economic Monitor** (API mở, không khóa; robots.txt 404): theo tháng từ 01/2010, chậm khoảng 4 tháng —
  CPI Việt Nam % so cùng kỳ, sản xuất công nghiệp (điều chỉnh mùa vụ), tỷ giá USD/VND bình quân tháng, xuất khẩu hàng hóa (điều chỉnh
  mùa vụ). Lưu `wb_vn_*` trong kho vĩ mô.
- **FRED DGS10**: lợi suất Mỹ 10 năm từ 1962 (`us10y_long`), ghép với chuỗi gần đây (trùng khớp trên các ngày chung).
- `macro-sync` đọc các chuỗi này **mỗi tuần một lần**; lỗi thì lượt sau đọc lại. Đọc lỗi mà còn số trong hạn (tháng: 200 ngày,
  DGS10: 10 ngày) là "trễ".
- **Lãi suất trong nước: không có nguồn lịch sử công khai** (NHNN trả 403, IMF trả 502 lúc kiểm). Không lưu, không thay thế; trang ghi rõ.

## Trạng thái vĩ mô: hai điều kiện (2×2)
- 8 điều kiện có/không: lạm phát (CPI) tăng so với 3 tháng trước; tỷ giá USD/VND tăng hơn X% trong 3 tháng (X: 0,5 / 1 / 2 / 3%);
  sản xuất công nghiệp tăng (so cùng kỳ) nhanh hơn trung bình 12 tháng; xuất khẩu 3 tháng tăng so cùng kỳ; giá dầu, USD rộng, lợi suất
  Mỹ 10 năm tăng trong 3 tháng; P/E VN-Index trên trung vị 5 năm.
- **Biết từ khi nào:** CPI, sản xuất công nghiệp, xuất khẩu tháng M từ ngày 10 tháng sau (lịch công bố của Tổng cục Thống kê); tỷ giá
  bình quân tháng từ ngày 1 tháng sau; số ngày của FRED từ hôm sau; P/E cùng ngày. Một phiên lấy trạng thái mới nhất đã biết, nếu
  không cũ quá 130 ngày (số tháng, vì World Bank chậm khoảng 4 tháng) hoặc 10 ngày (số ngày).
- Chủ sở hữu chọn A và B; bảng 4 ô (A có/không × B có/không) và "Mọi lúc"; ô của hôm nay tô đậm, chỉ khi phiên mới nhất biết đủ cả
  hai. Bảng "Vĩ mô hôm nay" ghi từng điều kiện, số liệu tháng hay ngày nào, có từ khi nào. Biểu đồ VN-Index theo tuần, tô các giai
  đoạn cả A và B cùng đúng.