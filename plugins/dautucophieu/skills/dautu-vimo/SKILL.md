---
name: dautu-vimo
description: Tóm tắt chỉ báo vĩ mô từ dữ liệu công khai trên máy — lạm phát, PMI, lãi suất, tỷ giá, lợi suất trái phiếu, hàng hóa, chỉ số Mỹ. Dùng khi người dùng gõ /dautu-vimo [chủ đề hoặc mã chỉ báo] hoặc hỏi vĩ mô đang thế nào.
argument-hint: [chủ đề như "lãi suất", "tỷ giá", "hàng hóa", hoặc mã chỉ báo]
---

# Vĩ mô: $ARGUMENTS

## Lấy dữ liệu (server dautucophieu-cong-khai)

1. Gọi `danh_sach_vi_mo` để biết mã nào đang có và trạng thái cập nhật.
2. Chọn chỉ báo:
   - Có chủ đề hoặc mã: lấy các mã trong danh sách khớp chủ đề đó (ví dụ lãi suất: vn_interbank_on, vn_interbank_1w, deposit_12m, vn10y, fed_effr, us10y; tỷ giá: usd_vnd_central, usd_vnd_free, dxy; hàng hóa: brent, wti, com_ các loại, xau_usd).
   - Không có gì: vn_cpi_yoy, vn_pmi, vn_interbank_on, deposit_12m, usd_vnd_central, usd_vnd_free, vn10y, us10y, dxy, brent.
   - Chỉ dùng mã có trong danh sách; mã không có thì ghi là thiếu.
3. Gọi `chi_bao_vi_mo` cho từng mã, so_diem 6.

## Trình bày

1. Bảng: chỉ báo, giá trị mới nhất, ngày, giá trị kỳ trước, chiều thay đổi. Thay đổi chỉ tính từ hai quan sát trong kho.
2. Chỉ báo có trạng thái không phải ok, hoặc ngày mới nhất đã cũ, thì ghi rõ "chưa cập nhật" kèm ngày.
3. **Thiếu**: mục nào trả `thieu` thì ghi lý do nguyên văn.
4. Một đoạn ngắn nêu những gì số cho thấy; không dự báo, không suy ra tác động lên mã cụ thể nào.

## Quy tắc

- Không đoán số, không nội suy, không lấy số từ kiến thức có sẵn hay nguồn ngoài.
- Không nhắc tới danh mục hay giao dịch của người dùng.
