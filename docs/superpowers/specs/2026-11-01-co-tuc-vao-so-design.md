# Cổ tức và quyền vào sổ; thuế và phí theo năm

Ngày: 01/11/2026 · Trạng thái: chủ sở hữu chọn "làm luôn" (không hỏi đáp); các lựa chọn dưới đây là quyết định của người làm, duyệt khi xem PR.

## Vì sao
Cổ tức tiền và cổ phiếu thưởng chưa ghi vào sổ làm lệch giá vốn, lãi lỗ, dòng tiền thụ động, điều kiện "Lỗ so với giá vốn" của
Luận điểm đầu tư và Hậu kiểm. Lịch sự kiện đã có ngày GDKHQ của các mã theo dõi, nên phần mềm soạn sẵn dòng sổ để chủ sở hữu xác nhận.

## Quy tắc (theo docs/decisions/market-rules.md)
- Sổ ghi số thực tế theo chứng từ. Phần mềm chỉ **soạn sẵn**; chủ sở hữu xem, sửa theo chứng từ rồi bấm "Ghi vào sổ". Không tự ghi.
- Số cổ phiếu hưởng quyền = số cổ phiếu trong sổ từ các giao dịch trước ngày GDKHQ (mua đúng ngày GDKHQ không được hưởng; bán đúng ngày
  GDKHQ vẫn được hưởng), tính cả cổ phiếu thưởng chưa về như phép kiểm của sổ. Bằng 0 thì không gợi ý.
- Cổ tức tiền: gộp = số cổ phiếu × giá trị mỗi cổ phiếu theo nguồn (đ/cp); thuế dự kiến = 5% (`config/market-rules-hose.json`,
  `dividend_tax_rate`), làm tròn đồng. Dòng quyền ghi vào ngày trước GDKHQ (số cổ phiếu lúc đó là số được hưởng, kể cả khi bán trong ngày GDKHQ);
  ngày chốt và ngày thanh toán theo nguồn — nguồn thiếu ngày chốt thì để trống cho chủ sở hữu điền theo chứng từ.
- Khi đã có quyền mà chưa có dòng nhận tiền và đã qua ngày thanh toán: gợi ý "Nhận cổ tức tiền" (thực nhận = gộp − thuế dự kiến).
- Cổ phiếu thưởng/cổ tức bằng cổ phiếu (tiêu đề nguồn "Trả Cổ tức bằng Cổ phiếu…" hoặc "Cổ phiếu thưởng…"): quyền = làm tròn xuống
  (số cổ phiếu × tỷ lệ); dưới 1 cổ phiếu thì chỉ báo, không soạn. Khi đã có quyền mà chưa có dòng "Cổ phiếu thưởng về": gợi ý ghi khi cổ
  phiếu về tài khoản, ngày để trống cho chủ sở hữu điền theo chứng từ (nguồn không có ngày về).
- Quyền mua cổ phiếu cho cổ đông hiện hữu: sổ chưa hỗ trợ (quy tắc hiện có: chặn phân tích) → chỉ nhắc, không soạn.
- Các loại phát hành khác (cho nhân viên, riêng lẻ, chuyển đổi trái phiếu) không thuộc cổ đông thường → bỏ qua.
- Đã ghi = sổ có dòng quyền cùng mã sự kiện, hoặc dòng quyền **cùng loại** (tiền hay cổ phiếu), cùng mã cổ phiếu, có ngày ghi hoặc ngày chốt
  trong vòng 5 ngày quanh GDKHQ (ghi tay trước đây). Cổ tức tiền và cổ phiếu thưởng cùng ngày chốt không lẫn nhau.
- Chủ sở hữu có thể "Bỏ qua" một gợi ý (ví dụ chứng từ khác hẳn); lưu ở kho cá nhân, khôi phục được.
- Phạm vi: GDKHQ trong 400 ngày gần nhất; sự kiện sắp tới (30 ngày) hiện để biết trước, chưa soạn.

## Thuế và phí theo năm
Bảng mỗi năm từ sổ: giá trị bán, phí giao dịch, thuế bán, cổ tức tiền đã nhận (thực nhận + thuế khấu trừ), thuế cổ tức đã khấu trừ,
tổng thuế và phí. Chỉ số đã ghi trong sổ; năm không có dòng nào thì không hiện. Không phải tư vấn thuế.

## Giao diện
Danh mục & Giao dịch: mục "Cổ tức và quyền" (cần ghi, đang chờ tiền/cổ phiếu về, sắp tới, quyền mua cần tự xử lý) và mục
"Thuế và phí theo năm". "Ghi vào sổ" mở form giao dịch đã điền sẵn; form có thêm hai loại "Quyền cổ phiếu thưởng" và "Cổ phiếu thưởng về".
Không gửi gì cho AI; dữ liệu chỉ trên máy và kho cá nhân.
