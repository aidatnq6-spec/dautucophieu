# Dự phóng quý tới (07/11/2026)

Cột vàng "Qn/yyF" trong bảng quý của Bảng số tài chính, như ảnh bảng số HPG chủ sở hữu gửi. **Kịch bản của chủ sở hữu, không phải dự báo của
ứng dụng**: ứng dụng không tự điền giả định; dòng nào dựa vào một ô để trống thì để trống. Không gọi AI, không đọc danh mục.

## Giả định (kho cá nhân `settings/quarter_forecast_<MÃ>`, theo quý)
Doanh thu % so cùng kỳ (−100 % đến 1.000 %), biên gộp (−100 % đến 100 %), chi phí bán hàng và quản lý (% doanh thu, 0–100 %), doanh thu tài
chính, chi phí tài chính, lãi vay (phần của chi phí tài chính), LN liên doanh liên kết, LN khác, khấu hao (tỷ đồng), thuế suất và phần cổ đông
không kiểm soát (0–100 %). Chỉ nhận cho **quý ngay sau quý VNDirect mới nhất**.

## Tính (`domain/quarter_forecast.py`)
Doanh thu = cùng quý năm trước × (1 + tăng trưởng); giá vốn = doanh thu × (1 − biên gộp); chi phí bán hàng, quản lý = % × doanh thu; LN HĐKD lõi
= lãi gộp − bán hàng − quản lý; LNTT = lõi + doanh thu tài chính − chi phí tài chính + liên doanh liên kết + LN khác; LNST công ty mẹ = LNTT ×
(1 − thuế suất) × (1 − phần cổ đông không kiểm soát); EBIT = LNTT + lãi vay; EBITDA = EBIT + khấu hao; % so cùng kỳ của doanh thu và LNST công ty
mẹ; các biên. Chưa có doanh thu cùng quý năm trước thì không có cột và ghi lý do.

## API và giao diện
- `GET /internal/quarter-forecast/{mã}`: quý tới, giả định đã lưu, cột tính được, và các dự phóng cũ của quý đã có số thật (doanh thu, LNST
  công ty mẹ: dự phóng bên cạnh thực tế). `PUT /internal/quarter-forecast/{mã}/{quý}`.
- Bảng quý: cột "Qn/yyF" nền vàng sau quý cuối; mục "Dự phóng Qn/năm (giả định của bạn)" với 12 ô (tỷ lệ nhập theo %), nút Lưu, danh sách so
  dự phóng với thực tế, chú thích công thức.
