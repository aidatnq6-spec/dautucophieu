# Doanh thu, chi phí tài chính trong Bảng số tài chính (25/11/2026)

Chủ sở hữu duyệt ngày 25/11/2026 (bước 1 của đề xuất). Kaizen từ bài "Doanh thu tài chính và chi phí tài chính" (HPG, HAG 2021). Đối chiếu VNDirect: HPG
2021 doanh thu tài chính 3.071,4, lãi vay 2.525,8 (2020: 2.191,7); HAG 2021 doanh thu tài chính 735,1 (2020: 1.287,4), chi phí tài chính 1.090,3, lãi vay
971,9; tiền thu lãi, cổ tức (32700) HAG 2021 74,3 tỷ. Dấu hiệu có sẵn "Thu nhập tài chính chưa thu được tiền" và "Phải thu khác lớn" đã bật cho HAG
2021, không bật cho HPG, nên không thêm dấu hiệu. Dữ liệu đã có, không thêm dòng nguồn.

## Bảng
Nhóm **Tài chính và khác**, ngay sau "trong đó: lãi vay" (số của kỳ, không cộng 4 quý):
- **Lãi tài chính ròng** = doanh thu tài chính − chi phí tài chính.
- **Chi phí tài chính ngoài lãi vay** = chi phí tài chính − lãi vay (lỗ tỷ giá, dự phòng đầu tư, lỗ thanh lý…), ghi số âm như các chi phí khác.
  HPG 2021: −1.206 tỷ.
- **Tiền thu lãi, cổ tức ÷ doanh thu tài chính** (dòng 32700 của lưu chuyển tiền tệ; doanh thu tài chính còn gồm lãi tỷ giá, lãi thanh lý thu
  tiền ở dòng khác). HPG 2021: 34,3%; HAG 2021: 10,1%. Doanh thu tài chính không dương: để trống.

## Doanh thu tài chính theo loại, lãi vay vốn hóa nhập tay (bổ sung 25/11/2026, chủ sở hữu duyệt bước 2)
- Khối Thuyết minh TSCĐ (nhập tay), khóa `fin_income_notes`: mỗi năm (tối đa 15) các loại theo thuyết minh, tỷ đồng: lãi tiền gửi; lãi cho vay, trong
  đó cho bên liên quan vay (không lớn hơn lãi cho vay); cổ tức, lợi nhuận được chia; lãi tỷ giá đã thực hiện, chưa thực hiện; lãi thanh lý, chuyển
  nhượng đầu tư; khác; và **lãi vay đã vốn hóa** trong năm (thuyết minh chi phí đi vay).
- Phần mềm tính: tổng các loại (không cộng phần bên liên quan, vì là một phần của lãi cho vay, và lãi vay vốn hóa, vì không phải doanh thu), đối chiếu
  với doanh thu tài chính của báo cáo đã lưu; **phần khó lặp lại hoặc chưa thu tiền** = lãi cho bên liên quan vay + lãi thanh lý + lãi tỷ giá chưa
  thực hiện, so với LNTT (lỗ thì không tính tỷ trọng), và **LNTT loại phần này**; **lãi vay thực tế** = chi phí lãi vay trên báo cáo + phần vốn hóa,
  phần vốn hóa so với LNTT, ghi chú phần này sẽ vào chi phí khi dự án hoàn thành.
- HAG 2021 (bài): lãi cho vay 490,8, trong đó bên liên quan 469; lãi thanh lý 240; phần khó lặp lại 709 tỷ khi lỗ trước thuế 130,6 tỷ.
- Ghi phần khác không gửi `fin_income_notes` thì giữ nguyên.
