# Trung vị ngành cho ngân hàng

Chủ sở hữu yêu cầu ngày 27/11/2026: so sánh một ngân hàng với các ngân hàng cùng ngành, trên Bảng số tài chính và qua Claude.

## Mục đích

Khi xem một ngân hàng, thấy ngay mỗi chỉ số của nó đứng ở đâu so với các ngân hàng khác trên HOSE (trung vị, tứ phân vị, thứ hạng), giống như doanh nghiệp thường đã có từ 26/11/2026.

## Phạm vi

- Chỉ ngân hàng (ICB cấp 2 "Ngân hàng", 22 mã HOSE ngày 27/11/2026). Chứng khoán và bảo hiểm để sau: ngành "Dịch vụ tài chính" lẫn công ty chứng khoán với công ty tài chính khác.
- Trung vị cho 9 chỉ số VNDirect đang hiện trên bảng: NPL, nợ quá hạn, bao phủ nợ xấu, NIM, LDR, tăng trưởng cho vay, vốn chủ / tổng tài sản, ROAA, ROAE.
- Không tính trung vị cho CASA và tỷ lệ nợ nhóm 2: hai dòng này lấy từ thuyết minh Vietcap và số nhập tay, chỉ có cho ngân hàng đang theo dõi. Ô trung vị của hai dòng này để "—".

## Cách làm (chủ sở hữu chọn A)

| | Cách | Được | Mất |
|---|---|---|---|
| **A (chọn)** | `financial-ratios-sync` tải cho cả 22 ngân hàng HOSE; trung vị tính từ kho trên máy bằng `market/sector_compare` | Có lịch sử nhiều quý; trang và Claude dùng chung một kho và một phép tính với doanh nghiệp thường | Thêm khoảng 15 lượt gọi VNDirect mỗi lần chạy |
| B | Mỗi tối một lượt gọi lấy quý mới nhất của cả 22 ngân hàng, lưu tệp so sánh riêng | Ít lượt gọi nhất | Chỉ một quý, thêm kho và phép tính riêng |
| C | Gọi VNDirect khi mở trang | — | Trái cách ứng dụng đọc số từ kho; trang hỏng khi VNDirect chậm |

Đã kiểm 27/11/2026: VNDirect có đủ 9 chỉ số quý 3/2026 cho cả 22 ngân hàng.

## Thiết kế

1. **Tải:** `financial-ratios-sync` tải như cũ cho mọi mã tài chính đang theo dõi, và thêm mọi mã HOSE thuộc ngành "Ngân hàng" trong `hose-listing.json` (một lượt gọi mỗi mã, như hiện nay). Mã lỗi được báo, mã khác vẫn tải. Từ 27/11/2026 chỉ mã đang theo dõi tải lỗi mới làm bước này báo lỗi (và vào Tình trạng hệ thống); mã khác lỗi chỉ được ghi (`unwatched_failed`). Độ mới của "Chỉ số ngành" tính theo tệp cũ nhất của các mã tài chính đang theo dõi.
2. **Tính:** `compare_sector` nhận ngân hàng: đọc `data/financial-ratios/`, so với các ngân hàng có số ở đúng quý mới nhất của mã đang xem, không gồm mã đó; tối thiểu 3 ngân hàng như cũ. Tên chỉ số lấy từ nhãn trên bảng. Chứng khoán và bảo hiểm vẫn trả `thieu` với lý do.
3. **Trang:** Bảng số tài chính của ngân hàng, chế độ Quý, có cột "Trung vị ngành Qx/yyyy" như doanh nghiệp thường; chú thích dưới bảng nêu số ngân hàng được so và quý.
4. **Claude:** `so_sanh_nganh` trả 9 chỉ số cho ngân hàng (trung vị, tứ phân vị, thứ hạng); mô tả công cụ, skill `/dautu-ma` và hướng dẫn Project sửa theo (plugin lên 0.19.0).

## Không làm

- Không đổi điểm sức khỏe, cảnh báo quý mới hay các trang khác đang đọc `data/financial-ratios/`.
- Không gắn nhãn tốt hay xấu theo trung vị.
- Không ước lượng chỉ số cho ngân hàng thiếu số quý đó.

## Ghi chú

Sau thay đổi, kho `data/financial-ratios/` có mọi ngân hàng HOSE chứ không chỉ mã đang theo dõi, nên `chi_so_tai_chinh` cũng trả được số cho mọi ngân hàng; việc mã nào có số không còn để lộ danh sách theo dõi.
