# So sánh cùng ngành

Duyệt 08/11/2026 (chủ sở hữu). Trước đó phần mềm không có bảng đặt chỉ số của nhiều mã cùng ngành cạnh nhau: Định giá lọc được theo
ngành nhưng chỉ có giá, giá hợp lý, chênh lệch, kết luận và chất lượng; trang từng mã có đủ chỉ số nhưng của một mã.

## Vị trí

Khối "So sánh cùng ngành" trên trang từng mã (`/research/<MÃ>`, neo `#so-sanh-cung-nganh`), ngay sau Bảng số tài chính: mọi mã cùng ngành
ICB cấp 2 trong danh sách theo dõi, mã đang xem tô đậm, mỗi mã dẫn tới trang của nó. Trang Định giá, khi chọn một ngành, có liên kết
"So sánh ngành này" tới khối này trên trang mã đầu tiên của ngành. Ngành chỉ có 1 mã theo dõi: ghi "Chỉ có 1 mã ngành … trong danh sách
theo dõi", không có bảng.

## Cột

| Nhóm | Cột |
|---|---|
| Doanh nghiệp thường | Vốn hoá, P/E, P/B, EV/EBITDA, ROE, biên gộp, doanh thu và LNST mẹ so cùng kỳ, vay / vốn chủ, F-Score, giá so với giá hợp lý |
| Ngân hàng | Vốn hoá, P/B, P/E, ROE, ROAA, NIM, NPL, nợ nhóm 2, bao phủ nợ xấu, CASA, LDR, tăng trưởng cho vay, CAR cuối năm, Điểm sức khỏe, giá so với giá hợp lý |
| Chứng khoán | Vốn hoá, P/B, P/E, ROE, ROAA, biên lợi nhuận ròng, cho vay / vốn chủ, Điểm sức khỏe, giá so với giá hợp lý |
| Bảo hiểm | Vốn hoá, P/B, P/E, ROE, ROAA, tỷ lệ kết hợp, biên lợi nhuận ròng, Điểm sức khỏe, giá so với giá hợp lý |

Mọi số là số trang của mã đã có, không nguồn mới, không AI: Bảng số tài chính theo quý (định giá tại giá cuối quý, 4 quý gần nhất),
chỉ số ngành VNDirect, nợ nhóm 2, CASA và CAR cuối năm từ Vietcap (số nhập tay ưu tiên), và bảng Định giá hôm nay cho F-Score / Điểm
sức khỏe và giá so với giá hợp lý (giá / giá hợp lý − 1; âm là rẻ hơn). "Vay / vốn chủ" của doanh nghiệp thường (nợ vay ngắn và dài hạn
trên vốn chủ sở hữu gồm phần không kiểm soát, như công ty chứng khoán) được thêm vào nhóm Quy mô và định giá của Bảng số tài chính.

## Quy tắc

- Kỳ so sánh mặc định là quý gần nhất mà mọi mã có số liệu đều có; chọn được quý khác (quý có ít nhất 2 mã). Mã thiếu quý đang chọn để trống
  và ghi "Chưa có số Qn/yyyy"; không lấy quý khác bù vào. Mã chưa có số liệu nào ghi "Chưa có số liệu (đồng bộ lúc 20:00)". CAR là số cuối
  năm gần nhất trước quý (Q4 thì chính năm đó).
- Mỗi cột có chiều: thấp là tốt (P/E, P/B, EV/EBITDA, vay / vốn chủ, NPL, nợ nhóm 2, tỷ lệ kết hợp, cho vay / vốn chủ, giá so với giá hợp
  lý), cao là tốt (ROE, ROAA, NIM, biên, tăng trưởng, bao phủ, CASA, CAR, điểm), hoặc không xếp hạng (Vốn hoá, LDR). Cột có từ 2 số trở lên:
  ô tốt nhất xanh, kém nhất đỏ; điểm so theo tỷ lệ tiêu chí đạt (6/9 hơn 4/7).
- Dòng "Trung vị ngành" cho mỗi cột số. "Đứng nhóm đầu" = số cột xếp hạng mà mã nằm trong 1/3 tốt nhất (làm tròn lên), trên số cột xếp
  hạng có số.
- Không có điểm tổng: trọng số giữa các cột là nhận định của người dùng, phần mềm không chọn thay và không gợi ý mua.
- Sắp xếp theo cột (lần bấm đầu đưa đầu tốt lên trên), biểu đồ thanh của một cột.
- API: `GET /internal/fairvalue/peers/<MÃ>` và `/<MÃ>/<yyyy-Qn>` (kỳ là một đoạn đường dẫn vì proxy web không chuyển chuỗi truy vấn). Bảng
  Định giá được tính không đánh dấu mã đang nắm.
