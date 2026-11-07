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
## Đọc số từ PDF công khai (07/11/2026)
- Trong mỗi nhóm: ô "Đọc từ PDF công khai (link https)" và nút Đọc PDF → `POST /internal/operating/{mã}/groups/{nhóm}/read-pdf`. Cùng cách tải an toàn như
  Số liệu ngân hàng (chỉ https tới địa chỉ công khai, không theo chuyển hướng, tối đa 30 MB, 250 trang). Không gọi AI.
- `domain/operating_pdf.py`: với mỗi dòng của nhóm, tìm các dòng chữ trong PDF chứa tên dòng (bỏ qua hoa thường, dấu), lấy số đầu tiên sau tên (đọc kiểu Việt
  Nam: dấu chấm nhóm nghìn, dấu phẩy thập phân; bỏ năm đứng riêng và phần của ngày tháng như 10/2026); tối đa 3 ứng viên, mỗi ứng viên kèm trang và đoạn chữ
  gốc. PDF chỉ có ảnh (scan) thì ghi "hãy nhập tay".
- **Không lưu gì** cho tới khi chủ sở hữu bấm Lưu kỳ: ứng viên đầu điền vào ô, link kèm số trang điền vào Nguồn; có thể bấm chọn ứng viên khác; chú thích nhắc
  kiểm tra đơn vị (PDF có thể ghi tấn khi nhóm là nghìn tấn). Kỳ do chủ sở hữu nhập.
- **Sửa sau khi thử PDF thật của HPG (07/11/2026, chủ sở hữu đồng ý).** Hòa Phát đăng PDF dạng scan: bản chỉ có ảnh, bản có lớp chữ nhận dạng sai
  ("th6p" thay cho "thép") hoặc ra tên ký tự phông (`/Ohorn.dotbl`). Bộ đọc trước đó đề xuất số sai: "3.5 million tonnes, up 35%" cho ra 35.
  - Số đầu tiên sau tên viết không theo kiểu Việt Nam (3.5, 1,234,567, 12.5%) thì dòng đó **không có ứng viên**, không lấy số sau nó. Chữ số
    dính vào chữ (Q3, th6p, l3%) là một phần của từ, bỏ qua.
  - Trang có chữ bị lỗi (từ 3 tên ký tự phông trở lên, hoặc từ 3 từ có chữ số ở giữa và chiếm ít nhất 2 % số từ) không cho ứng viên; cảnh báo
    "Chữ ở trang … bị lỗi phông hoặc nhận dạng kém: không lấy số từ các trang này, hãy nhập tay."
  - Kiểm trên dữ liệu thật: 6 PDF của HPG (2 chỉ có ảnh, 4 có chữ lỗi, đều báo đúng); 77 trang của 4 báo cáo ACBS có chữ sạch, không trang nào bị
    coi là lỗi.
