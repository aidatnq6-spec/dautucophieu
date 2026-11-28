# Chuỗi giá trị cho Claude (MCP)

Chủ sở hữu chọn ngày 28/11/2026 (cách B). Khi nhờ Claude phân tích một mã, chủ sở hữu muốn biết mã thuộc ngành nào, ngành đang hưởng lợi hay bất lợi, vĩ mô có ủng hộ ngành không. Công cụ đọc chuỗi giá trị như trang Thị trường & Ngành ([2026-10-30-chuoi-gia-tri-nganh-design.md](2026-10-30-chuoi-gia-tri-nganh-design.md)).

## Cách đã cân nhắc

| | Trả về | Được | Mất |
|---|---|---|---|
| A | Chuỗi của mã: các khâu kèm nguồn, từng yếu tố vĩ mô, nhãn tổng | Trả lời "vĩ mô có ủng hộ không" | Không biết giá ngành đã đi tới đâu |
| **B (chọn)** | A, thêm hiệu suất theo kỳ và P/E, P/B trung vị so với 5 năm của chuỗi | Thấy thị trường đã phản ánh ngành tới đâu | Thêm phần tính |
| C | A, thêm `danh_sach_chuoi()` chỉ có tên chuỗi | Hỏi theo ngành không cần mã | Câu hỏi luôn bắt đầu từ một mã |

## Thiết kế

Một công cụ `chuoi_gia_tri(ma)` trong `public_tools.py`, đăng ký ở `mcp_server` (bản trên máy và bản từ xa dùng chung).

1. **Tìm chuỗi theo ngành của mã (chủ sở hữu chọn ngày 28/11/2026).** 25 chuỗi gồm 55 mã, gần bằng số mã đang theo dõi, nên trả chuỗi theo thành viên sẽ gián tiếp lộ danh sách theo dõi. Công cụ đọc ngành ICB cấp 2 của mã trong `hose-listing.json` rồi trả mọi chuỗi trong `config/value-chains.json` có `icb` trùng tên ngành đó (1–3 chuỗi), theo thứ tự trong tệp. Mọi mã cùng ngành nhận cùng kết quả; kết quả không nói mã có nằm trong `symbols` của chuỗi hay không. `luu_y` nhắc Claude tự xét chuỗi nào sát với hoạt động của mã, và nói rõ khi chưa chắc. Mã không hợp lệ hoặc chưa có ngành ICB thì `thieu` kèm lý do.
2. **Mỗi chuỗi trả:**
   - Tên, trạng thái `da_duyet` (true hoặc false), ngày duyệt. Duyệt trong tệp cấu hình hoặc trên web cho đúng nội dung hiện tại, như `scored_chains`; duyệt cho nội dung cũ thì coi là chưa duyệt.
   - Các khâu Đầu vào → Trung gian → Đầu ra: tên, ghi chú, tỷ trọng nếu có, nguồn (tên báo cáo, đơn vị, ngày, trang, đường dẫn trong `sources`).
   - Từng yếu tố: tên, khâu, chỉ báo, chiều 1 tháng (tăng, giảm, đi ngang), tác động lên ngành (tốt, xấu, trung tính, chưa đánh giá được, sự kiện), trọng số (chính, phụ, nhỏ), ngày và giá trị của số mới nhất, lý do (`why`), nguồn. Yếu tố chưa đánh giá được thì ghi lý do: không có chuỗi số, chưa có số, số quá cũ, chỉ có một điểm.
   - Tỷ trọng tốt, xấu, trung tính, chưa đánh giá được theo trọng số (`score`).
   - Nhãn tổng (thuận lợi, trung tính, bất lợi, chưa đủ dữ liệu) chỉ khi đã duyệt. Bản nháp có `nhan: null` và lời nhắc "chuỗi chưa được chủ sở hữu duyệt; không có nhận định tổng".
   - Hiệu suất theo kỳ (`chain_returns`): thay đổi bình quân các mã của chuỗi trong 1 tuần, 1 tháng, 3 tháng, 1 năm, từ đầu năm, kèm số mã tính được; số mã tăng, giảm, đứng giá phiên gần nhất; vị trí trung vị trong biên độ 52 tuần.
   - Định giá (`chain_valuation`): P/E và P/B trung vị hiện tại, trung vị 5 năm, vị trí so với 5 năm, số mã; ngày bắt đầu khi lịch sử ngắn hơn 5 năm.
   - Số mã của chuỗi và số mã có giá hoặc có định giá. Không có danh sách mã, không có mã dẫn đầu, không có tên mã thiếu số hay số cũ: chỉ có số đếm.
3. **Ngành chưa có chuỗi** (ví dụ Y tế, Ô tô và phụ tùng): `thieu: true`, lý do "chưa có chuỗi giá trị cho ngành <tên>", kèm ngành ICB cấp 2 của mã, để Claude nói rõ là đang thiếu chứ không suy từ chuỗi của ngành khác.
4. **Mỗi kết quả có** `nguon` (tệp cấu hình, chuỗi vĩ mô, giá đóng cửa và định giá trong kho), `ngay` (hôm nay theo giờ Việt Nam) và `luu_y`: nhận định là phép tính trên chiều chỉ báo 1 tháng theo trọng số đã đặt, không phải dự báo; bình quân giá là bình quân các mã, không theo vốn hóa.

## Ràng buộc

- Không đọc Firestore, danh sách theo dõi hay mã đang nắm (`held` luôn rỗng). Tệp `data/value-chain-approvals.json` chỉ chứa việc duyệt nội dung chuỗi, không có số liệu cá nhân, nên được đọc.
- Không liệt kê thành viên chuỗi và không cho biết một mã có là thành viên hay không, để không lộ gián tiếp mã đang theo dõi.
- Không đoán: thiếu số thì để `null` kèm lý do.

## Kèm theo

- `docs/claude-project-instructions.md` thêm công cụ và cách dùng; skill `/dautu-ma` thêm mục "Ngành và vĩ mô" gọi `chuoi_gia_tri`: nêu chuỗi, trạng thái duyệt, các yếu tố tốt và xấu chính, hiệu suất và định giá so với 5 năm. Plugin 0.28.0.

## Để người dựng quyết

- Tên trường tiếng Việt không dấu theo kiểu các công cụ đang có; số giữ dạng chuỗi như kho.
- Định giá chỉ tính cho các chuỗi của mã hỏi, không tính cả 25 chuỗi.

## Sửa sau khi thử trên dữ liệu thật (chủ sở hữu chọn ngày 28/11/2026, cách 1)

Thử trên kho thật cho thấy vẫn lộ thành viên: 10/25 chuỗi chỉ có 1 mã và 10 chuỗi có 2 mã, nên "bình quân" và "trung vị" của chuỗi gần như là số của từng mã; 10/25 chuỗi có mã HOSE trong phần chữ (tên khâu, ghi chú, lý do). Kho `trend-sources` mà trang web dùng để tính hiệu suất cũng chỉ có khoảng 98 mã, phần lớn là mã đang theo dõi.

- Hiệu suất và định giá chuyển từ từng chuỗi lên `thong_ke_nganh`, tính trên mọi mã HOSE cùng ngành ICB cấp 2: hiệu suất là bình quân giá đã điều chỉnh trong `price-history` (đủ mã HOSE), cùng cách tính kỳ của `chain_returns`; định giá là trung vị P/E, P/B hiện tại và trung vị của các trung vị 5 năm, theo số tự tính của từng mã trong `index-history` (như `dinh_gia_lich_su`), kèm số mã đang thấp hơn trung vị 5 năm của chính nó. Số này khác số trên trang Chuỗi giá trị (tính theo thành viên chuỗi).
- Mã HOSE trong phần chữ thay bằng "[mã]"; "HRC" (thép cuộn cán nóng) giữ nguyên. Tên doanh nghiệp viết bằng chữ (Vingroup, Formosa, Lọc dầu Dung Quất) vẫn còn trong phần chữ.
- Nguồn trích dẫn của chuỗi phần lớn là báo cáo từng doanh nghiệp ("Cập nhật KDH – MUA", đường dẫn PDF mang mã): tên báo cáo cũng thay mã bằng "[mã]", đường dẫn bị bỏ; còn đơn vị phát hành, ngày, trang. "VND" (đơn vị tiền) giữ nguyên như "HRC". Đã kiểm 14 ngành có chuỗi trên kho thật ngày 28/11/2026: không còn mã HOSE nào trong kết quả ngoài mã được hỏi.
