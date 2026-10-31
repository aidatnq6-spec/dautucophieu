# Định giá dự phóng theo kịch bản, và dải ±2/±3 độ lệch chuẩn

Ngày: 31/10/2026 · Trạng thái: chủ sở hữu chọn làm (thay sheet "Định giá PE", "Định giá PB" trong Excel phân tích doanh nghiệp)

## Mục tiêu

Trên trang hồ sơ mã: chủ sở hữu tự đặt tăng trưởng lợi nhuận và vốn chủ cho 1–3 năm tới (và mức pha loãng cổ phiếu nếu có); phần mềm tính EPS, BVPS dự phóng và giá tương ứng ở P/E, P/B trung vị ±1, ±2, ±3 độ lệch chuẩn, so với giá hiện tại. Kèm ô "Giả sử P/E (P/B) = … thì giá là …". Đây là kịch bản của chủ sở hữu, không phải dự báo của phần mềm hay khuyến nghị.

## Số nền (không đoán)

- Năm gốc = năm tài chính gần nhất có lợi nhuận công ty mẹ và vốn chủ (báo cáo đã lưu). Số cổ phiếu hiện tại như phần định giá tham khảo (lợi nhuận / EPS năm gần nhất và các đợt phát hành sau đó).
- P/E, P/B theo tháng như biểu đồ P/E lịch sử: trung vị và độ lệch chuẩn của chuỗi tháng. Bội số = trung vị + k × độ lệch chuẩn, k ∈ {−3…3}; bội số ≤ 0 thì ô đó "không áp dụng".
- Thiếu số nền thì báo lý do, không tính.

## Cách tính

EPS năm gốc + i = lợi nhuận năm gốc × Π(1 + g lợi nhuận) / (số cổ phiếu × Π(1 + pha loãng)); BVPS tương tự với vốn chủ. Giá = EPS (BVPS) × bội số. Chênh lệch = giá / giá hiện tại − 1. Giả định tăng trưởng từ −90% đến +300% mỗi năm, pha loãng 0–100%.

Giả định lưu ở kho cá nhân (`settings/forward_<MÃ>`, có lịch sử phiên bản), mỗi mã một bộ.

## Biểu đồ P/E, P/B lịch sử

Thêm đường ±2 và ±3 độ lệch chuẩn (nét đứt nhạt) bên cạnh dải ±1 sẵn có; dòng chú thích ghi giá trị các mức. Mức âm không vẽ.
