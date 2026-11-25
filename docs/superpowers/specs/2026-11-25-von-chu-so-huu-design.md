# Vốn chủ sở hữu trong Bảng số tài chính (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 của đề xuất). Kaizen từ bài "Thay đổi vốn chủ sở hữu" (ví dụ HAG 2021, thuyết minh 25, 26): vốn chủ gồm
nhiều phần, không chỉ vốn góp; vốn chủ có thể giảm mạnh không qua lợi nhuận (điều chỉnh hồi tố, thoái vốn công ty con), và thặng dư vốn có thể
được dùng bù lỗ lũy kế. Doanh nghiệp thường, dữ liệu công khai, không gọi AI.

## Nguồn
- Đã có: vốn chủ sở hữu (14000), vốn góp (14110), lợi ích cổ đông không kiểm soát (14240, trước 2015: 15000), LNST hợp nhất, cổ tức đã trả (33600).
- Thêm (tên kiểm trong `v4/financial_models` ngày 25/11/2026): 14120 thặng dư vốn cổ phần, 14140 cổ phiếu quỹ (âm), 14160 chênh lệch tỷ giá hối
  đoái, 14170 quỹ đầu tư phát triển, 14200 LNST chưa phân phối; 33100 tiền thu từ phát hành cổ phiếu, nhận vốn góp; 33200 tiền chi trả vốn góp, mua
  lại cổ phiếu. `LINES_VERSION` lên 12.
- Đối chiếu HAG 31/12/2021: vốn chủ 4.673,2 (bài: 4.673), vốn góp 9.274,7, thặng dư 0 (2020: 3.263,9), LNST chưa phân phối −4.467,1 (đầu năm
  −6.301,7), quỹ đầu tư phát triển 282,4, chênh lệch tỷ giá −602,6 tỷ (bài ghi "−600,2 triệu", có lẽ nhầm đơn vị), lợi ích cổ đông không kiểm soát
  186,5 (2020: 4.949,3). Vốn chủ đầu năm VNDirect 10.027,8, bài ghi 10.270: chưa rõ nguồn lệch.
- Không dùng dòng "LNST chưa phân phối lũy kế đến cuối kỳ trước" (14220) làm dấu hiệu: lệch so với cuối năm trước ở 24/42 mã vì trích quỹ, chia cổ tức.

## Bảng
Nhóm **Vốn chủ sở hữu**, sau Nợ vay, trước Quy mô và định giá: vốn góp; thặng dư vốn cổ phần; cổ phiếu quỹ; chênh lệch tỷ giá hối đoái; quỹ đầu tư
phát triển; LNST chưa phân phối; lợi ích cổ đông không kiểm soát; **vốn chủ công ty mẹ ÷ vốn góp** (lần; dưới 1 là đã mất một phần vốn góp);
**lợi ích cổ đông không kiểm soát ÷ vốn chủ** (%); **thay đổi vốn chủ ngoài lợi nhuận** = vốn chủ cuối kỳ − vốn chủ kỳ trước (năm: năm trước;
quý: quý liền trước) − LNST hợp nhất − tiền phát hành − tiền mua lại + cổ tức đã trả (dòng tiền âm), tức thoái vốn công ty con, điều chỉnh hồi tố,
chênh lệch tỷ giá, trích quỹ… (thiếu một phần thì để trống). Ghi chú "Chưa đồng bộ" cho bản ghi trước phiên bản 12.

## Hai dấu hiệu ở Chất lượng báo cáo (bổ sung 25/11/2026, chủ sở hữu duyệt bước 2 và chọn ngưỡng)
Bản ghi cơ bản lấy thêm theo năm: vốn góp, LNST chưa phân phối, tiền phát hành, tiền mua lại cổ phiếu, cổ tức đã trả. Sau "Khả năng trả lãi thấp".
- **Vốn chủ thay đổi ngoài lợi nhuận**: |vốn chủ cuối năm − đầu năm − LNST − tiền phát hành − tiền mua lại − cổ tức đã trả| từ **10%** vốn chủ đầu năm.
  HAG 2021: −5.482 tỷ, 55% (thoái vốn HNG, điều chỉnh hồi tố); HPG 2021: 1,4%. Đọc thuyết minh thay đổi vốn chủ. Thiếu một phần hoặc vốn chủ đầu
  năm không dương: không đánh giá được.
- **Lỗ lũy kế, vốn chủ dưới vốn góp**: LNST chưa phân phối âm, **hoặc** vốn chủ công ty mẹ dưới vốn góp. Còn lỗ lũy kế thì chưa chia cổ tức tiền
  được; dưới vốn góp là đã mất một phần vốn. HAG 2021: −4.467 tỷ, 0,48 lần vốn góp.
- Hiện 0/42 mã theo dõi bật cả hai. Chỉ hiện trên trang.
