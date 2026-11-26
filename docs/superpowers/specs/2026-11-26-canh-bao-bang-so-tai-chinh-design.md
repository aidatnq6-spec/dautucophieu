# Cảnh báo lợi nhuận ngoài bán hàng và EPS lệch trên Bảng số tài chính

Chủ sở hữu duyệt ngày 26/11/2026: hai cảnh báo đã có cho Claude (MCP dữ liệu công khai) cũng hiện trên trang mã, ở Bảng số tài chính của doanh nghiệp thường.

## Cách tính (dùng chung với MCP, `market/report_flags.py`)

- **Lợi nhuận ngoài bán hàng**: (doanh thu tài chính + lợi nhuận khác) ÷ LNTT, cho quý gần nhất và tổng 4 quý gần nhất của báo cáo VNDirect đã lưu; cờ khi trên 30%. Không tính công ty liên kết. LNTT không dương, thiếu dòng hoặc chưa đủ 4 quý thì không tính và nói lý do. Chỉ doanh nghiệp thường.
- **EPS lệch**: năm mà (EPS ÷ EPS năm trước) ÷ (LNST công ty mẹ ÷ LNST công ty mẹ năm trước) trên 3 hoặc dưới 1/3; cả bốn số phải dương. Số liệu cơ bản (`fundamentals`), giữ nguyên như nguồn.

## Route

`GET /fairvalue/statements/{mã}` trả thêm `flags` cho doanh nghiệp thường: `{"outside_sales": {...}, "eps": [...]}` (cùng dạng `canh_bao_loi_nhuan_ngoai_ban_hang` và `canh_bao_eps.nam` của MCP); mã tài chính trả `flags: null`.

## Giao diện

- Ngay trên phần tóm tắt, cùng kiểu ghi chú P/E (`notice`):
  - "Lợi nhuận ngoài bán hàng: doanh thu tài chính và lợi nhuận khác bằng X% LNTT Q…/…[, Y% LNTT 4 quý đến Q…/…] (ngưỡng 30%). Lãi tiền gửi đều đặn cũng nằm trong doanh thu tài chính, nên đây không hẳn là khoản một lần." — chỉ khi quý gần nhất hoặc 4 quý vượt ngưỡng; chỉ nêu phần vượt.
  - "EPS lệch hẳn LNST công ty mẹ năm 2017, 2024, 2025 (hơn 3 lần so năm trước): có thể là lỗi nguồn hoặc phát hành nhiều cổ phiếu; số giữ nguyên như VNDirect." — chỉ khi có năm bị cờ.
- Không có cờ thì không hiện gì.
