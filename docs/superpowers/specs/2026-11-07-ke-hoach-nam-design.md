# Kế hoạch năm ĐHCĐ (07/11/2026)

Từ ảnh bảng số HPG (thẻ "DT lũy kế Q3/2026 · % kế hoạch", "LNST lũy kế · % kế hoạch"). Chủ sở hữu nhập kế hoạch doanh thu và lợi nhuận
từng năm cho từng mã kèm nguồn; ứng dụng tính % hoàn thành lũy kế từ số quý VNDirect ([Bảng số tài chính](2026-11-07-bang-so-tai-chinh-design.md))
và hiện thành thẻ ở đầu khối Bảng số tài chính trên trang hồ sơ mã. Không gọi AI, không đọc danh mục.

## Lưu và nhập
- Kho cá nhân `settings/annual_plan_<MÃ>` (ghi có phiên bản, mã yêu cầu như Số liệu ngân hàng): theo năm, doanh thu và lợi nhuận (tỷ đồng,
  > 0, có thể chỉ một trong hai), loại lợi nhuận (LNST hợp nhất, LNST công ty mẹ hoặc LNTT, vì mỗi công ty đặt kế hoạch theo một dòng), **nguồn
  bắt buộc** (ví dụ "Nghị quyết ĐHCĐ 2026, ngày họp"). Chỉ mã trong danh sách theo dõi.
- API: `GET /internal/annual-plans/{mã}`, `PUT /internal/annual-plans/{mã}/{năm}`, `POST /internal/annual-plans/{mã}/{năm}/delete`.

## Tính (`domain/annual_plans.py`)
- Doanh thu so với doanh thu thuần; lợi nhuận so với dòng đã chọn. Lũy kế = cộng các quý VNDirect của năm từ quý 1; gặp quý thiếu dòng đó thì
  dừng và ghi "Thiếu … quý n: chỉ cộng tới quý n−1"; chưa có quý 1 thì ghi "Chưa có số quý 1/năm". Không ước lượng phần còn lại của năm.
- Mã chưa có số VNDirect (ngân hàng, chứng khoán, bảo hiểm, mã chưa đồng bộ) vẫn lưu được kế hoạch; % để trống với lý do.

## Giao diện
- Hai thẻ cho năm mới nhất có kế hoạch: "DT lũy kế Qn/năm · % kế hoạch" (ví dụ 81,1% · 170.274 / KH 210.000 tỷ) và tương tự cho lợi nhuận.
- Mục "Kế hoạch năm (ĐHCĐ)": danh sách các năm đã nhập kèm nguồn và nút Xóa; biểu mẫu Năm, Doanh thu, Lợi nhuận, Loại lợi nhuận, Nguồn.

## Tự lấy từ CafeF (07/11/2026, chủ sở hữu hỏi "cào số tự động")
- Không có nguồn kế hoạch trong API VNDirect. CafeF có dữ liệu công khai của trang mã: `cafef.vn/du-lieu/Ajax/PageNew/KeHoachKinhDoanh.ashx?Symbol=<mã>`
  (robots.txt của cafef.vn cho phép mọi bot, kiểm 07/11/2026). Chỉ có **năm hiện tại** (bỏ qua tham số năm), nên mỗi năm đã đọc được giữ lại.
- Số ghi bằng tỷ ("210.000 tỷ", "48.660,13 tỷ") được đọc; "N/A" và kế hoạch ghi bằng lời (ngân hàng: "Tăng ~10%") giữ nguyên văn, không đổi thành số.
  Có doanh thu, LNTT, LNST tuỳ mã (HPG, MWG chỉ LNST; FPT chỉ LNTT; PNJ cả hai).
- `plans-sync`: lượt 20:00, mỗi mã đang theo dõi một lượt gọi, làm mới sau 7 ngày; `data/annual-plans-cafef/<mã>.json` (dữ liệu công khai).
- Năm bạn chưa nhập: dùng kế hoạch CafeF (lợi nhuận = LNST nếu có, không thì LNTT), ghi "theo CafeF (Kế hoạch kinh doanh), đọc ngày…" và gợi ý
  nhập số của bạn để thay. Năm bạn đã nhập: số của bạn luôn thắng. Kế hoạch theo CafeF không có nút Xóa.

