# Số liệu vận hành nhập tay (07/11/2026)

Từ ảnh "Kinh doanh · Vận hành" HPG (sản lượng bán theo sản phẩm, thị phần, doanh thu theo mảng, nội địa/xuất khẩu). Các số này riêng từng công
ty, nằm trong bản tin sản xuất kinh doanh, thuyết minh báo cáo tài chính, báo cáo hiệp hội; không có nguồn API chung, nên chủ sở hữu tự định
nghĩa và nhập, theo khuôn Số liệu ngân hàng. Không gọi AI, không đọc danh mục.

## Lưu (kho cá nhân `settings/operating_<MÃ>`)
- Tối đa 12 nhóm mỗi mã. Nhóm: tên, đơn vị, kỳ (tháng, quý, năm), 1–12 dòng (tên khác nhau, ≤ 40 ký tự), kiểu biểu đồ: **cột chồng** (cộng các dòng
  thành tổng) hoặc **đường** (không cộng; thị phần %, giá bán). Mã nhóm là tên bỏ dấu (`san-luong-ban`).
- Mỗi kỳ: số của các dòng (số thực, có thể âm) và **nguồn bắt buộc**. Kỳ phải đúng kiểu của nhóm (2026-09, 2026-Q3, 2026). Đổi tên các dòng thì
  số của dòng không còn bị bỏ; đổi kiểu kỳ khi đã có số thì bị từ chối.

## Tính (`domain/operating.py`)
- Cột chồng: tổng của kỳ, tỷ trọng từng dòng, % tổng so với cùng kỳ năm trước. Kỳ thiếu một dòng thì không có tổng (ghi "thiếu …"), không lấp.
- Đường: giữ nguyên số đã nhập.

## API và giao diện
- `GET /internal/operating/{mã}`; `PUT …/groups/{nhóm}`; `POST …/groups/{nhóm}/delete`; `PUT …/groups/{nhóm}/values/{kỳ}`;
  `POST …/groups/{nhóm}/values/{kỳ}/delete`.
- Trang hồ sơ mã, khối **Số liệu vận hành** (sau Bảng số tài chính): mỗi nhóm một biểu đồ SVG 12 kỳ gần nhất (cột chồng hoặc đường) kèm chú
  thích màu, bảng (số, tỷ trọng, tổng, so cùng kỳ, nguồn, nút Xóa kỳ), biểu mẫu nhập kỳ; mục "Thêm nhóm số liệu".
- Chưa có: đọc số từ PDF bản tin công khai (có thể làm sau theo cách của Số liệu ngân hàng).
