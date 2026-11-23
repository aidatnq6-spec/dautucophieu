# Chất lượng tài sản ngân hàng từ báo cáo công khai: dự phòng, lãi dự thu và dự phòng đi vào lợi nhuận (chủ sở hữu duyệt 23/11/2026)

Phần ngân hàng tương ứng với khối Phải thu và Tồn kho (22/11/2026), vốn chỉ áp dụng cho mã phi tài chính. Chỉ dùng số liệu công khai của VNDirect
và thuyết minh Vietcap đã có (`market/bank_notes.py`), không gọi AI, không đoán số.

Hiện trạng: bảng Chất lượng tài sản (`domain/bank_figures.py`, `quality_trend`) và các cờ của nó (bao phủ giảm, nhóm 2 tăng nhanh, dự phòng không
theo kịp nợ xấu, lãi dự thu tăng nhanh) chỉ chạy trên các quý chủ sở hữu tự nhập. Quý chưa nhập thì không có cờ nào, dù nguồn công khai đã có số.

VNDirect (kiểm 23/11/2026, mẫu TT49, model 101/102): 412100 cho vay khách hàng (gốc), 412200 dự phòng rủi ro cho vay khách hàng (âm), 412520 các
khoản lãi, phí phải thu, 421100 thu nhập lãi và các khoản tương tự, 422900 chi phí dự phòng rủi ro tín dụng, 88888 lợi nhuận thuần trước chi phí
dự phòng. Ví dụ VCB Q3/2026: 1.816.093 / −31.168 / 11.811 / 40.015 / 6.184 / 17.402 tỷ đồng. Có ở ACB từ 2008, TCB từ 2011. Ở các quý cũ, nguồn
ghi 0 cho dòng chưa tách.

## 1. Đồng bộ thêm dòng ngân hàng
- Thêm `loans_gross` (412100), `loan_reserve` (412200), `accrued_interest` (412520), `interest_income` (421100) và `provision_expense` (422900)
  vào bố cục ngân hàng. `FIN_LINES_VERSION` lên 3, nên mỗi ngân hàng đọc lại toàn bộ lịch sử một lần, như các lần thêm dòng trước.
- Một ngân hàng không có số dư cho vay, dự phòng hay lãi dự thu bằng 0, nên **số 0 ở ba dòng số dư này được coi là thiếu** và ghi "nguồn ghi 0,
  coi là chưa có số". Chi phí dự phòng của một quý có thể bằng 0 thật, nên giữ nguyên.

## 2. Bảng Chất lượng tài sản chạy cả khi chưa nhập tay
- Mỗi quý ghép các phần sau:
  - dư nợ nhóm 1–5 lấy từ thuyết minh Vietcap, chỉ khi các nhóm cộng khớp tổng (quy tắc đang có);
  - dự phòng rủi ro cho vay (số dư, đổi dấu thành số dương) và lãi, phí phải thu lấy từ VNDirect.
- Số nhập tay vẫn thắng số tự lấy. Mỗi ô ghi nguồn: "Vietcap", "VNDirect" hoặc "số nhập tay".
- Dư nợ kinh doanh bất động sản và chiết khấu bộ chứng từ không có nguồn công khai, nên vẫn chỉ nhập tay. Thiếu thì để trống, kèm lý do.
- Các cờ và ngưỡng giữ nguyên như hiện có. Tổng nhóm 1–5 của Vietcap lệch quá 1% so với dòng 412100 của VNDirect thì ghi cả hai số, không chọn
  bên nào. Tăng trưởng cho vay vẫn tính từ tổng nhóm 1–5, như bây giờ.
- Ví dụ từ số công khai: lãi, phí phải thu của TCB tăng từ 11.376 lên 14.305 tỷ đồng (+25,7%) từ Q2 sang Q3/2026. Khi đã tự lấy số, quý này sẽ
  bật cờ lãi dự thu tăng nhanh đang có (từ 20% so với quý trước) mà không cần nhập tay.

## 3. Dự phòng đi vào lợi nhuận (ngân hàng)
- Mỗi quý hiện hai chỉ số: chi phí dự phòng so với lợi nhuận trước dự phòng (422900 / 88888); và **chi phí tín dụng**, tức chi phí dự phòng 4 quý
  gần nhất chia cho dư nợ bình quân (412100 cuối quý này và cuối cùng quý năm trước). Thiếu quý nào thì không tính, ghi quý thiếu.
- Cờ "Lợi nhuận đỡ bởi giảm trích lập": chi phí dự phòng của quý giảm từ 30% trở lên so với cùng quý năm trước, trong khi nợ nhóm 3–5 tăng so
  với quý trước. Nợ nhóm 3–5 chưa có số thì không bật cờ và ghi lý do.

## 4. Lãi dự thu so với thu nhập lãi
- Mỗi quý hiện lãi, phí phải thu so với thu nhập lãi của quý, đặt cạnh cùng quý năm trước.
- Cờ "Lãi dự thu tăng nhanh hơn thu nhập lãi": lãi dự thu tăng so với cùng kỳ nhanh hơn thu nhập lãi từ 20 điểm % trở lên.

## Nơi hiện
- Hồ sơ mã ngân hàng, khối Chất lượng tài sản (mục 2–4).
- Bảng dấu hiệu, như hai cờ Phải thu và Tồn kho. Cờ mới của một mã đang giữ chỉ báo một lần, trong lượt báo quý đang có.

## Ngoài phạm vi
- Công ty chứng khoán và bảo hiểm: hai mẫu báo cáo này cần spec riêng.
- Không quy đổi lãi dự thu ra số ngày lãi chưa thu, vì như vậy phải giả định một lãi suất.
- Không khuyến nghị mua bán.

## Đã làm (23/11/2026)
- Phần 1: bố cục ngân hàng trong `market/statements.py` có thêm 5 dòng; `zero_missing` cùng `quarters_zeros` và `years_zeros` ghi các số dư nguồn ghi 0. `FIN_LINES_VERSION` 3.
- Phần 2: `public_quarters`, `merged_quarters` (`domain/bank_figures.py`); route trả `quality` (quý mới nhất, nguồn từng ô, ghi chú); bảng nhập tay giữ nguyên.
- Phần 3: `provision_view`; route trả `provision`; dấu hiệu `provision_cut` trên Bảng dấu hiệu.
- Phần 4: `accrued_view`; route trả `accrued`; dấu hiệu `accrued_outpace`.
- Bảng dấu hiệu chỉ dùng số công khai. Mỗi ngân hàng là một dòng, chỉ xét dấu hiệu ngân hàng, và không bị ghi thiếu các dấu hiệu phi tài chính.
- Báo mã đang giữ qua `check_signs` có sẵn, một lần khi dấu hiệu mới bật. Tiêu đề tin vẫn là "Dấu hiệu phải thu mới".

## Thứ tự
1 → 2 → 3 → 4, mỗi phần một nhánh, TDD, verify rồi merge. Các ngưỡng 30% (mục 3) và 20 điểm % (mục 4) do chủ sở hữu chốt ngày 23/11/2026.
