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

## Cải tiến chủ sở hữu duyệt 21/11/2026
1. Đường nhỏ của mỗi đèn vẽ đúng thứ đèn đo theo từng ngày trong 30 ngày (mức đổi 30 ngày của dầu, USD; khoảng chênh tỷ giá; số phiên
   bán ròng liên tiếp; lãi suất qua đêm), kèm đường ngưỡng vàng và đỏ.
2. Mỗi đèn ghi khoảng cách tới mức kế tiếp (ví dụ "còn 0,81 điểm % nữa là đỏ", "thêm 1 phiên bán ròng là vàng").
3. Dòng tóm tắt đầu khối: số đèn xanh, vàng, đỏ (và chưa có số, số cũ nếu có).
4. Mỗi đèn ghi ở mức hiện tại từ ngày nào, tính lại từ số đã lưu theo từng ngày; cả 30 ngày cùng mức thì ghi "ít nhất từ" ngày đầu.
5. Dầu WTI thêm chiều giảm: vàng khi giảm từ 15%, đỏ khi giảm từ 25% trong 30 ngày (giảm mạnh thường báo kinh tế thế giới yếu đi).
   USD không thêm chiều giảm.
6. Tên đèn dẫn tới dòng chỉ số gần nhất trên bảng Vĩ mô (dầu → WTI, USD → DXY, tỷ giá → tỷ giá tự do, khối ngoại, lãi suất qua đêm).

## Telegram
- Sau mỗi lượt cập nhật vĩ mô: so mức với lượt trước (`data/macro/_signals.json`); đèn đổi giữa xanh, vàng, đỏ thì gửi một tin gồm
  mọi đèn đã đổi. Lượt đầu chỉ ghi mức. Chuyển sang hoặc từ "chưa có số", "số cũ" không gửi.
- Chỉ gửi khi đã bật gửi theo lịch, như các nhắc khác.
- Gửi chung với Nhắc thanh khoản và tỷ giá (chủ sở hữu chọn 21/11/2026): một bước `macro-alerts` ngay sau lượt cập nhật vĩ mô soạn cả
  hai phần và gửi một tin gồm phần nào đang có, kèm một dòng "không phải khuyến nghị". Mỗi phần giữ trạng thái riêng; tin không gửi được
  thì cả hai phần giữ nguyên để lượt sau gửi lại. Lệnh `macro-signals` và `liquidity-alerts` vẫn chạy tay được, lịch không gọi nữa.

## Không làm
- Không đổi điều kiện của Nhắc thanh khoản và tỷ giá (liên ngân hàng nhảy vọt, tỷ giá sát trần): hai việc đo khác nhau; chỉ gửi chung.
