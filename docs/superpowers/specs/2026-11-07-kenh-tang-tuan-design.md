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

## Ngoài phạm vi
Vẽ kênh lên biểu đồ nến (PR sau), nguồn XAUUSD, cảnh báo Telegram (chủ sở hữu không làm).
