# Trung vị ngành cấp 4 cho doanh nghiệp thường

Chủ sở hữu chọn ngày 28/11/2026: doanh nghiệp thường được so trong nhóm ICB cấp 4 khi nhóm đó có ít nhất 5 mã khác có số, không thì giữ nhóm ICB cấp 2 như spec 26/11 ([2026-11-26-so-sanh-nganh-design.md](2026-11-26-so-sanh-nganh-design.md)).

## Vì sao

ICB cấp 2 gộp các ngành có cấu trúc tài chính khác nhau: "Xây dựng và Vật liệu" (54 mã) gồm Xây dựng công trình (30) và Vật liệu xây dựng (24); "Điện, nước & xăng dầu khí đốt" gồm Điện (19) và Gas (7); "Hàng & Dịch vụ Công nghiệp" gồm vận tải, vận tải biển, thiết bị điện. Biên gộp, số ngày tồn kho, nợ vay của nhà thầu và nhà sản xuất vật liệu khác nhau nên trung vị chung dễ gây hiểu sai.

## Cách đã cân nhắc

| | Cách | Được | Mất |
|---|---|---|---|
| **A (chọn)** | Cấp 4 khi có ít nhất 5 mã khác có số, không thì cấp 2 | Nhóm sát hơn cho 276/361 mã (28/11/2026); nhóm nhỏ không bị trung vị của 3 mã | Hai mã cùng cấp 2 có thể so với hai nhóm khác nhau |
| B | Luôn cấp 4 | Một quy tắc | 85 mã có nhóm dưới 5 mã, trung vị dao động mạnh hoặc không có |
| C | Chọn cấp 3 | Ở giữa | Kho chưa có cấp 3; thêm một lượt gọi VNDirect |

## Thiết kế

1. `hose_listing` lưu thêm `icb4_names` (tên tiếng Việt của nhóm cấp 4, cùng lượt gọi `industryLevel:4` đang có). Bản lưu chưa có `icb4_names` thì làm mới ở lượt kế tiếp.
2. `compare_sector`, `sector_history`, `sector_trend` cho doanh nghiệp thường (không phải ngân hàng, chứng khoán, bảo hiểm): nếu mã có cấp 4 và nhóm cấp 4 có ít nhất 5 mã khác (không gồm mã đang xem) có tệp chỉ số trong `financial-ratios-general`, thì nhóm so là nhóm cấp 4; không thì cấp 2. Nhóm được chọn một lần cho mã, không đổi theo quý, để đường trung vị theo quý cùng một nhóm. Mỗi quý vẫn cần ít nhất 3 mã có số (spec 26/11).
3. Kết quả có thêm `cap_nganh` (2 hoặc 4); `nganh` là tên nhóm cấp 4 (VNDirect); thiếu tên thì ghi "ICB <mã>"; `luu_y` nói đúng cấp. Công ty chứng khoán vẫn là cấp 4 Dịch vụ đầu tư, ngân hàng và bảo hiểm giữ nguyên.
4. Route `/fairvalue/ratios/{mã}`: `sector.level`; chú thích dưới bảng ghi "ICB cấp 4" hoặc "ICB cấp 2" theo `level`.
5. `so_sanh_nganh`, skill `/dautu-ma`, hướng dẫn Project sửa theo; plugin 0.26.0.

## Không làm

- Không đổi 16 chỉ số, tối thiểu 3 mã mỗi quý, cách tính tứ phân vị và thứ hạng.
- Không đổi phân ngành của Bản tin, Thị trường, Chuỗi giá trị (vẫn cấp 2).
- Không cho chọn cấp bằng tay trên giao diện.

## Quyết định của người dựng

- "5 mã khác có số" đếm mã có tệp chỉ số trong kho, không đếm theo từng quý, để nhóm không nhảy giữa các quý.

## Bổ sung: bước cấp 3 (chủ sở hữu chọn ngày 28/11/2026, cách A)

Sau bản cấp 4, 85/361 mã còn so ở cấp 2 vì nhóm cấp 4 dưới 5 mã khác (Giấy, Bao bì, Nước, Bán lẻ tổng hợp…). Thứ tự chọn nhóm nay là cấp 4 → cấp 3 → cấp 2, cùng ngưỡng 5 mã khác có tệp chỉ số.

| | Cách | Cấp 4 / 3 / 2 (28/11/2026) |
|---|---|---|
| **A (chọn)** | Giữ ngưỡng 5, thêm bước cấp 3 | 276 / 36 / 49 |
| B | Ngưỡng 4 | 281 / – / 80 |
| C | Ngưỡng 3 | 289 / – / 72 (trung vị 3 mã dao động, quý thiếu một mã thành "—") |
| D | Giữ nguyên | 276 / – / 85 |

- `hose_listing` lưu thêm `icb3_codes` và `icb3_names` từ một lượt gọi `industryLevel:3` (danh sách mã của từng nhóm, như cấp 2 và cấp 4; không suy từ mã cấp 4 vì `higherLevelCode` của VNDirect không thống nhất). Lượt gọi này lỗi thì không có cấp 3, cấp 4 và cấp 2 vẫn giữ. Bản lưu thiếu `icb3_names` thì làm mới ở lượt kế tiếp.
- Nhóm cấp 3 chỉ được dùng khi nó hẹp hơn ngành cấp 2 (có ít mã hơn); trùng với cấp 2 thì ghi là cấp 2.
- `cap_nganh` và `sector.level` có thể là 3; chú thích ghi "ICB cấp 3". Plugin 0.27.0.
