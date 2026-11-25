# EPS: trên mỗi cổ phiếu, pha loãng (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (cả ba bước của đề xuất). Kaizen từ bài "Lãi cơ bản trên cổ phiếu" (VNM 2020): tử số là LNST công ty mẹ trừ quỹ khen
thưởng, phúc lợi; mẫu số là cổ phiếu bình quân gia quyền; xem rủi ro pha loãng. Đối chiếu VNDirect: VNM 2020 LNST 11.235,7, LNST công ty mẹ 11.098,9
(khớp); EPS 2019 VNDirect 5.478 đ (bài 4.565 = 5.478 ÷ 1,2, đã điều chỉnh theo cổ phiếu thưởng 20% năm 2020), EPS 2020 4.770 đ (bài ghi 4.000: chưa
rõ nguồn). EPS suy giảm (700087) thường để trống. Dữ liệu công khai và số chủ sở hữu nhập, không gọi AI.

## 1. Bảng số tài chính, nhóm "Trên mỗi cổ phiếu" (sau Thuế TNDN)
- Thêm dòng 13343 trái phiếu chuyển đổi, 14149 quyền chọn chuyển đổi trái phiếu (tên kiểm ngày 25/11/2026); `LINES_VERSION` lên 14.
- **EPS cơ bản (báo cáo)**: số doanh nghiệp công bố (23001), không điều chỉnh lại khi sau đó có cổ phiếu thưởng.
- **LNST công ty mẹ ÷ cổ phiếu cuối kỳ** (vốn góp ÷ 10.000 đ; số của kỳ).
- **EPS báo cáo ÷ phần tự tính**: thấp hơn 1 khi trừ quỹ khen thưởng, phúc lợi hoặc phát hành trong kỳ. 42 mã: trung vị 0,98; 6 mã dưới 0,9.
- **Trái phiếu chuyển đổi** (số dư).

## 2. Dấu hiệu "Có thể bị pha loãng" (Chất lượng báo cáo, sau "Thuế suất thực tế thấp")
Bản ghi cơ bản lấy thêm hai dòng trên. Bật khi năm gần nhất có trái phiếu chuyển đổi hoặc quyền chọn chuyển đổi dương. 42 mã: 1 mã bật.

## 3. Pha loãng nhập tay (khối Thuyết minh, khóa `dilution`)
Tối đa 10 nguồn: tên (ESOP, trái phiếu chuyển đổi, phát hành theo nghị quyết) và số cổ phiếu (số nguyên dương). Phần mềm tính EPS trên LNST công ty mẹ 4
quý gần nhất và số cổ phiếu cuối quý đó (báo cáo đã lưu), và EPS khi cộng thêm số cổ phiếu bạn ghi (giả định lợi nhuận không đổi, ghi rõ không phải
dự báo); thiếu một quý: để trống. Ghi phần khác không gửi `dilution` thì giữ nguyên.
