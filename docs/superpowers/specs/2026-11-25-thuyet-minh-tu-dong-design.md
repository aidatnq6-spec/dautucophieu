# Thuyết minh tự động từ Vietcap cho doanh nghiệp thường (25/11/2026)

Chủ sở hữu chọn ngày 25/11/2026 (bước 1 và 2 của đề xuất "tự động thay nhập tay"). Nguồn: API IQ công khai của Vietcap
(`iq.vietcap.com.vn/api/iq-insight-service/v1/company/{mã}/financial-statement?section=NOTE`), nguồn chủ sở hữu đã duyệt ngày 08/11/2026 cho thuyết
minh ngân hàng ([Bảng số tài chính](2026-11-07-bang-so-tai-chinh-design.md), `bank-notes-sync`). Danh mục 157 mục thuyết minh doanh nghiệp đọc từ
`financial-statement/metrics` (mục NOTE) ngày 25/11/2026. Dữ liệu công khai, không gọi AI, không đoán số.

## Đối chiếu (25/11/2026)
HPG 2021 trên Vietcap: vay ngắn hạn theo hợp đồng 37.547,0 (bài nợ vay: 37.547), vay dài hạn đến hạn trả 6.200,6 (bài: 6.200), lãi tiền gửi và cho vay
1.194,4 (bài doanh thu tài chính: 1.194), lãi tỷ giá chưa thực hiện 46,6 (bài: 46), nguyên giá TSCĐ hữu hình đầu năm 82.616,6 (khớp VNDirect). NVL: các mục
tăng, giảm lợi thế thương mại để 0 dù có biến động, nên không dùng phần lợi thế thương mại. Vietcap có 8 năm, 35 quý.

## Lấy dữ liệu (`market/company_notes.py`, lệnh `company-notes-sync`)
- Mỗi mã doanh nghiệp thường trong danh sách theo dõi (ngân hàng, chứng khoán, bảo hiểm: không) một lần gọi, **cách 10 giây** (Crawl-delay), kể cả lần
  gọi đầu (bước chạy ngay sau `bank-notes-sync`, cũng gọi Vietcap), dưới tên ứng dụng; làm mới mỗi mã tối đa một lần một tuần; **tối đa 15 mã mỗi
  lượt** (bước bị giới hạn 10 phút), mã cũ nhất trước. Bị từ chối hay lỗi thì dừng cả lượt, mã còn lại chờ lượt sau. Lượt 20:00, sau `bank-notes-sync`.
- Giữ theo năm và quý (tỷ đồng → đồng như nguồn), chỉ các mục dưới đây; số thiếu bỏ qua. `data/company-notes/<MÃ>.json`.
  - **Vay**: vay ngắn hạn theo hợp đồng (noc66), vay dài hạn đến hạn trả (noc67), vay dài hạn ngân hàng (noc94), đối tượng khác (noc95), trái phiếu phát
    hành (noc96), thuê tài chính (noc97).
  - **Doanh thu tài chính**: lãi tiền gửi, cho vay (noc123), lãi trái phiếu, kỳ phiếu (noc124), cổ tức (noc125), lãi thanh lý đầu tư (noc155), lãi bán
    ngoại tệ (noc126), lãi tỷ giá đã thực hiện (noc127), chưa thực hiện (noc128), khác (noc130).
  - **Chi phí tài chính**: lãi tiền vay (noc132), lỗ thanh lý đầu tư (noc134), lỗ tỷ giá đã thực hiện (noc136), chưa thực hiện (noc137), dự phòng giảm giá
    đầu tư (noc138), khác (noc139).
  - **TSCĐ hữu hình**: nguyên giá đầu kỳ, tăng, giảm trong kỳ (noc36–38); hao mòn tăng trong kỳ (noc41).

## Hiện ở hồ sơ mã (khối Thuyết minh TSCĐ, mục "Tự động từ thuyết minh (Vietcap)")
5 năm gần nhất, chỉ đọc, ghi ngày đọc và nguồn:
- **Vay theo loại**: các dòng trên, tổng; **vay dài hạn đến hạn trả** đặt cạnh số bạn ghi ở Các khoản vay (nếu có, kỳ đó), khác nhau thì hiện cả hai.
- **Doanh thu, chi phí tài chính theo loại**; **phần khó lặp lại hoặc chưa thu tiền (tự động)** = lãi thanh lý đầu tư + lãi tỷ giá chưa thực hiện, so
  với LNTT của báo cáo đã lưu (không tách được lãi cho bên liên quan vay: Vietcap gộp lãi tiền gửi và cho vay).
- **Biến động TSCĐ hữu hình**: nguyên giá đầu năm, tăng, giảm trong năm (tăng gồm mua mới và kết chuyển XDCB, Vietcap không tách).
Phần nhập tay giữ nguyên.

## Dấu hiệu "XDCB dở dang vừa kết chuyển" dùng số tăng trong năm
Bản ghi cơ bản lấy thêm **nguyên giá TSCĐ hữu hình tăng trong năm** (noc37) khi có thuyết minh Vietcap. Điều kiện "nguyên giá tăng ít nhất một nửa phần
XDCB giảm" dùng số tăng này thay cho chênh lệch nguyên giá cuối năm (chênh lệch bị trừ bớt phần thanh lý, giảm); chưa có thuyết minh thì giữ cách cũ.
Phần chi tiết ghi rõ số nào được dùng.
