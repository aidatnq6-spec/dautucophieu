# So sánh ngành cho Claude (`so_sanh_nganh`)

Chủ sở hữu duyệt ngày 26/11/2026: một công cụ MCP đặt một mã cạnh các doanh nghiệp cùng ngành ICB cấp 2 trên HOSE, theo 16 chỉ số quý do VNDirect tính.

## Nguồn

- Ngành: `icb_codes` và `icb_names` trong `data/hose-listing.json` (VNDirect, cấp 2; 410/412 mã có ngành ngày duyệt). Không tạo tệp ngành mới, không đổi `industries.json`.
- Chỉ số: `data/financial-ratios-general/` (`general-ratios-sync`, mọi mã HOSE ngoài nhóm tài chính).

## Chỉ số (chủ sở hữu chọn)

Sinh lời: ROAE_TR_AVG4Q, ROIC_TR_AVG4Q, GROSS_MARGIN_TR, NET_MARGIN_TR. Sức khỏe: DEBT_TO_EQUITY_AQ, INTEREST_COVERAGE_TR, CURRENT_RATIO_AQ, DEBT_EBITDA. Dòng tiền và vận hành: CFO_TO_SALES_TR, DSO_TR_AVG5Q, DIO_TR_AVG5Q, CASH_CONVERSION_CYCLE_TR_AVG5Q. Tăng trưởng: NET_SALES_TR_GRYOY, NET_PROFIT_TR_GRYOY, EPS_TR_GR3YR, DIVIDEND_PAYOUT_TR.

## Cách so

- Quý so: quý mới nhất của mã có chỉ số. Chỉ so với doanh nghiệp cùng ngành có số ở đúng quý đó; doanh nghiệp chưa có quý đó (chưa công bố hay chưa tải) được đếm riêng, không lấy quý khác thay.
- Mỗi chỉ số: giá trị của mã, trung vị, tứ phân vị 25% và 75% của các doanh nghiệp còn lại, số doanh nghiệp có số, và thứ hạng của mã từ cao xuống thấp trong cả nhóm. Cần ít nhất 3 doanh nghiệp khác có số, không thì ghi thiếu kèm lý do.
- Không gắn nhãn tốt hay xấu: cao hơn không phải lúc nào cũng tốt (nợ vay, số ngày phải thu, tồn kho).
- Ngân hàng, bảo hiểm, dịch vụ tài chính: trả thiếu, vì bộ chỉ số ngành của họ khác.
- Số giữ nguyên như VNDirect tính; trung vị và tứ phân vị là phép tính thống kê trên các số đó, nói rõ trong kết quả.
