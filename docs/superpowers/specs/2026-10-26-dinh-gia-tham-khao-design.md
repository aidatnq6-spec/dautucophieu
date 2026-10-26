# Thiết kế: trang "Định giá" (định giá tham khảo nhiều phương án cho 50 mã)

Ngày: 26/10/2026 · Trạng thái: chờ chủ sở hữu duyệt

## Mục đích

Chủ sở hữu muốn biết, cho từng mã đang theo dõi, **giá hiện tại đang rẻ hay đắt so với giá trị thật**, để tham khảo. Ứng dụng đã có bộ tính định giá chi tiết (FCFF/FCFE, DDM, thu nhập thặng dư, NAV, chu kỳ) cùng quy trình duyệt giả định. Nhưng bộ này cần giả định nhập tay, chưa có màn hình nhập, và chưa có dữ liệu tài chính tự động, nên hiện chưa định giá được mã nào.

Trang mới **"Định giá"** dùng báo cáo tài chính lấy tự động. Với mỗi mã, trang áp dụng vài phương án định giá phù hợp với ngành, đưa ra một khoảng giá hợp lý và kết luận **Rẻ / Hợp lý / Đắt** so với giá hiện tại.

## Mục tiêu

- Định giá cả **50 mã** trong `data\market-symbols.txt`. Danh sách này gồm 9 mã của bảng Xu hướng và 4 mã chủ sở hữu đang nắm.
- Mỗi mã có:
  - giá hợp lý theo từng phương án áp dụng được;
  - khoảng giá hợp lý (thấp nhất – cao nhất);
  - giá hợp lý trung tâm (trung vị);
  - mức chênh lệch so với giá hiện tại;
  - kết luận Rẻ / Hợp lý / Đắt.
- **Ngưỡng kết luận (chủ sở hữu chọn): 20%.**
  - Giá ≤ 80% giá hợp lý trung tâm → **Rẻ**.
  - Giá ≥ 120% → **Đắt**.
  - Ở giữa → **Hợp lý**.
- **Lợi suất yêu cầu 13%/năm và tăng trưởng dài hạn 5%/năm** (chủ sở hữu đồng ý). Cả hai và ngưỡng 20% sửa được trong Cài đặt.
- Mỗi phương án hiện đủ số liệu đầu vào (EPS, giá trị sổ sách, ROE, P/E hoặc P/B bình quân, số năm dùng) để chủ sở hữu tự kiểm tra.

## Không làm

- Không mở vùng mua và không tạo khuyến nghị mua. Quy trình giả định đã duyệt và danh sách nghiên cứu hiện có giữ nguyên. Trang này chỉ để tham khảo.
- Không dùng AI.
- Không dùng nguồn trả phí.
- Không gửi Telegram.
- Không làm DCF dòng tiền tự do đúng nghĩa: lưu chuyển tiền tệ ở gói miễn phí chỉ có 7 dòng tổng, không có chi đầu tư tài sản cố định.
- Không làm NAV bất động sản: cần định giá quỹ đất, không có dữ liệu.

## Điều không được xảy ra

- Không bịa hoặc nội suy số. Phương án không đủ dữ liệu ghi "Không áp dụng" kèm lý do. Mã có ít hơn 2 phương án hợp lệ ghi "Chưa đủ dữ liệu" và không có kết luận.
- Không trộn giá đã điều chỉnh với EPS chưa điều chỉnh. Xem mục "Cách tính" về P/E và P/B lịch sử.
- Không trình bày như lời khuyên đầu tư. Trang ghi rõ là định giá tham khảo dựa trên số liệu công bố, có thể sai.
- Không vượt giới hạn Vnstock (60 lượt/phút) đến mức làm hỏng các lần chạy khác trong lịch.

## Dữ liệu (đã kiểm tra thực tế 25–26/10/2026, gói Vnstock Community)

| Số liệu | Có | Độ dài |
|---|---|---|
| Kết quả kinh doanh: doanh thu, LNST cổ đông công ty mẹ, EPS cơ bản (`IS_BASIC_EARNINGS_PER_SHARE`) | Có | 8 năm (2018–2025) và 8 quý |
| Bảng cân đối: `BS_EQUITY`, `BS_TOTAL_ASSETS`; ngân hàng có thêm `BS_LOANS_TO_CUSTOMERS` | Có | 8 năm và 8 quý |
| Lưu chuyển tiền tệ | Chỉ 7 dòng tổng | 8 năm |
| Sự kiện công ty (cổ tức tiền, cổ phiếu thưởng, phát hành) | Có, `Company(source="VCI").events()` | nhiều năm |
| Tỷ số tính sẵn (`ratio`) | Không, gói trả phí | — |
| Giá đóng cửa | Có, giá đã điều chỉnh, khoảng 8 năm | — |

Giới hạn: 60 lượt gọi mỗi phút, và mỗi lần lấy một báo cáo tốn nhiều lượt bên trong. Lúc kiểm tra, khoảng 3 báo cáo đã chạm giới hạn. Phân ngành ICB cấp 2 lấy từ `data\industries.json` (đã có).

## Cách tính

### Số liệu dẫn xuất (mỗi mã)

- **Số cổ phiếu hiện tại** = LNST công ty mẹ năm gần nhất / EPS cơ bản năm gần nhất. *Tôi chọn* cách này vì gói miễn phí không có số cổ phiếu lưu hành trực tiếp.
  - Sau đó **nhân thêm tỷ lệ của các đợt cổ phiếu thưởng, cổ tức bằng cổ phiếu và phát hành** có ngày sau kỳ báo cáo năm đó (lấy từ sự kiện công ty). Nếu bỏ bước này, một đợt thưởng 10% giữa năm sẽ làm giá hợp lý cao lên khoảng 10%.
  - EPS ở Việt Nam đôi khi đã trừ quỹ khen thưởng, phúc lợi, nên số cổ phiếu ước tính có thể lệch vài phần trăm. Trang ghi chú điều này.
- **EPS 4 quý gần nhất (TTM)** = tổng LNST công ty mẹ 4 quý gần nhất / số cổ phiếu hiện tại.
- **Giá trị sổ sách mỗi cổ phiếu (BVPS)** = vốn chủ sở hữu quý gần nhất / số cổ phiếu hiện tại.
- **ROE TTM** = LNST 4 quý / bình quân vốn chủ sở hữu của quý gần nhất và cùng quý năm trước.
- **P/E và P/B lịch sử theo năm** = (giá đóng cửa đã điều chỉnh của phiên cuối năm × số cổ phiếu hiện tại) / LNST năm (hoặc vốn chủ sở hữu cuối năm).
  - Lý do: giá đã điều chỉnh nhân với số cổ phiếu hiện tại xấp xỉ vốn hóa thật của năm đó, kể cả khi đã có cổ phiếu thưởng hay tách cổ phiếu. Cách này tránh chia giá đã điều chỉnh cho EPS chưa điều chỉnh.
  - Bỏ các năm LNST ≤ 0. Cần ít nhất 4 năm hợp lệ.
  - Lịch sử giá có khoảng 8 năm (từ cuối 2018), nên năm 2018 có thể thiếu giá cuối năm. Năm nào thiếu giá thì bỏ năm đó.

### Phương án

1. **P/E lịch sử**: EPS TTM × trung vị P/E các năm.
2. **P/B lịch sử**: BVPS × trung vị P/B các năm.
3. **P/E cùng ngành**: EPS TTM × trung vị P/E hiện tại của các mã cùng ngành ICB cấp 2 trong 50 mã. Cần ít nhất 3 mã khác có EPS TTM dương.
4. **P/B cùng ngành**: tương tự, dùng P/B.
5. **P/B hợp lý theo ROE**: BVPS × (ROE − g) / (r − g), với r = 13%, g = 5%. Không áp dụng khi ROE ≤ g.
6. **Chiết khấu cổ tức (Gordon)**: D₁ = cổ tức tiền mặt mỗi cổ phiếu năm gần nhất × (1 + g); giá trị = D₁ / (r − g). Chỉ áp dụng khi trả cổ tức tiền mặt ít nhất 4 trong 5 năm gần nhất. Cổ tức lấy từ sự kiện công ty, tính theo đồng mỗi cổ phiếu ở thời điểm chi trả.
7. **P/E trên lợi nhuận bình quân (cho ngành chu kỳ)**: (bình quân LNST 8 năm / số cổ phiếu hiện tại) × trung vị P/E các năm.

### Phương án theo ngành (tôi chọn, theo tên ICB cấp 2)

| Ngành | Phương án |
|---|---|
| Ngân hàng | P/B lịch sử, P/B theo ROE, P/E lịch sử, P/B cùng ngành |
| Dịch vụ tài chính, Bảo hiểm | P/B lịch sử, P/E lịch sử, P/B cùng ngành |
| Bất động sản | P/B lịch sử, P/E lịch sử |
| Tài nguyên Cơ bản, Hóa chất, Dầu khí | P/E trên lợi nhuận bình quân, P/B lịch sử |
| Các ngành còn lại | P/E lịch sử, P/E cùng ngành, chiết khấu cổ tức |

### Kết luận

- **Giá hợp lý trung tâm** = trung vị các phương án hợp lệ.
- **Khoảng giá hợp lý** = thấp nhất – cao nhất trong các phương án hợp lệ.
- **Chênh lệch** = giá hiện tại / giá hợp lý trung tâm − 1.
- Kết luận dùng ngưỡng 20% như ở mục Mục tiêu.
- Có ít hơn 2 phương án hợp lệ → "Chưa đủ dữ liệu".

## Cập nhật số liệu

- Báo cáo tài chính lưu mỗi mã một tệp `data\fundamentals\<mã>.json`. Mỗi tệp gồm số năm, số quý, sự kiện cổ tức, ngày lấy và nguồn. Số liệu tải lại được nên không đưa vào bản sao lưu.
- **Làm mới dần** (*tôi chọn*):
  - Mỗi lần lịch chạy lúc 20:00, lấy lại cho tối đa 8 mã có số liệu cũ nhất (cũ hơn 7 ngày). Như vậy cả 50 mã được làm mới khoảng mỗi tuần, mà mỗi lần chỉ mất vài phút.
  - Có lệnh chạy tay `fundamentals-sync --all` cho lần nạp đầu, mất khoảng 30–60 phút.
  - Gặp lỗi giới hạn lượt gọi thì đợi 65 giây rồi thử lại. Lỗi khác ghi vào log và bỏ qua mã đó trong lượt.
- **Định giá tính ngay khi mở trang**, từ số liệu đã lưu, giá đóng cửa mới nhất và cài đặt. Không lưu sẵn kết quả, nên đổi cài đặt là thấy kết quả mới ngay.
- **Cài đặt định giá** (`r`, `g`, ngưỡng) lưu cùng các cài đặt khác của chủ sở hữu trên Firestore (`settings/valuation`). Mặc định 13% / 5% / 20%.

## Giao diện

- Mục menu mới **"Định giá"**.
- **Bảng 50 mã** gồm các cột: Mã (đánh dấu nếu đang nắm), Ngành, Giá hiện tại, Giá hợp lý (trung tâm và khoảng), Chênh lệch %, Kết luận (nhãn màu: Rẻ xanh, Hợp lý xám, Đắt đỏ), Kỳ báo cáo gần nhất.
- **Lọc:** theo Kết luận, theo Ngành, hoặc chỉ mã đang nắm. **Sắp xếp** theo chênh lệch.
- **Bấm vào một mã** để mở phần chi tiết: từng phương án với giá hợp lý, các số đầu vào, ghi chú cách tính, hoặc lý do "Không áp dụng".
- Đầu trang ghi lợi suất yêu cầu, tăng trưởng, ngưỡng đang dùng, ngày số liệu, và câu "định giá tham khảo, không phải khuyến nghị".
- Trên điện thoại không có thanh trượt ngang: bảng chuyển thành dạng thẻ.

## Để người lập trình quyết định

- Tên module, đường dẫn API, định dạng tệp lưu, cách chia hàm.
- Chi tiết gọi `Company(...).events()` và cách nhận diện sự kiện cổ tức tiền mặt (mã sự kiện, đơn vị). Phải kiểm tra với dữ liệu thật trước khi viết bộ đọc.
- Thứ tự bước trong `run-after-close.ps1`.

## Tiêu chí hoàn thành

- Sau lần nạp đầu, trang "Định giá" hiện đủ 50 mã. Mã có từ 2 phương án hợp lệ trở lên có kết luận; mã còn lại ghi "Chưa đủ dữ liệu" kèm lý do.
- Có kiểm thử cho:
  - từng phương án trên số liệu biết trước, tính tay đối chiếu;
  - cách tính số cổ phiếu, EPS TTM, BVPS, ROE;
  - P/E và P/B lịch sử dùng giá đã điều chỉnh × số cổ phiếu hiện tại;
  - chọn phương án theo ngành;
  - ngưỡng kết luận;
  - các trường hợp không áp dụng (lỗ, thiếu năm, ROE ≤ g, không trả cổ tức);
  - làm mới dần và xử lý lỗi giới hạn lượt gọi;
  - API, cài đặt, trang (không cuộn ngang trên điện thoại).
- `verify.ps1` đạt.
- Chạy thật cho một vài mã đại diện (MBB, KDH, HPG, FPT), đối chiếu EPS và BVPS với báo cáo công bố.
