# Đáy nhịp tuần và kênh tăng (07/11/2026)

Từ ảnh "XAUUSD W · kênh tăng từ đáy 09/2022" chủ sở hữu gửi: vùng đáy theo MACD tuần (B1) và các kênh nối đáy (B2). Chủ sở hữu chọn
(07/11/2026): **thang thường** như ảnh; áp dụng cho **mọi dòng trên bảng Xu hướng** (vàng qua PAXG); điểm 0 = **đáy thấp nhất trong N năm**
(3/5/10, mặc định 5); **không** báo Telegram. Chỉ dữ liệu công khai, không đọc danh mục, không gọi AI. Không phải khuyến nghị.

## Luật (`market/channels.py`)
- Nến tuần (theo thứ Hai) từ nến ngày: cao nhất, thấp nhất, đóng cửa cuối tuần. Cổ phiếu và chỉ số dùng nến OHLC của biểu đồ bảng giá
  (đáy theo râu nến như ảnh); các dòng Vĩ mô chỉ có giá đóng cửa nên đáy là đóng cửa thấp nhất, trang ghi rõ. Tuần đang chạy được hiện
  giá nhưng không dùng.
- MACD 12/26/9 trên giá đóng cửa tuần. **Vùng đáy**: từ tuần MACD cắt xuống Signal tới tuần cắt lên; đáy = mức thấp nhất trong đó; vùng
  vẽ từ 2 tuần trước đáy (không trước tuần cắt xuống). Đáy chỉ được biết từ tuần cắt lên. Lần cắt lên đầu tiên không có lần cắt xuống trước
  đó thì không phải vùng đáy.
- **Điểm 0** = đáy vùng thấp nhất trong N năm tính tới tuần đã kết thúc gần nhất. Điểm 2 = vùng đáy kế tiếp; điểm 1 = đỉnh cao nhất giữa.
- **Kênh** = các cạnh của bao lồi dưới nối các vùng đáy từ điểm 0. Mỗi vùng nối ở điểm thoải nhất nhìn từ điểm nối trước (có thể không phải
  đáy thấp nhất của vùng, như dấu × khác ○ trong ảnh). Điểm nối nằm trên hoặc ngay trên đường tới điểm sau thì bị bỏ, nên đáy thẳng hàng chỉ
  cho một kênh, và các kênh sau luôn dốc hơn: basic 0-2 → tăng tốc 1, 2… → final.
- **Cạnh trên** song song qua đỉnh cao nhất giữa hai điểm nối; **gấp đôi** = cạnh dưới + 2 × độ rộng.
- Giá trị cạnh dưới, cạnh trên, gấp đôi **chỉ tại tuần đã kết thúc gần nhất**; không kéo kênh ra tương lai.
- **Trạng thái**: đóng cửa tuần gần nhất dưới cạnh dưới / trong kênh / trên cạnh trên của kênh final hiện tại, kể từ tuần nào.
- **Phá kênh**: tuần đầu tiên đóng cửa dưới kênh final đang có hiệu lực tuần đó, kênh dựng chỉ từ các đáy đã xác nhận tới tuần đó.
  Liệt kê mọi lần.
- Cần ít nhất 35 tuần (MACD tuần) và 2 vùng đáy từ điểm 0; thiếu thì ghi lý do.
- Điểm 0 do tác giả ảnh chọn bằng mắt; luật N năm có thể cho điểm khác ảnh. Kênh tính lại theo bao lồi cũng có thể khác nét vẽ tay.

## Vàng
Coinbase chỉ có PAXG từ 08/05/2025 (khoảng 78 tuần): hiện được 1 vùng đáy, trang ghi "Cần ít nhất 2 đáy vùng từ điểm 0 để có kênh". Đã tìm
nguồn XAUUSD công khai (07/11/2026): Stooq chặn mọi bot trong robots.txt và bắt chạy JavaScript; freegoldapi.com lấy giá ngày từ Yahoo
(hợp đồng tương lai, không ghi giấy phép); metals-api, API Ninjas, metalcharts cần khóa hoặc trả phí. Chưa có nguồn hợp lệ, chưa tích hợp.

## API và giao diện
- `GET /internal/trend/channels`: các dòng bảng Xu hướng. `GET /internal/trend/channels/{mã}/{N năm}`: N 1–20 (ngoài khoảng 422); mã
  không có trên bảng trả 404.
- Trang Xu hướng, dưới bảng MACD/RSI: chọn mã, nút 3/5/10 năm; dòng trạng thái kênh final; điểm 0-1-2; bảng các kênh; bảng vùng đáy (đánh
  dấu điểm 0, so đáy trước); các lần phá kênh. Chú thích ghi đủ luật trên.

## Vẽ lên biểu đồ nến (07/11/2026)
- Chỉ ở khung **Tuần** của "Bảng giá và biểu đồ": nhóm nút "Kênh tuần: Tắt · 3 năm · 5 năm · 10 năm", **mặc định Tắt** để biểu đồ như cũ.
- Lớp riêng, chỉ đọc, không lẫn với hình vẽ tay (màu cam, lưu trong kho cá nhân): không kéo, không xóa, không lưu.
- Xanh: cạnh dưới và cạnh trên của từng kênh từ điểm nối đầu tới tuần đã kết thúc gần nhất (basic nét liền, tăng tốc nét đứt, final đậm); gấp
  đôi (chấm) chỉ cho kênh final. Nâu: mỗi vùng đáy là một vạch ngang tại mức đáy, từ đầu vùng tới tuần cắt lên. Nhãn d1… dưới nến đáy (điểm 0 ghi
  "· 0"); mũi tên đỏ "phá kênh" trên tuần phá kênh. Các đường không tham gia tự co giãn trục giá.
- Thiếu điều kiện thì ghi lý do cạnh nút ("Chưa có kênh: …"); không vẽ gì ra sau tuần đã kết thúc gần nhất.

## Ngoài phạm vi
Nguồn XAUUSD, cảnh báo Telegram (chủ sở hữu không làm).

## Khung ngày và 1 giờ (07/11/2026)
Chủ sở hữu hỏi áp dụng cho khung ngày và 1 giờ: cùng luật trên, với các điểm khác sau.
- **Khung**: tuần (gộp từ nến ngày), ngày, 1 giờ (nến như biểu đồ; khóa giờ là giờ Hà Nội). Khung tháng không có.
- **Điểm 0 trong**: tuần 3/5/10 năm (mặc định 5), ngày 6/12/24 tháng (mặc định 12), 1 giờ 2/4/8 tuần (mặc định 4; nguồn giữ khoảng 1 năm nến giờ).
- **Đo theo số nến, không theo ngày lịch** (mọi khung, kể cả tuần): biểu đồ vẽ đường thẳng theo khoảng cách nến, nên nghỉ cuối tuần, ban đêm,
  nghỉ trưa không làm cong đường. Khung tuần gần như không đổi so với bản tính theo ngày lịch (HPG: cạnh dưới 20,93 thay 20,95).
- **Nến đang chạy không dùng**: tuần này; hôm nay theo giờ Hà Nội hoặc theo UTC (nến ngày Coinbase đóng lúc 07:00 giờ Hà Nội); giờ này.
- **Nguồn**: cổ phiếu, chỉ số có nến ngày 10 năm và nến giờ 1 năm (Vnstock); Vĩ mô chỉ có giá đóng cửa, nến giờ chỉ có BTC và vàng (PAXG),
  dòng khác ghi "Nguồn chỉ có giá ngày".
- Khi giá đang giảm, đáy thấp nhất trong khoảng tìm nằm gần hiện tại nên chưa đủ 2 vùng đáy từ điểm 0: trang ghi "Cần ít nhất 2 đáy vùng
  từ điểm 0 để có kênh"; không có kênh tăng để vẽ là đúng luật.
- API: `GET /internal/trend/channels/{mã}/{1W|1D|1H}/{n}` (n tối đa 20 năm, 60 tháng, 52 tuần; ngoài khoảng hoặc khung khác trả 422) thay
  cho đường dẫn chỉ có tuần.
- Giao diện: khối "Đáy nhịp và kênh tăng" có thêm chọn khung; trên biểu đồ nến, nhóm nút "Kênh" hiện ở khung Tuần, Ngày, 1 giờ, mỗi khung
  bật tắt riêng, mặc định Tắt.
