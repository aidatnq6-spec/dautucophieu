# Chỉ số tài chính (VNDirect) trên Bảng số tài chính của doanh nghiệp thường

Chủ sở hữu duyệt ngày 26/11/2026: hiện 12 chỉ số quý do VNDirect tính cho doanh nghiệp ngoài ngân hàng, chứng khoán, bảo hiểm, ở chỗ Bảng số tài chính đang hiện chỉ số ngành của nhóm tài chính.

## Dữ liệu

- Nguồn: `data/financial-ratios-general/<MÃ>.json` do `general-ratios-sync` tải (25 chỉ số VNDirect, từ 2017, mọi mã HOSE ngoài nhóm tài chính, 60 mã mỗi tối). Không đổi `data/financial-ratios/`, điểm sức khỏe hay các route khác.
- Route `GET /fairvalue/ratios/{mã}`: mã tài chính trả như cũ. Mã khác có tệp chỉ số thì trả `kind: "general"` với 12 dòng dưới đây, mọi quý có trong tệp. Không có tệp thì 404 như cũ.

| Mã VNDirect | Nhãn | Định dạng |
|---|---|---|
| ROAE_TR_AVG4Q | ROAE | % một số lẻ |
| ROAA_TR_AVG4Q | ROAA | % hai số lẻ |
| ROIC_TR_AVG4Q | ROIC | % một số lẻ |
| GROSS_MARGIN_TR | Biên lợi nhuận gộp 4 quý | % một số lẻ |
| NET_MARGIN_TR | Biên lợi nhuận ròng 4 quý | % một số lẻ |
| CFO_TO_SALES_TR | Dòng tiền kinh doanh / doanh thu 4 quý | % một số lẻ |
| DEBT_TO_EQUITY_AQ | Nợ vay / vốn chủ | lần |
| CURRENT_RATIO_AQ | Thanh toán hiện thời | lần |
| INTEREST_COVERAGE_TR | Khả năng trả lãi vay 4 quý | lần |
| DSO_TR_AVG5Q | Số ngày phải thu | ngày |
| DIO_TR_AVG5Q | Số ngày tồn kho | ngày |
| CASH_CONVERSION_CYCLE_TR_AVG5Q | Chu kỳ vận động vốn | ngày |

## Giao diện

- Bảng số tài chính của doanh nghiệp thường, chế độ Quý: nhóm đầu "Chỉ số tài chính (VNDirect)" với 12 dòng trên, theo đúng các quý của bảng; quý một bên không có để "—". Chế độ Năm không có nhóm này.
- Định dạng mới "ngày": số nguyên kèm chữ "ngày".
- Chú thích dưới bảng: tỷ lệ VNDirect tính sẵn từ dữ liệu công khai, theo quý; ROAE, ROAA, ROIC, biên và khả năng trả lãi trên 4–5 quý gần nhất, các hệ số khác tại cuối quý; quý doanh thu rất nhỏ làm số ngày và biên lệch xa, giữ nguyên như nguồn; có thể lệch "ROE 4 quý" và "ROIC vận hành 4 quý" ở phần tóm tắt vì ứng dụng tự tính từ báo cáo tài chính.
- Chưa có tệp chỉ số: bảng như cũ, không báo lỗi.
