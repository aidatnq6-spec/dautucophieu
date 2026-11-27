# Khối ngoại và tự doanh ròng 20 phiên trên Bản tin

Chủ sở hữu yêu cầu ngày 27/11/2026, kèm ảnh mẫu: hai dòng "Khối ngoại ròng" và "Tự doanh ròng", mỗi dòng có số ròng, tổng 20 phiên và 20 cột nhỏ. Chọn cách B (duyệt 27/11/2026, cả cách tính khối ngoại ròng bằng tổng các mã cổ phiếu): kho khối ngoại theo phiên từ VNDirect, như kho tự doanh.

## Cách làm

| | Cách | Được | Mất |
|---|---|---|---|
| A | Đọc ảnh chụp bản tin đã lưu | Không tải thêm | 1–3 cột trống trong 20 phiên; trộn số HOSE và VNDirect |
| **B (chọn)** | Kho `data/foreign/` theo phiên từ VNDirect `v4/foreigns` | 20 cột đủ, cùng nguồn, làm được công cụ MCP sau | Thêm một bước tải mỗi tối |

## Dữ liệu

- `data/foreign/<YYYY-MM-DD>.json` (`market/foreign_history.py`), cách làm giống `proprietary_history`: mỗi phiên một lượt gọi `foreigns?q=floor:HOSE~tradingDate:<ngày>`, giữ mã loại STOCK (mua, bán khối lượng và giá trị, đơn vị nguồn) và dòng `VNINDEX` nếu có; phiên không có dòng mã nào là thiếu (VNDirect phiên 24/11/2026 chỉ có dòng chỉ số). Số trống không lưu thành 0. Giữ 400 ngày; `foreign-sync --limit 260` ở lượt 20:00; phiên thiếu trong 20 phiên gần nhất hỏi lại.
- Khối ngoại ròng của một phiên = tổng các mã cổ phiếu (như mục Khối ngoại của bản tin hiện nay: phiên 26/11/2026 là −237,0 tỷ; dòng VNINDEX của VNDirect −186,9 tỷ và số HOSE −179,4 tỷ khác vì cách tính khác).
- Tự doanh ròng của một phiên = dòng `VNINDEX` của `data/proprietary/` (như mục Tự doanh và `tu_doanh`).

## Hiển thị

Trang Bản tin, mục thị trường, ngay trước "Khối ngoại", hai dòng:

```
Khối ngoại ròng                 −237,0 tỷ   ▁▂▇▁▃ … (20 cột)
Phiên 26/11 · 20 phiên −11.825 tỷ
Tự doanh ròng                   +357,5 tỷ   ▁▃▂▅▇ … (20 cột)
Phiên 23/11 (chậm 3 phiên) · 20 phiên +230 tỷ
```

- Số lớn: ròng của phiên mới nhất có số, không sau phiên của bản tin; xanh khi dương, đỏ khi âm. Dòng phụ: phiên của số (kèm số phiên chậm khi khác phiên bản tin) và tổng ròng của 20 phiên kết thúc ở phiên đó.
- 20 cột: 20 phiên HOSE kết thúc ở phiên của số, cột lên khi mua ròng (xanh), xuống khi bán ròng (đỏ), cùng một thang cho cả 20 cột của một dòng; phiên thiếu số để trống (không vẽ 0) và tổng ghi "(thiếu n phiên)". Di chuột lên cột hiện ngày và số ròng. Từ 27/11/2026: chạm vào cột (điện thoại) hiện ngày và số dưới dòng; mỗi cột có vùng chạm cao cả biểu đồ, kể cả phiên thiếu số ("thiếu số"); trình đọc màn hình đọc danh sách ẩn các phiên.
- Một dòng không có số thì ghi "chưa có số" kèm lý do. Bản tin Telegram không đổi.

## Không làm

- Không đổi số của mục Khối ngoại, Tự doanh hiện có; không đổi Telegram.
- Chưa làm công cụ MCP `khoi_ngoai` (để sau).
