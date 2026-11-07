# Định giá chỉ số VNINDEX và VN30

Ngày: 31/10/2026 · Trạng thái: chủ sở hữu đã chọn cách làm (P/E và P/B của chỉ số so với trung vị nhiều năm)

## Mục tiêu

Trang Định giá trả lời thêm câu hỏi "cả thị trường đang rẻ hay đắt?" cho VNINDEX và VN30, cùng cách đọc với bảng cổ phiếu: mức hợp lý, chênh lệch, kết luận Rẻ/Hợp lý/Đắt theo ngưỡng trong Cài đặt. Không phải khuyến nghị.

## Nguồn

- Vnstock 5.2 gói Cộng đồng **không** có P/E, P/B chỉ số (`Analytics().valuation(...)` báo "không thuộc quyền của cấp Cộng đồng", kiểm tra 31/10/2026).
- Dùng API công khai của VNDirect (nguồn mà Vnstock dùng cho số này): `https://api-finfo.vndirect.com.vn/v4/ratios`, mã `PRICE_TO_EARNINGS` và `PRICE_TO_BOOK`, chỉ số `VNINDEX`, `VN30`. Số theo ngày từ 15/12/2017. robots.txt của máy chủ này cho phép mọi user-agent (`Allow: /`, `use=reference`).
- P/E của VNDirect tính trên lợi nhuận bốn quý gần nhất, nên nhảy khi doanh nghiệp công bố báo cáo quý (ví dụ 29→30/10/2026: chỉ số −0,8%, P/E −7%). Trang ghi chú điều này.
- Điểm chỉ số lấy từ chuỗi giá đóng cửa đã lưu (`trend-sources/VNINDEX-1d`, `VN30-1d`), đúng ngày của P/E.

## Cách tính

Mỗi chỉ số có hai phương án:

- **P/E lịch sử:** mức hợp lý = điểm chỉ số × P/E trung vị 5 năm / P/E hiện tại.
- **P/B lịch sử:** như trên với P/B.

Trung vị lấy trên các giá trị theo ngày trong 5 năm tính đến ngày số liệu mới nhất. Mức hợp lý = trung vị hai phương án, khoảng = thấp nhất – cao nhất. Chênh lệch = điểm / mức hợp lý − 1; Rẻ/Đắt theo cùng ngưỡng ±trong Cài đặt như bảng cổ phiếu.

Không đoán số:

- phương án cần lịch sử phủ ít nhất 4 năm, nếu không ghi lý do;
- số liệu mới nhất cũ hơn 10 ngày thì không dùng, ghi lý do;
- thiếu điểm chỉ số đúng ngày của P/E thì không dùng, ghi lý do;
- ít hơn 2 phương án đủ dữ liệu thì "Chưa đủ dữ liệu".

## Lịch chạy

Bước `index-valuation-sync` trong `run-after-close.ps1`, mỗi lượt: lần đầu tải toàn bộ lịch sử, sau đó chỉ 14 ngày gần nhất (4 lượt gọi). Lưu ở `data/index-valuation/` (không vào Git). Nguồn lỗi thì ghi log và lượt chạy tiếp tục.

## Giao diện

Bảng nhỏ "Chỉ số thị trường" phía trên bảng cổ phiếu: chỉ số, điểm, mức hợp lý (khoảng), chênh lệch, kết luận, ngày số liệu; mỗi phương án ghi P/E (P/B) hiện tại, trung vị 5 năm và khoảng thời gian. Không lọc, không vào danh sách cổ phiếu.

## Biểu đồ dùng toàn bộ lịch sử (07/11/2026, chủ sở hữu yêu cầu)
Biểu đồ P/E, P/B theo tháng của VN-Index và VN30 (Định giá → Chi tiết) hiện mọi tháng đã lưu thay vì 5 năm, trung vị và dải ± độ lệch chuẩn tính
trên toàn bộ số liệu theo ngày, như biểu đồ của mã cổ phiếu. API tỷ số của VNDirect chỉ có từ 15/12/2017 (gọi từ 2000 vẫn bắt đầu ngày đó), nên
chuỗi bắt đầu từ 12/2017; trước đó không có nguồn sẵn (tự tính cần báo cáo của mọi mã trên sàn). Mức hợp lý ở bảng chỉ số giữ trung vị 5 năm.

## VN-Index 2013–2017 tự tính (07/11/2026, chủ sở hữu yêu cầu, biết rõ giới hạn)
- Không có nguồn công khai, miễn phí, hợp lệ cho P/E, P/B VN-Index trước 12/2017 (đã tìm: CEIC, EODHD, Bloomberg, FiinPro trả phí; báo cáo công ty chứng khoán
  chỉ có số rời; Smoney chặn bot). Nên **tự tính** (`market/index_history.py`, lệnh một lần `index-history`):
  - 408 mã cổ phiếu HOSE hôm nay (`hose-listing.json`); mỗi mã một lượt báo cáo quý VNDirect lọc theo các dòng mọi mẫu báo cáo dùng chung (LNST công ty mẹ
    23000, vốn chủ 14000, lợi ích cổ đông không kiểm soát 14240/15000, vốn góp 14110; cả ngân hàng, chứng khoán, bảo hiểm) và một lượt giá thực (từ 2013).
  - Mỗi ngày: tổng vốn hóa (giá đóng cửa gần nhất trong 30 ngày × vốn góp ÷ 10.000 đ của quý đã công bố) ÷ tổng LNST công ty mẹ 4 quý, ÷ tổng vốn chủ công
    ty mẹ; chỉ các mã có đủ quý **lẽ ra đã công bố** (45 ngày), thiếu thì loại khỏi ngày đó, không dùng số cũ.
- **Đối chiếu** cùng cách tính với VNDirect ở 108 tháng trùng nhau (12/2017–11/2026): P/E lệch trung bình 4,6 % (lớn nhất 14,8 %), P/B 2,3 % (lớn nhất 19,1 %);
  ngưỡng chấp nhận đặt trước là dưới 10 %. Lưu `index-valuation/VNINDEX-calc-check.json`.
- Biểu đồ VN-Index nối phần tự tính trước 15/12/2017, **nét đứt màu xám**, chú thích ghi số mã, "thiếu các mã đã hủy niêm yết nên quá khứ bị lệch" và mức lệch
  so với VNDirect; trung vị, dải của biểu đồ tính trên chuỗi đã nối. Mức hợp lý ở bảng vẫn trung vị 5 năm VNDirect. **VN30 không có** phần này (không dựng
  lại được rổ từng kỳ). Dữ liệu trước 2018 không đổi nên không chạy theo lịch; chạy lại `index-history` khi cần.
- **VN30 2013–2017** (chủ sở hữu chọn 07/11/2026): rổ thật không có dạng dữ liệu, nên dùng **rổ ước tính**: 30 mã vốn hóa lớn nhất trong 408 mã ở phiên cuối tháng 12
  (áp dụng từ 1/2) và cuối tháng 6 (từ 1/8); trước kỳ đổi đầu tiên lấy theo 02/01/2013. Luật thật còn xét free-float và thanh khoản. Đối chiếu VNDirect 108 tháng:
  P/E lệch trung bình 5,1 % (tháng nhiều nhất 29,8 %), P/B 4,1 % (29,7 %); đạt ngưỡng dưới 10 %. Chú thích ghi "rổ ước tính" và cả mức lệch nhiều nhất.

