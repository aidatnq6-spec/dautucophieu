# Vàng theo số chỉ × giá vàng công khai (06/11/2026)

Việc sau thứ ba của [Sổ tài sản](2026-11-05-so-tien-gui-design.md), làm giống [chứng chỉ quỹ theo NAV](2026-11-06-ccq-theo-nav-design.md).
Chủ sở hữu chọn (06/11/2026): bảng Vàng giống bảng Trái phiếu và chứng chỉ quỹ, "Số chỉ" thay cho "Số đơn vị"; mỗi dòng tự chọn loại giá;
giá trị theo giá **mua vào** (số tiền thực nhận nếu bán lại); nguồn **Phú Quý**.

## Nguồn giá
- **Phú Quý** (bảng giá trên trang chủ phuquygroup.vn): mọi loại (Vàng miếng SJC, Nhẫn tròn Phú Quý 999.9, vàng trang sức 999.9/999/99/98,
  vàng phi SJC…), giá mua vào và bán ra theo chỉ, kèm giờ cập nhật. phuquygroup.vn không có robots.txt (404: không giới hạn, RFC 9309) và
  không chặn bot (kiểm tra 06/11/2026). Đọc từ HTML: tiêu đề cột phải ghi "(VNĐ/Chỉ)", đổi đơn vị thì không lưu. Bỏ các dòng bạc.
- Không dùng: SJC (dịch vụ giá nằm sau lớp chặn bot Cloudflare: chương trình bị trả 403, không lách), PNJ (API cần token), Bảo Tín Minh Châu
  (api.btmc.vn chặn mọi đường dẫn). Vàng hãng khác (ví dụ nhẫn PNJ) tính theo loại Phú Quý mà chủ sở hữu chọn: trang ghi rõ "giá Phú Quý",
  là giá tham chiếu.

## Đồng bộ
- Lệnh `gold-price-sync` mỗi lượt sau giờ đóng cửa; lưu `data/gold-price.json` (loại, mua vào, bán ra theo chỉ, giờ cập nhật, nguồn). Trang
  lỗi, rỗng hoặc đổi đơn vị thì giữ bản cũ.

## Sổ tài sản
- Bảng Vàng có thêm **Loại giá** (chọn trong bảng Phú Quý) và **Số chỉ** (lớn hơn 0, tối đa 2 chữ số thập phân); có cả hai hoặc không có ô
  nào. Ô số tiền đổi tên **Vốn đã mua (đ)**.
- Có cả hai: giá trị hiện tại = số chỉ × giá mua vào/chỉ, làm tròn đến đồng, kèm chênh lệch so với vốn đã mua và "giá Phú Quý mua vào
  <x> đ/chỉ lúc hh:mm dd/mm/yyyy". Giá cũ hơn 3 ngày ghi "giá đã cũ". Loại không còn trong bảng: tính bằng vốn đã mua và ghi rõ.
- Tháp tài sản dùng giá trị này cho lớp Vàng.
