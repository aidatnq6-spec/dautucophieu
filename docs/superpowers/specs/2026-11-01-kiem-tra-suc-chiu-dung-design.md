# Kiểm tra sức chịu đựng danh mục

Ngày: 01/11/2026 · Trạng thái: chủ sở hữu chọn "làm luôn"; các lựa chọn dưới đây là quyết định của người làm.

## Mục tiêu
Trước một cú sốc (VN-Index giảm, dầu tăng, đồng USD mạnh lên), thấy danh mục cổ phiếu đang nắm có thể giảm bao nhiêu đồng và bao nhiêu
phần trăm, so với mức chính chủ sở hữu khai là chịu được, và mã nào sẽ vượt ngưỡng của Kế hoạch sụt giảm. Ước tính tuyến tính từ quan hệ
trong quá khứ — **không phải dự báo**.

## Cách tính (mỗi mã đang nắm)
- Giá trị hiện tại = số cổ phiếu × giá đóng cửa gần nhất đã lưu. Không có giá → mã bị loại khỏi phép tính và được nêu tên.
- Thay đổi ước tính = beta × thay đổi VN-Index + hệ số dầu × thay đổi giá dầu + hệ số USD × thay đổi chỉ số đồng USD.
  - Beta: VNDirect công bố (đã lưu cho Gợi ý CAPM). Thiếu beta khi kịch bản có VN-Index → mã bị loại, nêu tên.
  - Hệ số dầu, USD: Độ nhạy 3 năm trên trang Vĩ mô (phần vượt ngoài VN-Index). Chỉ tính khi quan hệ **rõ** (|t| ≥ 2); không rõ hoặc
    chưa đủ dữ liệu → phần đó không tính, ghi rõ "chưa tính" cho mã đó.
  - "USD" là chỉ số đồng USD rộng (như trang Vĩ mô), không phải tỷ giá USD/VND.
- Một mã không giảm quá −100% (ước tính vượt thì chặn và ghi chú). Mã đã thấp hơn giá vốn quá ngưỡng từ trước được ghi chú riêng.
- Hệ số dầu và USD đo riêng rẽ (mỗi cái cùng VN-Index), nên cú sốc cả hai có thể tính trùng một phần; trang ghi rõ.
- Không có kịch bản lãi suất: phần mềm chưa có quan hệ đo được giữa lãi suất và giá từng mã; không lấp bằng giả định.

## Kịch bản
Có sẵn: VN-Index −10%, VN-Index −20%, lặp lại đợt giảm sâu nhất của VN-Index trong lịch sử đã lưu (độ sâu và ngày thật), dầu +30%,
USD +5%. Tự nhập: ba ô VN-Index %, dầu %, USD %.

## So sánh
- Với câu 10 khảo sát rủi ro (đầu tư 100 triệu, giảm bao nhiêu trong 1 năm khiến muốn giảm rủi ro): A đến 5%, B đến 10%, C đến 20%,
  D trên 20%. Kết quả nói kịch bản vượt hay chưa vượt mức đã khai (A–C; đúng bằng mức khai là chưa vượt); D không có giới hạn trên.
  Chưa làm khảo sát → không so sánh. Có mã không tính được thì ghi "chỉ trên phần được tính" và giá trị không tính được.
- Với Kế hoạch sụt giảm: mã sẽ thấp hơn giá vốn quá ngưỡng (cài đặt hiện tại) sau kịch bản.

## Giao diện
Danh mục & Giao dịch, mục "Kiểm tra sức chịu đựng", ngay sau Kế hoạch sụt giảm. Tính trên trình duyệt từ số liệu máy chủ trả; không gửi
gì cho AI, không lưu kịch bản.
