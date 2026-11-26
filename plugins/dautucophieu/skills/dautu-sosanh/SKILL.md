---
name: dautu-sosanh
description: "So sánh hai đến bốn mã cổ phiếu HOSE cạnh nhau từ dữ liệu công khai trên máy: ngành, giá, kết quả kinh doanh, EPS, cổ tức, chỉ số tài chính. Dùng khi người dùng gõ /dautu-sosanh <MÃ1> <MÃ2> … hoặc nhờ so sánh vài mã."
argument-hint: "<MÃ1> <MÃ2> [MÃ3] [MÃ4] (ví dụ FPT CMG)"
---

# So sánh: $ARGUMENTS

Các mã là những từ người dùng gõ sau lệnh, viết hoa, từ 2 đến 4 mã. Ít hơn 2 thì hỏi lại; nhiều hơn 4 thì chỉ lấy 4 mã đầu và nói rõ.

## Lấy dữ liệu (server dautucophieu-cong-khai, gọi song song được)

Với từng mã:
1. `thong_tin_ma`.
2. `gia_ngay` với so_phien 60.
3. `bao_cao_tai_chinh` với ky "nam", so_ky 3; thêm ky "quy", so_ky 4.
4. `eps_co_tuc` với so_ky 4.
5. `chi_so_tai_chinh` với so_ky 4.

## Trình bày

1. **Một bảng chung**, mỗi mã một cột: ngành, nhóm chỉ số, giá đóng phiên mới nhất (kèm ngày), thay đổi 60 phiên, doanh thu và lợi nhuận 3 năm, EPS gần nhất, cổ tức gần nhất, số cổ phiếu lưu hành.
2. **Chỉ số tài chính**: chỉ đặt cạnh nhau những chỉ số mà mọi mã đều có. Ngân hàng, chứng khoán, bảo hiểm có bộ chỉ số khác doanh nghiệp thường; khác loại thì tách bảng và nói rõ là không so trực tiếp được.
3. **Khác biệt chính**: 3 đến 5 gạch đầu dòng, chỉ nêu điều số trong bảng cho thấy.
4. **Thiếu**: mục nào trả `thieu` thì ghi mã, mục và lý do nguyên văn; ô thiếu trong bảng để "thiếu", không để trống.
5. **Nguồn** và thời điểm lấy của từng mã.

## Quy tắc

- Không đoán số, không nội suy, không lấy số từ kiến thức có sẵn hay nguồn ngoài.
- Mọi phép tính (thay đổi %, đổi đơn vị sang tỷ đồng) chỉ dùng số trong kho và ghi rõ kỳ dùng để tính.
- Không xếp hạng "nên mua mã nào", không khuyến nghị mua bán, không đặt giá mục tiêu.
- Không hỏi, nhắc hay suy đoán danh mục, giá vốn, danh sách theo dõi của người dùng.
