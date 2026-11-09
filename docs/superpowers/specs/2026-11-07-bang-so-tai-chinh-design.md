# Bảng số tài chính (07/11/2026)

Từ 3 ảnh bảng số HPG chủ sở hữu gửi (kết quả kinh doanh 10 quý có EBIT/EBITDA; định giá theo năm có vốn hoá, nợ ròng, EV, EV/EBITDA, FCFF).
Chủ sở hữu chọn (07/11/2026): làm **bảng số quý/năm**; với lãi vay, khấu hao, nợ vay, capex thì **kiểm tra VNDirect trước** rồi dùng
VNDirect làm nguồn; lúc đầu **giữ** quy tắc 45 ngày của chuỗi định giá theo tuần. Các việc sau ghi lúc đó đều đã làm (07/11/2026): ngày VNDirect đưa số lên ([Số quý VNDirect](2026-11-07-chuoi-dinh-gia-tuan-design.md)), kế hoạch
năm ĐHCĐ, dự phóng quý tới, số liệu vận hành nhập tay (và đọc từ PDF). Chỉ dữ liệu công khai, không đọc danh mục, không gọi AI.

## Nguồn (`market/statements.py`)
- Vnstock gói Cộng đồng chỉ có 8 kỳ, không có lãi vay, khấu hao, nợ vay, capex (đã kiểm với HPG 07/11/2026).
- API công khai VNDirect `v4/financial_statements` (robots.txt trả 404: không cấm gì; cùng API đang dùng cho tỷ số ngân hàng): báo cáo đầy
  đủ theo mã dòng, quý từ 2010–2015 tuỳ mã, năm từ 2010–2012. Số quý là **từng quý, không lũy kế** (HPG 2025: 4 quý cộng đúng bằng cả năm
  ở doanh thu, khấu hao, lãi vay, capex). Dấu: chi phí dương, tiền chi ra âm.
- Chỉ giữ các dòng cần (mẫu chung TT200; dòng liên doanh liên kết và lợi ích cổ đông không kiểm soát của mẫu trước 2015 được nhận). Một dòng
  có hai số khác nhau trong cùng kỳ là **xung đột**: không lấy số nào, liệt kê cả hai.
- Bỏ qua ngân hàng, chứng khoán, bảo hiểm (mẫu khác; đã có bảng số liệu ngành).
- `statements-sync`: lượt 20:00, 8 mã cũ nhất (chưa có trước), làm mới sau 7 ngày; lần đầu lấy toàn bộ lịch sử, sau đó 2 năm gần nhất và giữ
  kỳ cũ. Ba lượt gọi mỗi mã (quý, năm, giá thực). `--all` cho lần nạp đầu. `data/statements/<mã>.json`.

## Bảng (`valuation/statement_table.py`)
- Quý và năm: doanh thu bán hàng, giảm trừ, doanh thu thuần, giá vốn, lãi gộp, chi phí bán hàng, quản lý, **LN HĐKD lõi** (= gộp − bán hàng
  − quản lý), doanh thu và chi phí tài chính, lãi vay, liên doanh liên kết, LN khác, LNTT, LNST công ty mẹ; **EBIT** = LNTT + lãi vay;
  **EBITDA** = EBIT + khấu hao; % so cùng kỳ (doanh thu, lãi gộp, LNST, EBITDA), biên gộp, ròng, EBIT, EBITDA; lưu chuyển tiền HĐKD, capex,
  **FCFF** = lưu chuyển HĐKD + lãi vay × (1 − thuế ÷ LNTT) + capex, không tính khi LNTT ≤ 0 hoặc thuế suất ngoài 0–100 %.
- Năm thêm: **vốn hoá** = giá đóng cửa thực (chưa điều chỉnh) phiên cuối năm × số cổ phiếu cuối năm (vốn góp ÷ mệnh giá 10.000 đ), đổi ngày
  07/11/2026 theo chủ sở hữu (bản đầu dùng giá điều chỉnh × số cổ phiếu hiện tại, làm các năm cũ thấp: HPG 2018 63.152 so với 65.735 tỷ). Giá
  thực từ API giá VNDirect (`v4/stock_prices`, từ 02/01/2013; một lượt gọi mỗi mã, giữ giá phiên cuối mỗi năm); năm không có giá thực hoặc vốn góp
  thì để trống vốn hoá và các bội số theo nó; nợ vay; tiền và đầu tư tài chính
  ngắn hạn; **nợ ròng** = nợ vay − tiền − đầu tư tài chính ngắn hạn; **EV** = vốn hoá + nợ ròng + lợi ích cổ đông không kiểm soát; P/E (LNST
  công ty mẹ), P/B (vốn chủ công ty mẹ), EV/EBITDA, EV/doanh thu, lợi suất FCFF = FCFF ÷ EV, ROE = LNST công ty mẹ ÷ vốn chủ công ty mẹ bình
  quân năm đó và năm trước.
- Quý thêm cùng khối **Quy mô và định giá** (08/11/2026, chủ sở hữu yêu cầu): vốn hoá = giá đóng cửa thực phiên cuối quý × số cổ phiếu cuối
  quý (vốn góp quý ÷ 10.000 đ); nợ vay, tiền, nợ ròng, EV theo bảng cân đối cuối quý; P/E, EV/EBITDA, EV/doanh thu, lợi suất FCFF trên tổng 4
  quý tới quý đó; P/B trên vốn chủ công ty mẹ cuối quý; ROE = LNST 4 quý ÷ vốn chủ công ty mẹ bình quân quý đó và cùng quý năm trước. Thiếu
  một trong 4 quý thì để trống các bội số theo lợi nhuận. Đồng bộ giữ thêm giá phiên cuối mỗi quý (`quarter_end_close`), cùng lượt gọi giá;
  mã đồng bộ trước khi có giá cuối quý được làm lại ngay lượt sau, lấy giá từ 2010.
- **Ngân hàng và chứng khoán** (08/11/2026, chủ sở hữu duyệt): khối **Quy mô và định giá** riêng, đặt sau Chỉ số ngành theo quý, nút Quý/Năm,
  Xu hướng và biểu đồ như bảng trên (mở sẵn P/B với ROE). Dòng: vốn hoá, vốn chủ công ty mẹ, giá trị sổ sách / cổ phiếu (đồng), P/B, P/E, ROE;
  ngân hàng thêm vốn hoá / LN trước dự phòng và vốn hoá / tổng thu nhập hoạt động; chứng khoán thêm vay (ngắn + dài hạn) / vốn chủ sở hữu và
  vốn hoá / doanh thu hoạt động. Quý tính trên 4 quý tới quý đó, năm trên số cả năm, giá và số cổ phiếu cuối kỳ như trên. Không có nợ ròng, EV,
  EBITDA, FCFF (đi vay là hoạt động kinh doanh). Nguồn: cùng API, mẫu ngân hàng (101–103, TT49) và chứng khoán (89–91, TT334), chỉ giữ dòng cần
  dùng, lưu riêng `data/statements-financial/` để Định giá tham khảo, chuỗi định giá tuần, kế hoạch năm và báo quý mới không đổi nguồn. Mỗi lượt
  gọi tối đa 60.000 dòng (lịch sử quý của SSI khoảng 27.000; giới hạn 20.000 cũ cắt mất các quý mới); trả đủ 60.000 dòng thì coi là có thể bị cắt,
  báo lỗi, không lưu. Kiểm tra chéo: tổng 4 quý với cả năm (LNST công ty mẹ, LN trước dự phòng, tổng thu nhập hoạt động, doanh thu hoạt động) và
  LNST với Vnstock.
- **Bảo hiểm** (08/11/2026, chủ sở hữu duyệt; BVH): cùng khối, mẫu 411–413. Dòng chung như trên, thêm vốn hoá / doanh thu phí bảo hiểm thuần,
  danh mục đầu tư (tiền + đầu tư tài chính ngắn và dài hạn) / vốn chủ, **kết quả kinh doanh bảo hiểm** và **lợi nhuận hoạt động tài chính**
  (tỷ; 4 quý ở chế độ Quý); biểu đồ mở sẵn hai dòng này. Kết quả bảo hiểm chỉ hiện ở kỳ mà nó cộng lợi nhuận hoạt động tài chính, lợi nhuận
  hoạt động khác, LN khác và liên kết (cả dòng cũ "trước 2015" BVH vẫn ghi) ra đúng LNTT: từ Q3/2014 chênh 0, mẫu cũ chênh tới vài trăm tỷ;
  kỳ không khớp để trống và ghi ở Kiểm tra chéo. Không tính P/EV (giá trị nội tại không có trong báo cáo) và tỷ lệ kết hợp (BVH hợp nhất
  nhân thọ; bảng chỉ số ngành đã có số của VNDirect).
- **Một khối cho ngân hàng, chứng khoán, bảo hiểm** (08/11/2026, chủ sở hữu yêu cầu; thay hai khối riêng Chỉ số ngành theo quý và Quy mô và
  định giá): Bảng số tài chính của các mã này giống doanh nghiệp thường — biểu đồ trên cùng, nút Quý/Năm, 8 · 12 · 20 quý · Tất cả, rồi một bảng
  với nhóm **Chỉ số ngân hàng / công ty chứng khoán / bảo hiểm** (tỷ lệ VNDirect) trước nhóm Quy mô và định giá; bấm tên dòng nào cũng vẽ được.
  Tỷ lệ chỉ có theo quý (chế độ Năm chỉ có nhóm định giá, có ghi chú); đồng bộ tỷ lệ lấy từ 2017 (VNDirect giữ từ Q4/2017, ROAA và ROAE từ
  Q3/2023) thay vì 800 ngày, API trả mọi quý. Tỷ lệ VNDirect ghi 2 chữ số thập phân như bảng cũ (NPL, nợ quá hạn, NIM, ROAA, cho vay / vốn chủ).
- Tóm tắt 4 quý gần nhất liền nhau với giá đóng cửa gần nhất: LNST, EBITDA, ROE, P/E, P/B, EV/EBITDA.
- Thiếu một thành phần thì để trống, không ước lượng. Đối chiếu HPG với ảnh: Q3/26 khớp từng số; 2025 nợ ròng 64.389 và FCFF −5.704 khớp,
  EV/EBITDA 9,1x khớp; vốn hoá 2018 = 30,95 nghìn đ × 2.123,9 triệu cổ phiếu = 65.735 tỷ, khớp ảnh.
- **Kiểm tra chéo** (lệch hơn 0,5 %): lãi gộp với doanh thu thuần − giá vốn; tổng 4 quý với cả năm (doanh thu, LNST công ty mẹ, khấu hao,
  capex, lưu chuyển HĐKD); LNST công ty mẹ VNDirect với Vnstock. Dòng tiền quý những năm cũ thường lệch số cả năm đã kiểm toán (HPG
  2010–2023); trang liệt kê, không sửa.

## API và giao diện
- `GET /internal/fairvalue/statements/{mã}`: mã trong danh sách theo dõi (khác: 404); ngân hàng, chứng khoán, bảo hiểm và mã chưa đồng bộ trả
  lý do.
- Trang hồ sơ mã, sau Định giá tham khảo: khối **Bảng số tài chính**: 4 thẻ tóm tắt 4 quý; nút Quý/Năm; nút 8 · 12 · 20 quý · Tất cả; bảng
  (tỷ đồng, chi phí âm, % so cùng kỳ xanh/đỏ, cột nhãn đứng yên khi cuộn ngang); mục Kiểm tra chéo; chú thích công thức và nguồn.
- **Biểu đồ** (08/11/2026, chủ sở hữu duyệt mức 1 và 2): cột **Xu hướng** cuối mỗi dòng theo đúng các kỳ đang chọn (tiền: cột nhỏ quanh
  trục 0; %, bội số: đường). Bấm tên dòng để vẽ **biểu đồ lớn** trên bảng, tối đa 2 dòng (dòng thứ ba thay dòng chọn sớm nhất); mở sẵn
  Doanh thu thuần với Biên gộp. Tiền vẽ cột theo tỷ đồng làm tròn như bảng (âm chúc xuống), %, bội số vẽ đường; mỗi đơn vị một trục (trái, phải). Ô trống là khoảng
  trống, không nối, không nội suy. Cột dự phóng của chủ sở hữu (quý F) vẽ gạch chéo, không nối với số thật. Kỳ có lệch trong Kiểm tra chéo ở
  chính dòng đang vẽ hoặc số tính ra từ nó gắn dấu * dưới trục, chạm vào kỳ hiện chỗ lệch (sửa 08/11/2026: bản đầu gắn * cho mọi
  chỗ lệch, HPG năm nào cũng có). Trục chia số tròn, tiền luôn có mốc 0. Chạm hoặc rê vào kỳ hiện số; mục **Xem số liệu** liệt kê đủ số đang vẽ. Không thêm thư viện, vẽ bằng SVG.

## Ngày công bố cho VN-Index, VN30 tự tính 2013–2017 (07/11/2026)
Chuỗi tự tính ([index_history](../../../backend/src/investment_agent/market/index_history.py)) vẫn dùng quy tắc 45 ngày. Đã kiểm trên báo cáo VNDirect
đã lưu của các mã theo dõi: gần như mọi quý 2013–2017 (690/692) có `createdDate` là đợt nạp số cũ tháng 12/2019, nằm ngoài 120 ngày, nên quy tắc ngày
VNDirect cũng rơi về 45 ngày. Đổi sang ngày VNDirect không làm khác chuỗi này, nên không đổi.

- **CASA và tỷ lệ nợ nhóm 2 cho ngân hàng** (08/11/2026, chủ sở hữu duyệt): VNDirect không có hai tỷ lệ này (188 mã của MBB, chỉ có
  tiền gửi / tổng tài sản và LDR), nên nhóm "Chỉ số ngân hàng" lấy chúng từ Số liệu ngân hàng (nhập tay), cùng công thức với khối đó:
  nợ nhóm 2 / nợ nhóm 1–5 (2 chữ số thập phân, ngay sau NPL) và (không kỳ hạn + ký quỹ) / tiền gửi của khách hàng (ngay sau NIM). Nhãn ghi
  "(nhập tay)"; quý chưa nhập để trống, không nội suy; quý đã nhập mà VNDirect chưa có thì vẫn thêm cột. Bấm tên dòng để vẽ như các chỉ số khác.
- **Nợ nhóm 2 và CASA từ Vietcap** (08/11/2026, chủ sở hữu duyệt): nguồn chính là thuyết minh báo cáo tài chính trên API IQ công khai của
  Vietcap (`iq.vietcap.com.vn/.../financial-statement?section=NOTE`: nợ nhóm 1–5 và tổng dư nợ, tiền gửi theo loại và tổng tiền gửi;
  từ Q1/2018). Đã dò: VNDirect có danh mục mục thuyết minh (mẫu 104) nhưng không trả số; Vnstock Cộng đồng khoá `note` và `ratio`; TCBS
  chặn bằng Cloudflare. Lệnh `bank-notes-sync` (lượt 20:00) gọi mỗi ngân hàng theo dõi một lần, cách nhau 10 giây theo `Crawl-delay`
  của `trading.vietcap.com.vn` (`iq.vietcap.com.vn` không có robots.txt), dưới tên ứng dụng (không giả trình duyệt), mỗi mã làm mới tối đa một lần một tuần; lưu `data/bank-notes`. Tỷ lệ chỉ tính khi
  nhóm 1–5 cộng ra đúng tổng dư nợ và các loại tiền gửi cộng ra đúng tổng tiền gửi; lệch thì để trống và ghi hai số ở "Đối chiếu nợ nhóm
  2 và CASA". Quý đã nhập tay dùng số nhập tay; khác số Vietcap (ở 4 chữ số thập phân) thì ghi cả hai. Nhãn bỏ "(nhập tay)". CAR vẫn nhập tay.
- **CAR cuối năm** (08/11/2026, chủ sở hữu duyệt): không nguồn miễn phí nào có CAR theo quý (VNDirect: mục 55002 rỗng; Vietcap: dòng quý
  ghi 0,0). Dòng "CAR (cuối năm)" sau Vốn chủ / tổng tài sản, 2 chữ số thập phân, ở cột Q4: số của Vietcap (`statistics-financial`, dòng năm,
  cùng lượt `bank-notes-sync`, thêm một lần gọi cách 10 giây; bị từ chối thì không thử lại và dừng cả lượt, các mã còn lại chờ lượt sau), năm Vietcap chưa có thì dùng
  `BANK_CAR_AQ` của VNDirect (lấy cùng `financial-ratios-sync`, không hiện thành dòng), trừ mức 8,00% VNDirect ghi nhiều năm cho BID (mức
  tối thiểu, không phải số báo cáo). Ghi ở mục đối chiếu khi hai nguồn lệch quá 0,1 điểm, hoặc Vietcap ghi đúng y số năm trước (EIB 2025).
  Quý đã nhập CAR ở Số liệu ngân hàng dùng số nhập tay. Chưa đưa CAR vào Điểm sức khỏe (chỉ có số năm).
- **Vốn hoá của 4 thẻ tóm tắt** (08/11/2026, chủ sở hữu duyệt): vốn hoá hiện tại = vốn hoá cuối quý mới nhất (giá thực × vốn điều lệ ÷ 10.000 đ) × giá đã
  điều chỉnh mới nhất ÷ giá đã điều chỉnh của phiên cuối quý đó, thay cho giá × số cổ phiếu suy ra từ LNST / EPS (28/57 mã lệch quá 3% so với số niêm yết;
  PLX +40%). Thiếu phiên cuối quý trong chuỗi giá thì vốn hoá, P/E, P/B, EV/EBITDA trên thẻ để trống. Phép định giá ở trang Định giá giữ nguyên: đo
  08/11/2026 đổi sang số niêm yết không làm đổi kết luận của mã nào trong 57 mã.
- **ROIC vận hành 4 quý** (09/11/2026, chủ sở hữu duyệt), trên thẻ tóm tắt của doanh nghiệp thường: LN HĐKD lõi 4 quý × (1 − thuế ÷ LNTT 4 quý) ÷ vốn đầu tư bình quân cuối kỳ và cùng kỳ năm trước; vốn đầu tư = vốn chủ gồm cổ đông thiểu số + nợ vay − tiền và đầu tư tài chính ngắn hạn. Thu nhập tài chính và khoản bất thường không tính. Thiếu một thành phần, LNTT âm hoặc vốn đầu tư không dương thì để trống.
- **Đối chiếu định giá** (09/11/2026, chủ sở hữu duyệt): dưới Bảng số tài chính, vốn hoá, P/E, P/B của phần mềm tại giá mới nhất đặt cạnh số `MARKETCAP`, `PRICE_TO_EARNINGS`, `PRICE_TO_BOOK` của VNDirect (`valuation-check-sync`, lượt 20:00, lưu `data/valuation-check`). Lệch quá 10% thì tô đỏ và đếm ở tiêu đề; không tự chỉnh số. FiinTrade là nguồn trả phí nên không so.
- **Số cổ phiếu khi vốn hoá lệch** (09/11/2026, chủ sở hữu duyệt): vốn hoá hiện tại theo số cuối quý lệch quá 10% so với `MARKETCAP` của VNDirect thì tính bằng giá đóng cửa mới nhất × `OUTSTANDING_SHARES` của VNDirect (cổ phiếu phát hành sau quý mà chuỗi giá điều chỉnh không phản ánh, như PHR, HCM). Chỉ áp dụng cho 4 thẻ tóm tắt, cột "theo giá" của So sánh cùng ngành, bảng đèn và bảng đối chiếu; bảng theo quý và trang Định giá giữ nguyên. Bảng đối chiếu ghi rõ khi đã dùng số này, vì khi đó không còn là phép kiểm tra độc lập.

