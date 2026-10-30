# Thiết kế: "Chuỗi giá trị" trong trang Thị trường & Ngành

Ngày: 30/10/2026 · Trạng thái: chờ chủ sở hữu duyệt

## Mục đích

Với mỗi ngành, chủ sở hữu muốn nhìn một sơ đồ trả lời được bốn câu hỏi:

1. **Đầu vào** của ngành là gì (nguyên liệu, chi phí chính)?
2. **Trung gian** là gì (chế biến, phân phối)?
3. **Đầu ra** là gì (sản phẩm, ai mua)?
4. **Yếu tố vĩ mô** nào tác động lên đầu vào và đầu ra, và hiện tại vĩ mô đang **tốt hay xấu** cho ngành?

Ví dụ ngành xi măng: than chiếm khoảng 35–40% giá thành sản xuất (ACBS, báo cáo HT1 ngày 28/10/2026, trang 1). Giá than tăng là xấu cho đầu vào. Lãi suất giảm hỗ trợ cầu nhà ở, tức tốt cho đầu ra.

Hiện ứng dụng đã có các mảnh rời: 17 chỉ số vĩ mô đã lưu, "Chuỗi tác động vĩ mô" trên trang Vĩ mô đọc chiều đi một tháng của từng chỉ số, và trang Nhận định có các ý "ngành hưởng lợi / bất lợi" lấy từ báo cáo. Chưa có chỗ nào nối vĩ mô với cấu trúc của từng ngành.

## Quyết định của chủ sở hữu

- **Nội dung chuỗi lấy từ báo cáo công khai.** Mỗi mục có trích dẫn nguồn.
- **Mỗi ngành phải có đủ chuỗi ngay từ đầu** (cách A). Nội dung được **soạn sẵn khi làm tính năng**, từ báo cáo và tài liệu công khai, rồi chủ sở hữu duyệt. Không chờ pipeline AI đọc dần.
- **Trình bày kiểu C:**
  - đầu mục là các thẻ, mỗi ngành một thẻ, kèm thanh tốt/xấu của vĩ mô hiện tại;
  - bấm thẻ thì mở sơ đồ Đầu vào → Trung gian → Đầu ra của ngành đó, với yếu tố vĩ mô gắn vào từng khâu (kiểu A trong bản phác).
- **Yếu tố quan trọng hơn được tính nặng hơn,** theo tỷ trọng nêu trong báo cáo. Cách quy đổi xem mục "Cách tính".
- **Thêm giá hàng hoá thế giới theo tháng, miễn phí, từ FRED** (chủ sở hữu đồng ý 30/10/2026). Đây là chuỗi IMF Primary Commodity Prices. Kiểm tra ngày 30/10/2026, số liệu đến tháng 9/2026:
  - than Úc `PCOALAUUSDM`; quặng sắt `PIORECRUSDM`; cao su `PRUBBUSDM`; đường `PSUGAISAUSDM`; tôm `PSHRIUSDM`;
  - khí LNG Nhật `PNGASJPUSDM`; nhôm `PALUMUSDM`; đồng `PCOPPUSDM`; lúa mì `PWHEAMTUSDM`; đậu tương `PSOYBUSDM`.

  Giá urê không có trên FRED, nên yếu tố này để xám. Các chuỗi này chỉ dùng cho Chuỗi giá trị, không hiện trong bảng của trang Vĩ mô, giống chuỗi dầu và USD dài hạn của phần Độ nhạy. Chúng được lấy cùng bước `macro-sync`.
- **Giai đoạn sau, không làm trong bản này:** AI của ứng dụng đọc báo cáo ACBS mới để bổ sung hoặc cập nhật chuỗi.

## Mục tiêu

- Có chuỗi cho mọi ngành của 50 mã trong `data\market-symbols.txt` (14 ngành ICB cấp 2, số liệu ngày 30/10/2026):

  | Ngành ICB cấp 2 | Mã |
  |---|---|
  | Ngân hàng | MBB, ACB, BID, CTG, SHB, STB, TCB, VCB, EIB |
  | Bất động sản | KDH, VHM, VIC, KBC, DXG, NLG, IJC |
  | Thực phẩm và đồ uống | MSN, VNM, VHC, KDC, SBT, ANV, PAN |
  | Hóa chất | GVR, DCM, DPM, PHR, DPR |
  | Điện, nước & xăng dầu khí đốt | GAS, REE, NT2, HDG |
  | Hàng & Dịch vụ Công nghiệp | GMD, PVT, VSC, HAH |
  | Dịch vụ tài chính | SSI, HCM, VND |
  | Xây dựng và Vật liệu | BMP, CTD, VCG |
  | Công nghệ Thông tin | FPT, CMG |
  | Bán lẻ | MWG, DGW |
  | Tài nguyên Cơ bản | HPG |
  | Bảo hiểm | BVH |
  | Hàng cá nhân & Gia dụng | PNJ |
  | Dầu khí | PVD |

- **Ngành ICB gộp những mô hình khác nhau thì tách thành chuỗi con.** Mỗi chuỗi con có thẻ riêng. Ví dụ:
  - Hóa chất → cao su tự nhiên (GVR, PHR, DPR) và phân bón (DCM, DPM);
  - Thực phẩm → sữa (VNM), thủy sản (VHC, ANV), đường (SBT), hàng tiêu dùng (MSN, KDC, PAN);
  - Bất động sản → nhà ở (KDH, VHM, VIC, DXG, NLG, IJC) và khu công nghiệp (KBC);
  - Điện, nước & xăng dầu khí đốt → khí (GAS) và điện (REE, NT2, HDG);
  - Hàng & Dịch vụ Công nghiệp → cảng (GMD, VSC), vận tải biển (PVT, HAH);
  - Xây dựng và Vật liệu → nhựa xây dựng (BMP), xây dựng (CTD, VCG).

  Danh sách tách cuối cùng do người soạn quyết, theo nguyên tắc: hai nhóm mã có đầu vào hoặc đầu ra chính khác nhau thì tách. Mỗi mã thuộc đúng một chuỗi.
- Mỗi chuỗi có: Đầu vào, Trung gian, Đầu ra; các yếu tố vĩ mô gắn với khâu chúng tác động; các mã theo dõi thuộc chuỗi.
- Thẻ tổng quan cho biết ngay chuỗi nào đang "thuận gió" và chuỗi nào đang bất lợi.

## Không làm

- Không có khuyến nghị mua bán. Đây là bức tranh mô tả.
- Không dùng AI khi ứng dụng chạy. Phần tốt/xấu được tính bằng quy tắc trên số liệu đã lưu.
- Không thêm nguồn số liệu trả phí.
- Không tự cập nhật nội dung chuỗi từ báo cáo mới (để giai đoạn sau).
- Không gửi Telegram.

## Điều không được xảy ra

- **Không bịa nội dung hay số.** Mỗi mục trong Đầu vào, Trung gian, Đầu ra và mỗi quan hệ "yếu tố → khâu → chiều tác động" phải có ít nhất một nguồn công khai (tên tài liệu, ngày, trang hoặc đường dẫn). Không tìm được nguồn thì không đưa vào, hoặc ghi "chưa có nguồn". Tỷ trọng chỉ ghi khi nguồn có nêu.
- **Không giấu phần chưa đánh giá được.** Yếu tố không có số liệu vẫn có mặt trên sơ đồ và chiếm phần xám trên thanh tốt/xấu.
- **Không hiện chuỗi chưa được duyệt** như thể đã kiểm chứng (xem mục "Duyệt").
- Không trình bày kết quả như lời khuyên đầu tư. Mục có ghi chú: mô tả từ tài liệu công khai và quy tắc đơn giản, có thể sai.

## Ràng buộc

- Chỉ dùng nguồn công khai mà robots.txt cho phép. Không lấy VnExpress. Không đăng nhập thay chủ sở hữu, nên PDF của SSI không dùng được (chỉ có tiêu đề).
- Nguồn đã kiểm tra ngày 30/10/2026:
  - **dùng tốt:** ACBS "Báo cáo Ngành & Doanh nghiệp" (`acbs.com.vn/trung-tam-phan-tich/bao-cao-doanh-nghiep`): PDF công khai, tiếng Việt, trích được chữ;
  - **dùng được:** BSC (`bsc.com.vn/Report/ReportFile/<id>`): PDF công khai, nhưng phần lớn là bản tin ngày hoặc báo cáo tiếng Anh, chữ trích ra có lúc vỡ dấu;
  - **dùng tham khảo:** báo cáo thường niên của doanh nghiệp, số liệu của Tổng cục Thống kê và các hiệp hội ngành (công khai).
- Dữ liệu cá nhân không ra khỏi máy. Thông tin "đang nắm" chỉ dùng để đánh dấu thẻ.
- Theo quy trình chung của repo: TDD, chạy toàn bộ test backend trước mỗi commit, và `verify.ps1` phải đạt trước khi mở PR.

## Nội dung chuỗi

**Lưu ở đâu:** trong repo, dạng tệp cấu hình công khai, ví dụ `config/value-chains.json`. Nội dung là kiến thức công khai, không phải dữ liệu cá nhân, nên được commit và review như code.

**Mỗi chuỗi gồm:**
- mã định danh, tên hiển thị, ngành ICB cấp 2 gốc, danh sách mã thuộc chuỗi;
- ba khâu `input`, `middle`, `output`; mỗi khâu là danh sách mục (tên, mô tả ngắn, tỷ trọng nếu nguồn có nêu, nguồn);
- danh sách yếu tố vĩ mô (xem dưới);
- ngày soạn và phiên bản nội dung.

**Mỗi yếu tố vĩ mô gồm:**
- khâu bị tác động (`input`, `middle` hoặc `output`) và mục cụ thể nếu có;
- chỉ số đã lưu tương ứng, lấy trong 17 chỉ số của `config/macro-indicators.json`; hoặc `null` nếu ứng dụng chưa có chuỗi số liệu (ví dụ giá than, quặng sắt, giá thép, giá urê, giá cao su);
- chiều tác động: chỉ số **tăng** thì tốt hay xấu cho ngành;
- mức quan trọng **chính / phụ / nhỏ**, lý do chọn mức, và tỷ trọng gốc nếu nguồn có nêu;
- nguồn.

**Soạn nội dung (một lần, khi làm tính năng):**
- Người làm đọc báo cáo công khai và ghi lại từng mục kèm nguồn.
- Ưu tiên báo cáo ACBS ngành và doanh nghiệp của chính các mã trong chuỗi, sau đó đến báo cáo thường niên của các mã đó.
- Mỗi chuỗi kèm một danh sách nguồn đã dùng để chủ sở hữu tự mở kiểm tra.

## Cách tính tốt/xấu

1. **Chỉ số có quy tắc riêng thì dùng lại quy tắc đang có trong `macro-indicators.json`** (người làm quyết, 30/10/2026):
   - PMI đọc "lên" khi ≥ 50 và không giảm, "xuống" khi < 50 và không tăng, còn lại là "đi ngang";
   - khối ngoại đọc theo dấu của tổng ròng 20 phiên.
   Các chỉ số khác đọc theo mục 2.
2. **Chiều đi của chỉ số:** dùng lại cách của "Chuỗi tác động vĩ mô" (`domain/macro_chain.py`): so điểm mới nhất với điểm cách khoảng một tháng; trong một ngưỡng nhỏ thì coi là "đi ngang". Mỗi chỉ số cần ngưỡng riêng (biến động theo tỷ lệ cho giá, theo điểm phần trăm cho lãi suất và CPI). Chọn ngưỡng cụ thể cho từng chỉ số là việc của người làm, ghi rõ trong code, hiện được trên trang.
3. **Kết quả của từng yếu tố** là một trong bốn:
   - **tốt:** chỉ số đi theo chiều có lợi;
   - **xấu:** chỉ số đi theo chiều bất lợi;
   - **trung tính:** chỉ số đi ngang;
   - **chưa đánh giá được:** không có chỉ số, chưa có số liệu, hoặc số liệu quá cũ (dùng ngưỡng "cũ" sẵn có của từng chỉ số).
4. **Trọng số:**
   - **chính = 3, phụ = 2, nhỏ = 1**;
   - nguồn nêu tỷ trọng thì quy về mức như sau, tính trên điểm giữa nếu tỷ trọng là một khoảng: **≥ 25% là chính, 10–25% là phụ, < 10% là nhỏ**. Tỷ trọng gốc vẫn hiện bên cạnh;
   - nguồn không nêu số (thường gặp ở phía đầu ra) thì người soạn gán mức kèm lý do, và chủ sở hữu duyệt mức này cùng chuỗi.
   - Vì đầu vào và đầu ra không cùng thang đo, cả hai đều được quy về ba mức trước khi cộng.
5. **Thanh tốt/xấu của thẻ:** phần trăm trọng số của tốt, xấu, trung tính và chưa đánh giá được. Ví dụ: "tốt 55% · xấu 15% · trung tính 0% · chưa đánh giá được 30%".
6. **Nhãn tổng của thẻ** (mỗi thẻ một nhãn):
   - **Thuận gió:** tốt − xấu ≥ 20 điểm phần trăm;
   - **Ngược gió:** xấu − tốt ≥ 20 điểm phần trăm;
   - **Trung tính:** các trường hợp còn lại;
   - **Chưa đủ dữ liệu:** phần chưa đánh giá được > 50%. Nhãn này ưu tiên hơn ba nhãn trên.

## Giao diện

**Vị trí:** mục mới "Chuỗi giá trị" trong trang Thị trường & Ngành, đặt dưới mục "Diễn biến theo ngành" hiện có.

**Thẻ tổng quan:**
- Mỗi chuỗi một thẻ, gồm tên, thanh tốt/xấu, nhãn tổng và số mã theo dõi.
- Thẻ có mã đang nắm thì hiện dấu "Đang nắm".
- Thứ tự thẻ: Thuận gió → Trung tính → Ngược gió → Chưa đủ dữ liệu; trong cùng nhãn, xếp theo (tốt − xấu) giảm dần.

**Bấm thẻ** thì mở sơ đồ ngay bên dưới, mỗi lúc chỉ mở một thẻ:
- ba cột Đầu vào → Trung gian → Đầu ra; trên màn hình hẹp, ba cột xếp dọc;
- mỗi mục có nguồn nhỏ bên dưới, bấm vào để mở tài liệu;
- mỗi yếu tố vĩ mô là một nhãn màu (xanh tốt, đỏ xấu, xám trung tính hoặc chưa đánh giá được), gắn vào đúng khâu. Nhãn ghi: tên chỉ số, chiều đi và mức thay đổi một tháng, mức quan trọng, và ngày của số liệu mới nhất;
- danh sách mã theo dõi trong chuỗi, mỗi mã là link tới Hồ sơ doanh nghiệp (`/research/<mã>`).

**Yêu cầu chung:**
- Không cuộn ngang ở màn hình rộng 375px.
- Màu không phải cách duy nhất để phân biệt tốt và xấu: nhãn có thêm chữ "tốt / xấu / …".

## Duyệt

- Tệp chuỗi có trạng thái cho từng chuỗi: **nháp** hoặc **đã duyệt**.
- Chủ sở hữu duyệt bằng cách xem nội dung, nguồn và mức quan trọng. Người làm chọn cách cụ thể, theo một trong hai hướng:
  - duyệt trong ứng dụng, giống luồng duyệt danh sách nghiên cứu, gắn với phiên bản nội dung; sửa nội dung thì phải duyệt lại;
  - duyệt qua review PR.
- Chuỗi nháp vẫn hiện trên trang, nhưng có nhãn "Chưa duyệt" và không có nhãn tổng.

## Kiểm thử

- Quy tắc tốt/xấu, trọng số và nhãn tổng: test đơn vị với số liệu tổng hợp, gồm cả trường hợp thiếu số liệu, số liệu cũ, chỉ số đi ngang, và tỷ trọng ở ranh giới 10% và 25%.
- Tệp chuỗi: test kiểm tra cấu trúc. Mỗi mục và mỗi yếu tố đều có nguồn; mỗi chỉ số được nhắc tới có thật trong `macro-indicators.json`; mỗi mã thuộc đúng một chuỗi; mỗi mã trong danh sách theo dõi có chuỗi.
- API và giao diện: test route và test e2e trên dữ liệu tổng hợp, gồm thứ tự thẻ, mở sơ đồ, link tới Hồ sơ doanh nghiệp, và không cuộn ngang ở 375px.

## Để người làm quyết

- Ngưỡng "đi ngang" cụ thể của từng chỉ số.
- Danh sách chuỗi con cuối cùng, theo nguyên tắc ở mục "Mục tiêu".
- Danh sách theo dõi và tệp chuỗi lệch nhau (người làm quyết, 30/10/2026):
  - khi chạy, mã đang theo dõi mà chưa có chuỗi hiện thành thông báo "chưa có chuỗi giá trị" trên trang;
  - test kiểm tra độ phủ dựa trên bản sao danh sách 50 mã trong spec này, vì `data\` không có trong Git.
- Cấu trúc chính xác của tệp cấu hình và của API.
- Cách duyệt cụ thể, trong hai hướng ở mục "Duyệt".
- Bố cục chi tiết, miễn là theo kiểu C và các yêu cầu ở mục "Giao diện".
