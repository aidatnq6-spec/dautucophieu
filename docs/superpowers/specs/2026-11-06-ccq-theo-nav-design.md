# Chứng chỉ quỹ theo số đơn vị × NAV công khai (06/11/2026)

Việc sau thứ hai của [Sổ tài sản](2026-11-05-so-tien-gui-design.md). Chủ sở hữu chọn (06/11/2026): nguồn Fmarket; ô số tiền của
dòng là vốn đã mua lúc đầu và vẫn giữ. Hiện mỗi dòng trong "Trái phiếu và chứng chỉ quỹ" là một số tiền nhập
tay, nên giá trị đứng yên dù NAV thay đổi mỗi kỳ. Với dòng là chứng chỉ quỹ, chủ sở hữu nhập mã quỹ và số đơn vị đang có; giá trị = số đơn
vị × NAV/đơn vị mới nhất đã công bố, kèm ngày định giá.

## Nguồn NAV
- **Fmarket** (`api.fmarket.vn/res/products/filter`): một lần gọi trả về khoảng 70 quỹ mở, mỗi quỹ có NAV/đơn vị và ngày định giá
  (`lastNAVDate`). robots.txt của host API trả 401; theo RFC 9309, mã 4xx nghĩa là không có giới hạn. Đây là nền tảng phân phối, không phải
  công ty quản lý quỹ, nên trang ghi rõ "NAV theo Fmarket, kỳ dd/mm/yyyy".
- Kiểm tra ngày 06/11/2026: VFF, VIBF và DCBF đều có NAV kỳ 05/11/2026.
- Phương án thay thế (không chọn): file Excel NAV từng kỳ trên trang VinaCapital (cho phép theo robots.txt), và trang Dragon Capital (cho
  phép); mỗi công ty một định dạng, phải đọc từng quỹ.

## Đồng bộ
- Lệnh `fund-nav-sync` chạy trong mỗi lượt sau giờ đóng cửa: một lần gọi cho mọi quỹ; không gửi dữ liệu cá nhân nào (không gửi mã quỹ
  đang giữ). Lưu `data/fund-nav.json`: mã, tên quỹ, NAV/đơn vị, ngày định giá, nguồn, giờ tải (chỉ dữ liệu công khai).
- Nguồn lỗi hoặc trả về rỗng thì giữ bản cũ, không ghi đè bằng kết quả trống; quỹ không còn trong danh sách thì giữ số cũ kèm ngày cũ.

## Sổ tài sản
- Dòng Trái phiếu và chứng chỉ quỹ có thêm hai ô tùy chọn: **Mã quỹ** (ví dụ VFF) và **Số đơn vị** (tối đa 2 chữ số thập phân, như số dư
  trên app). Có cả hai thì dòng được tính theo NAV; không có ô nào thì dòng dùng số tiền nhập tay như trước.
- Có mã quỹ thì phải có số đơn vị, và ngược lại (nhập một ô thì báo lỗi).
- Ô số tiền của dòng đổi tên thành **Vốn đã mua (đ)**: số tiền đã bỏ ra lúc mua, vẫn bắt buộc.
- Dòng theo NAV hiện: số đơn vị × NAV = giá trị hiện tại, làm tròn đến đồng, kèm "NAV <mã> kỳ dd/mm/yyyy (Fmarket)", và chênh lệch so với vốn
  đã mua (đồng và %), là phép trừ hai số trên, không ước lượng. NAV cũ hơn 14 ngày thì ghi "NAV đã cũ".
- Chưa có NAV cho mã đó (mã sai, chưa đồng bộ lần nào): dòng tính bằng vốn đã mua và ghi "chưa có NAV cho <mã>, đang tính bằng vốn đã mua".
  Không ước lượng NAV.
- Tháp tài sản và Dòng tiền thụ động dùng giá trị theo NAV (lợi suất từng dòng vẫn như cũ).

## Ngoài phạm vi
Tự lấy số đơn vị từ app MiO hay DragonX; lịch sử NAV; giá vốn bình quân khi mua nhiều lần (vốn đã mua là tổng do chủ sở hữu nhập); vàng và tiền số theo giá công khai (việc 3, 4).
