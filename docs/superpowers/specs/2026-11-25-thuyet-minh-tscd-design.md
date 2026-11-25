# Thuyết minh TSCĐ nhập tay: dự án XDCB và khung khấu hao (25/11/2026)

**Chờ chủ sở hữu duyệt.** Chủ sở hữu chọn ngày 25/11/2026: nhập cho **mọi mã theo dõi** (không gắn Luận điểm); đến quý hoàn thành dự kiến thì
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
