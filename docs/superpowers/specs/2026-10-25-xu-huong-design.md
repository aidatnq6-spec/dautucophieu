# Thiết kế: trang "Xu hướng" (bảng MACD/RSI nhiều khung thời gian)

Ngày: 25/10/2026 · Trạng thái: chờ chủ sở hữu duyệt

## Mục đích

Chủ sở hữu đang duy trì bằng tay một bảng "Thống kê chỉ báo cổ phiếu hằng ngày sau khi giá đóng cửa 15:30", đọc số từ TradingView. Mỗi mã có trạng thái MACD và giá trị RSI ở 5 khung thời gian: tháng (M), tuần (W), ngày (D1), 4 giờ (H4), 1 giờ (H1). Bảng dùng để nhìn nhanh xu hướng của từng mã ở các khung khác nhau.

Mục tiêu: sau 15:30 mỗi phiên giao dịch, ứng dụng **tự tạo bảng này** trên một trang mới tên **"Xu hướng"**. Những ô **vừa đổi trạng thái so với phiên trước** được làm nổi bật. Chủ sở hữu không phải chép số từ TradingView nữa.

## Mục tiêu

- Trang "Xu hướng" trong ứng dụng, có trong menu, cùng giao diện với các trang hiện có.
- Danh sách mã cố định theo bảng của chủ sở hữu:
  - **Vĩ mô:** DXY, US10Y, VN10Y, Vàng, Dầu (USOIL), Bitcoin.
  - **Chỉ số:** VN-Index, VN30.
  - **Cổ phiếu:** MBB, CTG, ACB, SSI, HPG, KDH, MWG, FPT, PNJ.
- Mỗi mã, mỗi khung M, W, D1, H4, H1 có hai ô:
  - **MACD:** hiện `up` nếu đường MACD đang **nằm trên** đường tín hiệu, `down` nếu nằm dưới; kèm `>0` hoặc `<0` theo vị trí đường MACD so với mức 0. Ví dụ `up,>0`, `down,<0`. Ô up tô xanh, ô down tô đỏ.
  - **RSI:** giá trị số nguyên.
- Làm nổi bật các ô đã đổi trạng thái so với bảng của **phiên giao dịch trước**.
- Tự chạy theo lịch hiện có, từ khung 15:30 trở đi, không cần thao tác.

## Không làm

- Không có khung "Hành động" (chủ sở hữu đã bỏ).
- Không gửi Telegram; chỉ hiển thị trên trang.
- Không thêm khuyến nghị mua bán và không đưa bảng này vào bản tin.

## Điều không được xảy ra

- **Không dùng tài khoản TradingView** của chủ sở hữu (thông tin đăng nhập có trong ảnh chụp). Không đăng nhập, không đọc dữ liệu từ TradingView.
- Không bịa hoặc nội suy số cho ô thiếu dữ liệu. Ô thiếu hiện `—` kèm lý do.
- Không dùng nguồn có điều khoản hoặc kỹ thuật chặn truy cập tự động: Investing.com, TradingView, API ẩn.
- Không trình bày bảng như lời khuyên đầu tư.

## Ràng buộc và nguồn dữ liệu (đã kiểm tra thực tế ngày 25/10/2026)

| Nhóm | M · W · D1 | H4 · H1 | Nguồn |
|---|---|---|---|
| 9 cổ phiếu, VN-Index, VN30 | Có | Có: H1 khoảng 1 năm; H4 ghép từ H1 | Vnstock (đang dùng). Nến ngày đã lưu trong `data\prices`. Nến giờ lấy bằng `ohlcv(interval="1H")`. Nguồn không có khung 4H |
| Bitcoin | Có | Có | API giá công khai của Coinbase Exchange (`/products/BTC-USD/candles`), không cần tài khoản. Tối đa 300 nến mỗi lần gọi, nên phải gọi nhiều lần nối tiếp |
| Vàng | Gần đúng | Gần đúng | Không có giá vàng miễn phí hợp lệ. Dùng **PAXG-USD** trên Coinbase, một token bám giá vàng. Ghi rõ "gần đúng" trên trang |
| Dầu WTI, US10Y | Có | Không | FRED (`DCOILWTICO`, `DGS10`): mỗi ngày một giá đóng cửa |
| DXY | Gần đúng | Không | FRED `DTWEXBGS` (chỉ số USD rộng), thay cho DXY vốn là dữ liệu có bản quyền của ICE. Trang Vĩ mô cũng dùng cách này |
| VN10Y | Không | Không | Không có nguồn miễn phí hợp lệ. Dòng vẫn hiện, toàn bộ ô là `—` kèm lý do |

Ràng buộc khác: ứng dụng chạy trên máy chủ sở hữu và cập nhật theo lịch (không theo thời gian thực). Dữ liệu không rời máy. Tuân theo các quy ước đã có:
- Windows Task Scheduler gọi `run-after-close.ps1`.
- Dữ liệu nằm trong `data\`.
- Trang dùng API nội bộ qua proxy Next có ký HMAC.
- Có kiểm thử trước khi gộp mã (TDD) và chạy `verify.ps1`.

## Cách tính (đã thống nhất với chủ sở hữu)

- **MACD 12-26-9 và RSI 14** trên giá đóng cửa, theo cách TradingView mặc định:
  - EMA hệ số 2/(n+1);
  - đường tín hiệu là EMA 9 của MACD;
  - RSI làm trơn kiểu Wilder (RMA).
- **up/down** là trạng thái MACD so với đường tín hiệu tại nến gần nhất, không chỉ đúng nến vừa cắt. **>0/<0** là dấu của đường MACD.
- **Lưu ý cho chủ sở hữu:** số có thể lệch nhẹ so với TradingView vì nguồn giá khác nhau (giá đã điều chỉnh, cách cắt nến 4 giờ). Chiều lên/xuống thường trùng.

## Quyết định của người viết (chủ sở hữu có thể đổi)

1. **Nến chưa đóng được tính.** Tháng và tuần hiện tại được tính như TradingView đang hiển thị (nến đang hình thành).
2. **M và W được dựng từ nến ngày:** tháng theo lịch, tuần ISO từ thứ Hai. D1 là nến ngày.
3. **H4 = gộp nến 1 giờ theo khối 4 giờ neo lúc 07:00 giờ Việt Nam** (00:00 UTC, giống TradingView). Với cổ phiếu Việt Nam, mỗi phiên có 2 nến H4: buổi sáng, và từ 11:00 trở đi.
4. **Không đủ lịch sử** (dưới 35 nến cho MACD, dưới 15 nến cho RSI): ô hiện `—`, ghi "chưa đủ lịch sử".
5. **Màu RSI:** từ 70 trở lên là quá mua, từ 30 trở xuống là quá bán, còn lại trung tính. Lý do: màu RSI trong ảnh không theo một quy tắc cố định.
6. **"Đổi trạng thái":**
   - ô MACD đổi khi up/down hoặc >0/<0 khác bảng phiên trước;
   - ô RSI đổi khi chuyển vùng (quá bán / trung tính / quá mua).
   - Ô đổi được viền đậm và có ghi chú trạng thái cũ, ví dụ "trước: down,<0".
7. **Thời điểm chạy:** lập bảng ở mỗi lần lịch chạy vào ngày giao dịch, từ 15:30 trở đi. Lần chạy sau trong ngày ghi đè bảng của ngày hôm đó. "Phiên trước" là bảng đã lưu của phiên giao dịch liền trước theo lịch HOSE. Ngoài ngày giao dịch không lập bảng mới.
8. **Lưu trữ:**
   - mỗi phiên một tệp `data\trend\<ngày>.json`, giữ 90 ngày;
   - nến giờ lưu riêng trong `data\intraday\`, vì kho giá ngày hiện tại chỉ nhận một nến mỗi ngày;
   - chuỗi giá từ Coinbase và FRED lưu trong `data\trend-sources\`.
   - Các tệp này là dữ liệu tính lại được, nên không đưa vào bản sao lưu.
9. **Danh sách mã** nằm trong `config\trend-board.json` (nhóm, mã, nguồn, nhãn, ghi chú), để đổi mã không phải sửa code.
10. **Một nguồn lỗi không làm hỏng cả bảng:** dòng của nguồn đó hiện `—` với lý do "lỗi nguồn"; các dòng khác vẫn cập nhật. Đầu trang ghi thời điểm lập bảng và nguồn của từng nhóm.
11. **Bố cục:**
    - ba nhóm thẻ: Vĩ mô, Chỉ số, Cổ phiếu;
    - mỗi thẻ là bảng nhỏ với cột M/W/D1/H4/H1 và hai hàng MACD/RSI;
    - trên điện thoại các thẻ xếp một cột, không cuộn ngang;
    - có dòng ghi chú "không phải khuyến nghị".

12. **Nạp bù lịch sử một lần:**
    - `data\prices` hiện chỉ có khoảng 21 phiên cho mỗi mã, mà MACD tháng cần ít nhất 35 tháng. Vì vậy cần một lần nạp bù tối đa mà gói Vnstock Community cho phép (2.920 ngày, khoảng 8 năm) cho 9 cổ phiếu, VN-Index và VN30. VN30 được nạp theo điểm, giống VN-Index.
    - Sau đó, các lần nạp hằng ngày đã có sẽ giữ dữ liệu luôn mới.
    - Nến giờ được nạp lại khoảng 60 ngày gần nhất ở mỗi lần chạy. Lần đầu nạp tối đa mức nguồn cho phép.
13. **Đơn vị giá không ảnh hưởng chỉ báo:** chiều của MACD so với đường tín hiệu và so với mức 0, cũng như giá trị RSI, không đổi khi giá nhân với một hằng số. Vì vậy không cần quy đổi nến giờ (nghìn đồng) sang đồng; chỉ cần dùng cùng một đơn vị trong mỗi chuỗi.
14. **Phiên đầu tiên chưa có bảng phiên trước:** không ô nào được làm nổi bật, và đầu trang ghi "chưa có phiên trước để so sánh".

## Để người lập trình quyết định

- Tên module và đường dẫn API (ví dụ `GET /internal/trend`).
- Định dạng cụ thể của tệp lưu.
- Cách phân trang khi gọi Coinbase và FRED.
- Mức độ chia nhỏ việc tính toán.
- Thứ tự các bước trong `run-after-close.ps1`, miễn là bước lập bảng chạy sau bước nạp giá.

## Tiêu chí hoàn thành

- Sau lần chạy lịch 15:30 của một phiên, trang "Xu hướng" hiện đủ 17 thẻ (6 vĩ mô, 2 chỉ số, 9 cổ phiếu), mỗi thẻ có các ô MACD và RSI.
- Ô thiếu dữ liệu ghi rõ lý do.
- Phiên kế tiếp làm nổi bật đúng các ô đổi trạng thái.
- Có kiểm thử cho:
  - MACD và RSI trên chuỗi số biết trước, đối chiếu với giá trị tính tay;
  - cách dựng nến W, M, H4;
  - so sánh với phiên trước;
  - nguồn lỗi;
  - trang hiển thị và không cuộn ngang trên điện thoại.
- `verify.ps1` đạt.
