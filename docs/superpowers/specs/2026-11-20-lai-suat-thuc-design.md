# Lợi suất thực của Mỹ và lãi suất tiền gửi thực (20/11/2026)

Chủ sở hữu chọn ngày 20/11/2026: mục 1 và 2 trong các đề xuất từ bài phân tích giá vàng. Hai dòng mới trên trang Vĩ mô đo chi phí cơ hội của
việc giữ tài sản không sinh lời như vàng. Chỉ dữ liệu công khai; không đọc danh mục, không gọi AI.

## Lợi suất thực trái phiếu 10 năm của Mỹ (`us10y_real`)
- Đường lợi suất thực (TIPS) do Bộ Tài chính Mỹ công bố cuối mỗi ngày giao dịch, cột "10 YR" (`daily_treasury_real_yield_curve`, cùng tệp
  CSV với đường danh nghĩa của `us10y`; robots.txt cho phép, kiểm tra 20/11/2026). Không đọc được thì lấy FRED `DFII10`, chậm 1–2 ngày.
- Đơn vị %; quá 7 ngày là cũ. Tăng là "Xấu", như lợi suất danh nghĩa.

## Lãi suất tiền gửi 12 tháng thực (`vn_real_deposit`)
- Bằng lãi suất tiền gửi VND 12 tháng (`deposit_12m`) trừ thẳng lạm phát Việt Nam so cùng kỳ của tháng mới nhất (`vn_cpi_yoy`), làm tròn
  2 chữ số. Không dùng công thức Fisher, để người đọc tự trừ lại được.
- Chỉ tính khi cả hai số đã có và còn mới theo nhịp của chính chúng (tiền gửi 45 ngày, CPI 40 ngày). Thiếu hoặc cũ thì không tính, không
  lấy số cũ hơn: dòng hiện "Lỗi nguồn lần gần nhất", và ghi chú của dòng nêu điều kiện này.
- Tính mỗi lượt cập nhật, sau khi đã lấy hai số trong lượt đó (thứ tự trong cấu hình); mỗi ngày giữ số cuối. Đơn vị %/năm; quá 45 ngày
  là cũ. Tăng là "Xấu", như lãi suất tiền gửi.

## Không làm
- Không thêm dự báo hay ngưỡng "đắt, rẻ" cho vàng; không đổi Tháp tài sản hay Chuỗi tác động vĩ mô.
