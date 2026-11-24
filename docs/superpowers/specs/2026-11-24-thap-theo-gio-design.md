# Hình tháp theo giỏ (24/11/2026)

Chủ sở hữu chọn ngày 24/11/2026. Ghép hai phần của spec 2026-11-24-thap-mua-va-gio-chien-luoc-design.md: Soi hình tháp khi mua thêm (Hậu
kiểm) và Giỏ chiến lược. Mục đích là thấy kiểu "mua đuổi" (Tháp ngược) hay xảy ra ở cách đánh nào. Dữ liệu cá nhân, tính trên máy, không
gửi cho AI. Chỉ đếm hình dạng đã xảy ra, không chấm điểm, không khuyến nghị.

## Cách tính
- Dùng đúng các dòng hình tháp của Hậu kiểm (`pyramids`): đợt nắm có từ 2 lần mua trở lên, nhãn Tháp xuôi / Tháp ngược / Xen kẽ như spec gốc.
  Nhãn ở hai nơi luôn khớp nhau.
- Mỗi đợt thuộc giỏ đang gắn cho đợt đó (nhãn không còn khớp đợt nào thì tính vào "Chưa gắn giỏ", như Kết quả theo giỏ).
- Mỗi giỏ (và "Chưa gắn giỏ"):
  - số đợt mỗi nhãn;
  - số đợt chưa so được (thiếu giá ngày mua, hoặc đợt bắt đầu từ số dư đầu kỳ);
  - phần tiền bình quân bỏ vào ở mức giá cao hơn lần mua đầu, chỉ khi giỏ có từ 5 đợt so được; dưới 5 đợt thì ghi "chưa đủ 5 đợt".
- Đợt chỉ mua một lần không có hình tháp và không được đếm.

## Giao diện
- Bảng "Kết quả theo giỏ" trên trang Danh mục & Giao dịch có thêm cột "Hình tháp", ví dụ: "2 xuôi · 1 ngược · 0 xen kẽ · 1 chưa so được ·
  chưa đủ 5 đợt". Giỏ không có đợt nào mua từ 2 lần trở lên thì ghi "chưa có đợt mua thêm".
- Câu giải thích nói các nhãn lấy từ Hậu kiểm, trang Nhật ký.

## Không làm
- Không thêm nhắc Telegram, không đổi Hậu kiểm.

## Đã làm (24/11/2026)
- `basket_view(..., pyramids=)` thêm `pyramid` cho mỗi giỏ (`_shapes` dùng chung với tổng kết của Hậu kiểm); `baskets_for` đọc giá đã lưu.
- Cột "Hình tháp" ở bảng Kết quả theo giỏ (`basketPyramid`).
