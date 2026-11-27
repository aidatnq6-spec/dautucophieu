# Tự doanh cho Claude (công cụ MCP `tu_doanh`)

Chủ sở hữu yêu cầu ngày 27/11/2026: hỏi Claude "3–6 tháng gần nhất tự doanh đang mua bán các cổ phiếu nào". Chọn cách A.

## Nguồn

API công khai VNDirect `v4/proprietary_trading` (như mục Tự doanh của bản tin, [2026-10-26-ban-tin-thi-truong-design.md](2026-10-26-ban-tin-thi-truong-design.md)): có từ 17/05/2022; mỗi phiên một dòng tổng `VNINDEX` và các mã HOSE có giao dịch tự doanh (88 mã phiên 23/11/2026). VNDirect đăng chậm vài phiên và thiếu một số phiên (19/319 từ 13/8/2025).

## Cách làm

| | Cách | Được | Mất |
|---|---|---|---|
| **A (chọn)** | Lưu từng phiên, khoảng 1 năm; công cụ cộng dồn khi hỏi | Hỏi được 3, 6 tháng hay khoảng khác; xem được từng phiên của một mã | Lần đầu khoảng 250 lượt gọi |
| B | Lịch sử từ 2022 theo từng mã | Đủ lịch sử | Khoảng 400 lượt gọi, vẫn phải gộp theo phiên |
| C | Cộng dồn sẵn 60 và 120 phiên | Kho nhỏ nhất | Không hỏi khoảng khác, không xem từng phiên |

## Thiết kế

1. **Kho** `data/proprietary/<YYYY-MM-DD>.json`, mỗi phiên một tệp: `date`, `fetched_at`, `source`, `index` (mua, bán khối lượng và giá trị của dòng `VNINDEX`), `stocks` (mỗi mã HOSE loại STOCK: mua, bán khối lượng và giá trị), `khop` (tổng các mã có bằng dòng `VNINDEX` không). Số giữ nguyên đơn vị nguồn (đồng, cổ phiếu). Phiên VNDirect không có số: tệp `{"date", "thieu": true, "hoi_luc"}`.
2. **Tải** `proprietary-sync --limit 260` ở lượt 20:00: các phiên HOSE trong 400 ngày gần nhất (250 phiên mất khoảng 365 ngày, cộng phần VNDirect đăng chậm) (lịch `config/`, trước đó là phiên VN-Index của VNDirect như các công cụ khác), một lượt gọi mỗi phiên, cách nhau 0,5 giây, mới trước cũ sau. Phiên đã có số không tải lại. Phiên chưa có số trong 20 phiên gần nhất thì hỏi lại mỗi lượt (VNDirect đăng chậm); cũ hơn thì ghi thiếu một lần, không hỏi lại. Phiên đang giao dịch (trước 15:00) không hỏi. Xóa tệp cũ hơn 400 ngày. Số VNDirect để trống hay hỏng không lưu thành 0: mã đó bị loại khỏi phép cộng và ghi ở `bo_qua` (phiên đó `khop` sai); dòng `VNINDEX` thiếu số thì cả phiên là thiếu.
3. **Công cụ** `tu_doanh(so_phien=60, ma=None)`, `so_phien` từ 1 đến 250:
   - Khoảng: `so_phien` phiên HOSE kết thúc ở phiên mới nhất có số trong kho; trả phiên đầu, phiên cuối, số phiên chậm so với phiên HOSE gần nhất đã đóng cửa, danh sách phiên VNDirect không có số (`phien_thieu`) và phiên kho chưa tải (`chua_hoi`). `so_phien` là số phiên thật của khoảng, `so_phien_hoi` là số đã xin. Không lấy phiên khác thế vào.
   - Không có `ma`: tổng mua, bán, ròng (khối lượng, giá trị) của toàn sàn trong khoảng; 10 mã mua ròng và 10 mã bán ròng mạnh nhất theo giá trị, mỗi mã có mua, bán, ròng (giá trị và khối lượng) và số phiên có giao dịch tự doanh. Phiên có `khop` sai thì nêu tên.
   - Có `ma`: từng phiên của mã đó trong khoảng (phiên không có dòng của mã nghĩa là tự doanh không giao dịch mã đó, khác phiên thiếu số), và tổng cộng dồn.
   - Đơn vị: đồng và cổ phiếu, ghi trong `don_vi`; kèm `nguon`, `lay_luc`. Kho trống thì `thieu` kèm lý do.
4. Mô tả công cụ, hướng dẫn Project (`docs/claude-project-instructions.md`), skill `/dautu-thitruong` (thêm dòng tự doanh 60 phiên) sửa theo; plugin 0.21.0.

## Không làm

- Không đổi mục Tự doanh của bản tin.
- Không nhãn tốt hay xấu, không suy ra ý định của tự doanh.
- Không lưu chứng quyền (CW) hay chỉ số khác ngoài `VNINDEX`.
