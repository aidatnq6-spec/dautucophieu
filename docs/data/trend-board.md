# Bảng "Xu hướng" (MACD/RSI theo khung thời gian)

Thiết kế: `docs/superpowers/specs/2026-10-25-xu-huong-design.md`. Danh sách mã: `config\trend-board.json`. Lệnh: `cli trend-run --data-dir data --calendar <lịch HOSE>`, do `run-after-close.ps1` gọi ở mỗi lần lịch chạy; chỉ lập bảng vào ngày giao dịch, từ 15:30 (giờ Việt Nam).

## Nguồn (kiểm tra 25/10/2026)

| Nhóm | M · W · D1 | H4 · H1 | Nguồn |
|---|---|---|---|
| 9 cổ phiếu, VN-Index, VN30 | Có | Có (H4 ghép từ H1) | Vnstock: nến ngày và nến 1 giờ |
| Bitcoin | Có | Có | Coinbase Exchange, nến công khai, không cần tài khoản |
| Vàng | Gần đúng | Gần đúng | PAXG-USD trên Coinbase (token bám giá vàng); không có giá vàng miễn phí hợp lệ |
| Dầu WTI, US10Y | Có | Không | FRED (`DCOILWTICO`, `DGS10`), một giá mỗi ngày |
| DXY | Gần đúng | Không | FRED `DTWEXBGS` (chỉ số USD rộng) thay DXY của ICE |
| VN10Y | Không | Không | Không có nguồn miễn phí hợp lệ |

Không dùng TradingView, Investing.com hay API ẩn, và không dùng tài khoản TradingView của chủ sở hữu.

## Cách tính

- MACD 12-26-9 và RSI 14 trên giá đóng cửa theo mặc định của TradingView (EMA hệ số 2/(n+1) khởi đầu bằng trung bình đơn; RSI làm trơn kiểu Wilder).
- `up`/`down`: MACD nằm trên/dưới đường tín hiệu ở nến gần nhất; `>0`/`<0`: dấu của đường MACD. Dưới 35 nến (MACD) hoặc 15 nến (RSI): "Chưa đủ lịch sử".
- W, M dựng từ nến ngày (tuần ISO, tháng theo lịch), tính cả nến đang chạy như TradingView. H4 gộp nến 1 giờ theo khối 4 giờ neo lúc 07:00 giờ Việt Nam (00:00 UTC).
- Dòng cổ phiếu/chỉ số Việt Nam cần nến của đúng phiên; thiếu thì ghi "Chưa có giá của phiên".
- RSI ≥ 70 quá mua, ≤ 30 quá bán. Ô đổi trạng thái so với bảng đã lưu trước đó (thường là phiên liền trước, trang ghi rõ ngày): MACD đổi `up/down` hoặc dấu; RSI đổi vùng.

Số có thể lệch nhẹ so với TradingView do nguồn giá (giá đã điều chỉnh, cách cắt nến); chiều lên/xuống thường trùng.

## Lưu trữ

- `data\trend-sources\<mã>-1d.json` (nến ngày), `data\intraday\<mã>-1h.json` (nến giờ): lần đầu nạp tối đa 2.920 ngày nến ngày (Coinbase cũng vậy) và 365 ngày nến giờ (Coinbase 60 ngày); các lần sau chỉ làm mới 60 ngày / 30 ngày gần nhất.
- `data\trend\<ngày>.json`: một bảng mỗi phiên, giữ 90 ngày. Tất cả tính lại được nên không đưa vào bản sao lưu.

Chỉ để theo dõi, không phải khuyến nghị.
