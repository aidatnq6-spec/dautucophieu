# Chỉ báo vĩ mô (trang "Vĩ mô")

Theo bảng Leading Indicator của chủ sở hữu (25/10/2026). Danh mục và quy tắc đánh giá nằm trong `config\macro-indicators.json`; số liệu lưu ở `data\macro\<chỉ số>.json` (có trong bản sao lưu).

## Nguồn (kiểm tra 25/10/2026)

| Chỉ số | Nguồn | Cách lấy |
|---|---|---|
| Giá dầu WTI, CPI Mỹ (so cùng kỳ, tính từ CPIAUCSL), Fed qua đêm (EFFR), lợi suất 10 năm Mỹ | FRED, tệp CSV công khai | Tự động mỗi lần lịch chạy (`cli macro-sync`) |
| Chỉ số USD rộng (DTWEXBGS) | FRED | Tự động; **thay cho DXY** — DXY của ICE là dữ liệu có bản quyền, chỉ số rộng cùng chiều nhưng khác giá trị |
| USD/VND bán – Vietcombank | XML tỷ giá công khai của Vietcombank | Tự động |
| USD/VND bán – tự do và NHNN (SBV), lãi suất tiền gửi 12 tháng cột "NHTM Khác" | Trang công khai của Topi (`online.topi.vn/market/ty-gia-usd-vnd`, `/lai-suat`); robots.txt cho phép, điều khoản không cấm đọc; dữ liệu do đối tác của Topi cung cấp | Tự động, đọc từ nội dung trang; ghi theo ngày tải (trang không ghi ngày công bố). Topi đổi giao diện → báo lỗi nguồn, vẫn cho nhập tay |
| Khối ngoại mua/bán ròng trên HOSE, giá trị giao dịch toàn sàn HOSE (gồm thỏa thuận) | Dịch vụ thống kê của chính HOSE phía sau hsx.vn (`api.hsx.vn/mk/api/v1/market/foreign-trading-value-report`, kiểm tra 26/10/2026); robots.txt của hsx.vn cho phép; không có tài liệu chính thức | Tự động, 7 ngày gần nhất mỗi lần chạy (ngày nghỉ trả rỗng); đơn vị triệu đồng → tỷ đồng. Chỉ tính sàn HOSE, nên khác số toàn thị trường hoặc chỉ khớp lệnh. HOSE đổi dịch vụ → báo lỗi nguồn, vẫn cho nhập tay |
| M2, PMI Mỹ và Việt Nam, lợi suất 10 năm Việt Nam, liên ngân hàng qua đêm | Không có nguồn miễn phí hợp lệ (kiểm tra lại 26/10/2026): website NHNN chặn truy cập tự động ("Request Rejected"); API chính thức của IMF không có M2 Việt Nam; HNX/VBMA không có dữ liệu lợi suất đọc được; PMI thuộc ISM/S&P Global (S&P trả 403); Investing.com, TradingEconomics, TradingView chặn; Vnstock Community không cấp quyền | Chủ sở hữu nhập tay trên trang, kèm ngày và link nguồn |

Lãi suất liên ngân hàng có trên website NHNN nhưng chỉ đọc được bằng cách phân tích trang HTML của NHNN; chưa làm. Biểu đồ khối ngoại và tự doanh 10 phiên cần nguồn trả phí.

## Xu hướng và đánh giá

Xu hướng so giá trị mới nhất với kỳ trước (Tăng / Giảm / Đi ngang). Đánh giá theo `rule`:

- `up`: tăng là Xấu, giảm là Tốt (DXY, dầu, CPI, tỷ giá, lãi suất, lợi suất).
- `down`: giảm là Xấu, tăng là Tốt (M2, giá trị giao dịch).
- `sign`: âm là Xấu (khối ngoại bán ròng), dương là Tốt.
- `pmi`: Tốt khi trên 50 và không giảm; còn lại Xấu.

Đi ngang là Trung tính. Số liệu quá `max_age_days` được ghi "số liệu cũ". Đây là bảng theo dõi, không dùng làm bằng chứng phân tích (đó là chuỗi có phiên bản trong `market/macro.py`) và không phải khuyến nghị.
