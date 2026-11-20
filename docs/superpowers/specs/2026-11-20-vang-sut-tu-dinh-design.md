# Vàng: sụt từ đỉnh và độ truyền giá (20/11/2026)

Chủ sở hữu chọn ngày 20/11/2026: mục 3 và 4 trong các đề xuất từ bài phân tích giá vàng. Chủ sở hữu duyệt: làm ngay, giá SJC tự tích lũy;
đặt trong phần Chênh lệch vàng SJC so với thế giới trên trang Vĩ mô. Chỉ giá công khai; không đọc danh mục, không gọi AI, không dự báo.

## Nguồn (kiểm tra 20/11/2026)
- Vàng thế giới: giá gold-api.com mới được lưu từ 16/11/2026 (nguồn chỉ cho giá hiện tại), nên mức sụt từ đỉnh dùng chuỗi ngày PAXG-USD
  (Coinbase) mà bảng Xu hướng đã lưu từ 08/05/2025. Ghi "gần đúng giá vàng".
- Vàng miếng SJC: giá mua vào Phú Quý mỗi ngày (`gold-price-history.json`), có từ 14/11/2026. SJC chặn chương trình đọc tự động nên không
  có lịch sử cũ hơn; chuỗi tự dài thêm mỗi ngày.

## Sụt từ đỉnh (`domain/gold_moves.drawdown`)
- Số mới nhất so với giá cao nhất trong số liệu đã lưu; trang ghi số liệu tính từ ngày nào và nói rõ đây không phải đỉnh mọi thời.
- Số cũ: PAXG quá 7 ngày, SJC quá 3 ngày (như Sổ tài sản). Không có số thì ghi "Chưa có số liệu".

## Độ truyền giá trong 30 ngày (`domain/gold_moves.pass_through`)
- So mức đổi của giá SJC với giá thế giới quy ra đồng/chỉ (XAU/USD gold-api.com × tỷ giá bán Vietcombank × 3,75 / 31,1034768, như chênh
  lệch SJC), giữa ngày gần nhất có cả hai giá và ngày có cả hai giá gần nhất cách đó ít nhất 30 ngày. Tỷ giá lấy ngày gần nhất trước đó
  trong 7 ngày (cuối tuần, nghỉ lễ); không có thì bỏ ngày đó. Hiện cả hai mức đổi, không tính tỷ lệ truyền.
- Chưa đủ 30 ngày thì ghi từ ngày nào có cả hai giá và khoảng ngày nào có số.
