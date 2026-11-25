# Thuyết minh TSCĐ nhập tay: dự án XDCB và khung khấu hao (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026, nguyên văn; đã chọn: nhập cho **mọi mã theo dõi** (không gắn Luận điểm); đến quý hoàn thành dự kiến thì
**một dòng ở Việc cần xem**, không gửi Telegram; **chưa** thêm điều kiện "Dự án trễ hạn" vào Luận điểm. Phần sau của
[Tài sản cố định](2026-11-25-tai-san-co-dinh-design.md) và [Hai dấu hiệu XDCB](2026-11-25-tin-hieu-xdcb-design.md): VNDirect không có nội dung
thuyết minh (tên dự án, tiến độ, thời gian khấu hao), nên chủ sở hữu tự ghi khi đọc báo cáo, như "Dự án và điểm rơi lợi nhuận" của mã bất động sản.
Dữ liệu chủ sở hữu nhập, lưu ở kho cá nhân, không gửi AI. Không phải khuyến nghị.

## Nội dung (mỗi mã một bản ghi `settings/fixed_asset_notes_<mã>`, có phiên bản chống ghi đè)
Chỉ doanh nghiệp thường trong danh sách theo dõi (ngân hàng, chứng khoán, bảo hiểm: 404 như Bảng số tài chính).

**Dự án XDCB** (tối đa 20):
- Tên dự án (1–120 ký tự, bắt buộc), ví dụ "Khu liên hợp Gang thép Dung Quất 2".
- **Quý hoàn thành dự kiến** (bắt buộc, dạng Q3/2027).
- Kỳ báo cáo đã đọc (tùy chọn, năm 2025 hoặc quý Q2/2026) và giá trị dự án trong XDCB tại kỳ đó (tỷ đồng, tùy chọn).
- Tổng vốn đầu tư dự kiến (tỷ đồng, tùy chọn). Link nguồn (http/https, tùy chọn). Ghi chú (tối đa 500 ký tự).
- Trạng thái: **đang làm** hoặc **đã hoàn thành** (kèm ngày chủ sở hữu xác nhận).
- **Lùi hạn**: đổi quý hoàn thành dự kiến qua nút "Lùi hạn" ghi quý cũ, quý mới, ngày và lý do (tùy chọn, tối đa 200 ký tự); lịch sử lùi hạn
  được giữ và hiện cạnh dự án (ví dụ "đã lùi 2 lần"). Sửa thẳng ô quý không được khi dự án đã có quý; tên, số tiền, ghi chú sửa tự do.
- Xóa dự án được (bản ghi có phiên bản nên các bản cũ vẫn còn trong kho).

**Khung khấu hao** (tùy chọn) theo 6 nhóm của thuyết minh: nhà cửa, vật kiến trúc; máy móc, thiết bị; phương tiện vận tải, truyền dẫn; thiết bị,
dụng cụ quản lý; vật nuôi, cây lâu năm; TSCĐ khác. Mỗi nhóm số năm từ–đến (số nguyên 0–100, "từ" không lớn hơn "đến"), cùng kỳ báo cáo đã đọc.
Chỉ để đọc lại; phần mềm không dùng để tính khấu hao.

Số tiền nhập như ô tỷ đồng của "Dự án và điểm rơi lợi nhuận" (7.500 hoặc 7500, dấu phẩy thập phân). Thiếu thì để trống, không suy ra.

## Giao diện
Khối **Thuyết minh TSCĐ (nhập tay)** ở hồ sơ mã, ngay sau Bảng số tài chính: bảng dự án (tên, quý hoàn thành dự kiến, trạng thái, số lần lùi
hạn, XDCB và tổng vốn bạn ghi, nguồn), nút Thêm dự án, Lùi hạn, Đã hoàn thành; bảng khung khấu hao. Cạnh mỗi dự án đang làm, số đọc từ báo cáo
đã lưu (không phải số nhập): XDCB dở dang và nguyên giá TSCĐ hữu hình của cả công ty ở kỳ đã đọc và ở quý mới nhất. Ghi chú: "XDCB và nguyên giá
là số của cả công ty; báo cáo không tách theo dự án".

## Đến hạn
- Một dự án **đang làm** đến hạn khi báo cáo quý của quý hoàn thành dự kiến đã có trong báo cáo VNDirect đã lưu (có XDCB dở dang quý đó).
  Quá quý đó mà báo cáo chưa có: chưa đến hạn, trang ghi "chờ báo cáo Qx/yy".
- Đến hạn thì Việc cần xem (trang Tổng quan) có một dòng mức thấp, dẫn tới hồ sơ mã: "HPG: dự án <tên> đến quý hoàn thành dự kiến Q3/25. XDCB dở
  dang cuối Q3/25: A tỷ (kỳ đã đọc 2024: B tỷ); nguyên giá TSCĐ hữu hình: C tỷ (D tỷ). Xác nhận đã hoàn thành hoặc lùi hạn." Thiếu số nào thì
  ghi "chưa có" ở chỗ đó. Dòng còn đến khi chủ sở hữu bấm Đã hoàn thành hoặc Lùi hạn.
- Không gửi Telegram: dòng này **không** vào danh sách việc của Bản tin tuần.
- Phần mềm không tự kết luận dự án đã xong: XDCB giảm có thể do dự án khác, nên chỉ đưa số để chủ sở hữu xác nhận.

## Không làm
- Điều kiện "Dự án trễ hạn" trong Luận điểm (để sau, chủ sở hữu quyết sau khi dùng).
- Ngân hàng, chứng khoán, bảo hiểm.

## Chi phí trả trước: phân bổ trong năm (bổ sung 25/11/2026, chủ sở hữu duyệt bước 3 của đề xuất chi phí trả trước)
- Cùng bản ghi, khóa `prepaid`: mỗi năm (tối đa 15) số phân bổ theo loại của thuyết minh, tỷ đồng: công cụ dụng cụ, sửa chữa lớn, tiền thuê
  đất và đền bù, chi phí trước hoạt động, khác; và tổng phân bổ nếu thuyết minh ghi. Năm không có số nào thì không lưu được.
- Tổng = số thuyết minh ghi; không ghi thì cộng các loại đã nhập (ghi rõ "cộng các loại đã nhập"). HPG 2021: công cụ 109, sửa chữa lớn 139, tổng 425.
- **Số năm phân bổ còn lại** = chi phí trả trước dài hạn cuối năm đó (báo cáo đã lưu, dòng 12610) ÷ tổng phân bổ năm đó, một chữ số thập phân,
  ghi "nếu giữ nhịp phân bổ năm đó" (HPG 2021: 3.171 ÷ 425 ≈ 7,5). **Phân bổ ÷ LNTT** năm đó. Thiếu số dư, LNTT hoặc LNTT không dương: để trống.
- Lùi hạn, hoàn thành dự án và lưu bảng dự án từ trang cũ (không gửi `prepaid`) giữ nguyên số phân bổ đã lưu.

## Thương vụ mua bán, sáp nhập (bổ sung 25/11/2026, chủ sở hữu duyệt bước 2 của đề xuất lợi thế thương mại)
- Cùng bản ghi, khóa `deals` (tối đa 20, xếp theo ngày mua), từ thuyết minh hợp nhất kinh doanh: công ty được mua (bắt buộc), ngày mua
  (15/03/2024), tỷ lệ mua (trên 0 đến 100%), giá mua và giá trị hợp lý tài sản thuần của cả công ty được mua (tỷ đồng, tài sản thuần có thể âm),
  số năm phân bổ (tùy chọn, 1–10 theo VAS), link nguồn, ghi chú.
- **Lợi thế thương mại = giá mua − tỷ lệ × giá trị hợp lý tài sản thuần** (công thức của bài). Dương: phân bổ đều = lợi thế thương mại ÷ số năm,
  hết vào ngày mua + số năm; không ghi số năm thì không có lịch. Âm: **lãi mua rẻ**, lợi nhuận một lần năm mua, cần loại ra khi so lợi nhuận.
- Dưới bảng: tổng mức phân bổ mỗi năm của các thương vụ đang phân bổ hôm nay (theo số năm chủ sở hữu ghi).
- Ghi phần khác không gửi `deals` thì giữ nguyên thương vụ đã lưu.
