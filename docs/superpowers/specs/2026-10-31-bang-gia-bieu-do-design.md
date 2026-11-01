# Bảng giá và biểu đồ trên Xu hướng (31/10/2026)

Chủ sở hữu muốn bảng giá hiện tại của chỉ số và mã, kèm biểu đồ nến, tương tự TradingView/FireAnt. Bước 1 (đã đồng ý): danh sách giá
trong phiên bên phải, bấm một dòng mở biểu đồ nến ngày hoặc 1 giờ có MACD và RSI. Công cụ vẽ để bước sau.

## Nguồn (Vnstock gói Cộng đồng, đã kiểm tra 31/10/2026)
- Cổ phiếu: `Trading(source="VCI").price_board(...)`, cả danh sách theo dõi trong một lượt gọi: giá khớp, tham chiếu, trần, sàn, cao, thấp,
  khối lượng (đồng; hiện bằng nghìn đồng như bảng giá sàn).
- Chỉ số: bảng giá không trả VNINDEX/VN30; dùng nến 1 phút 7 ngày gần nhất: nến cuối là mức hiện tại, nến cuối của phiên trước là tham chiếu.
- Nến: `ohlcv(interval="1D")` 10 năm (gói Cộng đồng trả từ khoảng 2018), `ohlcv(interval="1H")` 1 năm (nguồn trả khoảng 1.000 nến).

## Quy tắc
- Mã chưa khớp trong phiên: không có giá, không lấy tham chiếu thay giá.
- Bảng giá đệm trong bộ nhớ 15 giây trong phiên (9:00–15:00, thứ 2–6, giờ Hà Nội), 5 phút ngoài phiên; trình duyệt hỏi lại 20 giây/5 phút
  và dừng khi tab bị ẩn. Giới hạn nguồn 60 lượt/phút.
- Nến lưu `data/chart/<MÃ>-<khung>.json`: ngày làm mới 10 phút trong phiên / 6 giờ ngoài phiên; 1 giờ là 2 phút / 1 giờ. Nguồn lỗi thì hiện
  bản đã lưu kèm ngày đọc; không có bản lưu thì ghi lý do. Dòng nến sai (cao < mở/đóng…) bị bỏ, không sửa.
- Chỉ mã trong danh sách theo dõi và VNINDEX, VN30.
- MACD (12, 26, 9) và RSI (14) tính như TradingView (cùng hàm của bảng Xu hướng).
- Màu theo quy ước sàn: tím trần, xanh lơ sàn, vàng tham chiếu, xanh lá tăng, đỏ giảm.
- Biểu đồ dùng Lightweight Charts 5.2.1 (TradingView, Apache-2.0); giữ logo ghi công mặc định của thư viện.
- Proxy web không chuyển chuỗi truy vấn, nên khung nằm trong đường dẫn: `/internal/trend/chart/<MÃ>/<1D|1H>`.

## Bổ sung: Vĩ mô trên bảng giá (31/10/2026)
- Nhóm "Vĩ mô" giữa Chỉ số và Cổ phiếu: DXY, US10Y, VN10Y, Vàng, Dầu WTI, Bitcoin.
- Bitcoin và Vàng (PAXG) đọc tức thời từ thống kê công khai của Coinbase (`/products/<cặp>/stats`), so với giá 24 giờ trước; nguồn lỗi thì
  dùng giá đóng cửa đã lưu. Các biến khác: giá đóng cửa gần nhất đã lưu (trend-sources; VN10Y từ kho vĩ mô) so với phiên trước, ghi ngày.
- Một điểm duy nhất thì không có thay đổi; không có chuỗi thì "Chưa có số". Lợi suất: thay đổi bằng điểm phần trăm.
- Biểu đồ của biến vĩ mô là đường giá đóng cửa (nguồn không có mở/cao/thấp) kèm MACD/RSI; khung 1 giờ chỉ cho Bitcoin và Vàng.

## Bổ sung: giá chạy ngoài giờ và nến đang mở (31/10/2026)
- Trình duyệt hỏi bảng giá mỗi 20 giây ở mọi giờ (dừng khi tab ẩn). Máy chủ giữ cổ phiếu/chỉ số 15 giây trong phiên, 5 phút ngoài phiên;
  dòng Vĩ mô có bộ đệm riêng 15 giây ở mọi giờ, nên Bitcoin và vàng chạy cả cuối tuần (Coinbase: 2 lượt mỗi 15 giây).
- Nến đang mở trên biểu đồ (cùng ngày/cùng giờ với giá mới) nhận giá của bảng giá: giá đóng cửa mới, cao/thấp nới theo giá đó, giá mở giữ nguyên.
  Khi giá thuộc nến mới chưa có trong dữ liệu, không tự tạo nến (không đoán giá mở/cao/thấp); biểu đồ đọc lại nguồn, tối đa mỗi 2 phút.
- MACD và RSI cập nhật khi đọc lại nguồn, không tính lại theo từng giá.

## Bổ sung: công cụ vẽ trên biểu đồ (01/11/2026)
Chủ sở hữu chọn "làm luôn", không qua hỏi đáp; các lựa chọn dưới đây là quyết định của người làm, chủ sở hữu duyệt khi xem PR.
- Thanh công cụ trên biểu đồ: **Con trỏ** (mặc định, không vẽ), **Đường ngang** (một lần bấm), **Đường xu hướng** (bấm hai điểm),
  **Xóa hết** cho mã đang xem. Esc hoặc bấm lại công cụ thì hủy điểm đầu đang chờ.
- Chỉ vẽ trên khung giá (khung trên cùng), không vẽ trên MACD/RSI. Điểm bấm bám theo nến (thời gian của nến gần nhất), giá lấy đúng
  vị trí con trỏ trên trục giá, làm tròn 2 chữ số. Không bám tự động vào giá mở/cao/thấp/đóng.
- Đường ngang là một mức giá: hiện ở cả hai khung (Ngày và 1 giờ), có nhãn trên trục giá. Đường xu hướng nối hai điểm (thời gian, giá)
  và chỉ hiện ở khung đã vẽ, vì thời gian nến ngày và nến giờ khác nhau; không kéo dài quá hai điểm.
- Danh sách hình vẽ dưới biểu đồ, mỗi dòng có Xóa (sửa = xóa rồi vẽ lại). Mã vĩ mô (đường giá đóng cửa) cũng vẽ được.
- Lưu ở kho cá nhân (`settings/chart_drawings`), như Cảnh báo giá: có phiên bản chống ghi đè, tối đa 200 hình. Chỉ mã trong danh sách
  theo dõi, VNINDEX, VN30 và các biến Vĩ mô của bảng giá. Hình vẽ không gửi đi đâu, không vào bản tin, không phải cảnh báo.
- Đây là công cụ ghi chú của chủ sở hữu; phần mềm không tự vẽ hỗ trợ/kháng cự hay đường xu hướng nào.
