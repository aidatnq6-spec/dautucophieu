# Đèn tín hiệu rủi ro vĩ mô (21/11/2026)

Chủ sở hữu duyệt ngưỡng ngày 27/10/2026 (bản dở trên nhánh `feat/macro-signals`) và chọn ngày 21/11/2026 làm lại trên `main`. Năm đèn
trên trang Vĩ mô, tính từ số đã lưu; một tin Telegram khi một đèn đổi mức. Chỉ mô tả dữ liệu, không khuyến nghị; không đọc danh mục.

## Năm đèn (vàng / đỏ)
| Đèn | Đo | Vàng | Đỏ | Số quá cũ sau |
|---|---|---|---|---|
| Giá dầu WTI | đổi trong 30 ngày (`factor_oil`) | ≥ +10% | ≥ +20% | 10 ngày |
| Đồng USD (chỉ số rộng của Fed) | đổi trong 30 ngày (`factor_usd`) | ≥ +2% | ≥ +4% | 14 ngày |
| Tỷ giá tự do so với Vietcombank | giá bán tự do cao hơn Vietcombank, cùng ngày | ≥ 1% | ≥ 2% | 7 ngày |
| Khối ngoại | số phiên bán ròng liên tiếp (`foreign_net`) | ≥ 5 | ≥ 10 | 7 ngày |
| Lãi suất liên ngân hàng qua đêm | mức mới nhất (`vn_interbank_on`) | ≥ 5%/năm | ≥ 7%/năm | 7 ngày |

- Mỗi đèn đọc số mới nhất của chính nó. Mức đổi 30 ngày so với số gần nhất cách ít nhất 30 ngày; chưa có thì đèn ghi "chưa có số".
- Số mới nhất cũ hơn hạn ở cột cuối thì đèn ghi "số cũ" kèm ngày, không tô màu (không đoán số).
- Đèn có thêm đường 30 ngày của chính thứ nó đo; dưới 30 ngày số liệu thì ghi tính từ ngày nào.

## Telegram
- Sau mỗi lượt cập nhật vĩ mô: so mức với lượt trước (`data/macro/_signals.json`); đèn đổi giữa xanh, vàng, đỏ thì gửi một tin gồm
  mọi đèn đã đổi. Lượt đầu chỉ ghi mức. Chuyển sang hoặc từ "chưa có số", "số cũ" không gửi.
- Chỉ gửi khi đã bật gửi theo lịch, như các nhắc khác.

## Không làm
- Không đổi Nhắc thanh khoản và tỷ giá (liên ngân hàng nhảy vọt, tỷ giá sát trần): hai việc đo khác nhau, đèn chỉ báo khi đổi mức.
