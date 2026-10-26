# Thiết kế: phần "Thị trường phiên" trong Bản tin sau phiên

Ngày: 26/10/2026 · Trạng thái: chờ chủ sở hữu duyệt

## Mục đích

Chủ sở hữu đọc bản tin sau phiên để biết nhanh phiên vừa rồi diễn ra thế nào. Bản tin hiện tại chủ yếu là bảng danh mục, cùng vài mục lặp lại và mã kỹ thuật khó hiểu. Chủ sở hữu muốn **đầu bản tin** trả lời theo thứ tự:

1. VN-Index, VN30, các mã đang theo dõi và các ngành tăng/giảm bao nhiêu **điểm** và bao nhiêu **%**.
2. Tổng giá trị giao dịch trong phiên.
3. Số mã tăng, giảm, đứng giá.
4. Khối ngoại: khối lượng và giá trị mua, bán.
5. Tự doanh: khối lượng và giá trị mua, bán.
6. Tin nóng, quan trọng về vĩ mô, ngành, cổ phiếu.

## Nguồn dữ liệu (đã kiểm tra 26/10/2026, đều miễn phí, chỉ đọc)

| Mục | Nguồn | Ghi chú |
|---|---|---|
| VN-Index, VN30 | Vnstock (giá chỉ số; ứng dụng đã lưu `VNINDEX-1d`, `VN30-1d`) | điểm = đóng cửa phiên − đóng cửa phiên trước |
| Mã theo dõi | Giá đã lưu của 50 mã (`data/market-symbols.txt`) | |
| Ngành, số mã tăng/giảm, khối ngoại theo mã, tổng giá trị | **Bảng giá cả sàn Vnstock** `Trading.price_board`: 407 mã cổ phiếu HOSE trong **một lần gọi** | chạy được ở gói Cộng đồng. Có giá tham chiếu, giá khớp, khối lượng và giá trị khớp lũy kế, khối ngoại mua/bán (khối lượng, giá trị) theo từng mã. Ngành lấy theo mã ICB cấp 2 của `Listing.symbols_by_exchange`. Phiên 26/10: 107 tăng, 205 giảm, 65 đứng giá, 30 không giao dịch |
| Tổng giao dịch và khối ngoại toàn sàn (đối chiếu) | Dịch vụ thống kê HOSE `api.hsx.vn/mk/api/v1/market/...` (`foreign-trading-value-report`, `foreign-trading-volumn-report`, `summary/hompage`) | ứng dụng đã dùng nguồn này. Báo cáo khối ngoại của phiên **chưa có lúc 16:13 cùng ngày**, có lẽ đăng sáng hôm sau |
| Tự doanh | **Chưa có nguồn miễn phí hợp lệ** | Vnstock chặn ở gói Cộng đồng; HOSE không công bố; trang của CafeF đã gỡ; Vietstock tải số bằng JavaScript và có mã chống tự động (không vượt qua). **Chủ sở hữu chọn ghi "chưa có nguồn miễn phí".** |
| Tin tức | RSS **CafeF** (`thi-truong-chung-khoan.rss`, `vi-mo-dau-tu.rss`), **Vietstock** (`830/chung-khoan/co-phieu.rss`, `761/kinh-te/vi-mo.rss`), **Vneconomy** (`chung-khoan.rss`) | robots.txt cho phép. Chỉ lấy tiêu đề, link và thời gian. **Không dùng VnExpress** (robots chặn). Vnstock đã ngừng hỗ trợ tin tức |

## Bản tin mới, theo thứ tự

### A. Thị trường phiên dd/mm (phần mới, ở đầu)
1. **Chỉ số:** VN-Index và VN30: đóng cửa, ± điểm, ± %.
2. **Thanh khoản:** tổng giá trị giao dịch HOSE (tỷ đồng), có thể kèm khối lượng.
3. **Độ rộng:** số mã tăng / giảm / đứng giá trên toàn HOSE. Mã không giao dịch được ghi riêng.
4. **Khối ngoại:**
   - mua, bán và ròng, cả khối lượng lẫn giá trị;
   - **3 mã bán ròng mạnh nhất và 3 mã mua ròng mạnh nhất** (theo giá trị).
5. **Tự doanh:** dòng "Chưa có nguồn miễn phí".
6. **Ngành:** % tăng/giảm của từng ngành ICB cấp 2 **trên toàn HOSE**, xếp từ tăng mạnh nhất đến giảm mạnh nhất.
7. **Mã đang theo dõi:**
   - Mỗi mã có giá, ± giá và ± %.
   - **Mã đang nắm đứng đầu**, sau đó là các mã biến động mạnh nhất. Các mã còn lại thu gọn ("xem thêm").
8. **Tin nóng:** tối đa **8 tin** trong khoảng từ phiên trước đến lúc lập bản tin.
   - Mỗi tin có tiêu đề, nguồn, giờ và link.
   - Lọc **trên máy, không dùng AI**. Một tin được giữ khi tiêu đề có: mã đang theo dõi hoặc đang nắm, tên ngành của các mã đó, hoặc từ khóa vĩ mô (lãi suất, tỷ giá, Fed, GDP, CPI, lạm phát, NHNN, FED, thuế quan, xuất khẩu…).
   - Tin nhắc mã đang nắm được xếp trước.
   - Tin trùng (cùng tiêu đề từ nhiều nguồn) chỉ giữ một.

### B. Danh mục (giữ)
- Bảng lãi/lỗ các mã đang nắm như hiện nay, **bỏ cột "Phạm vi"**.

### C. Gọn lại các mục cũ
- **"Cơ hội và cảnh báo":**
  - Khi mọi mã cùng một lý do (ví dụ "Mã ngoài danh sách nghiên cứu đã duyệt…"), chỉ ghi **một dòng**.
  - Mã nào có lý do riêng thì vẫn liệt kê riêng.
- **"Nhận định (số liệu đã kiểm chứng, không dùng AI)":** bỏ, vì trùng với bảng Danh mục.
- **"Kiểm tra dữ liệu":**
  - Chuyển xuống cuối, chữ nhỏ.
  - Mã kỹ thuật được viết thành câu tiếng Việt. Ví dụ `universe_incomplete` thành "Danh sách nghiên cứu chưa hoàn tất".

### D. Telegram (bản rút gọn)
- Gồm các mục A1 đến A6.
- Tối đa 3 mã đang nắm (giá, ± %).
- Tối đa 5 tin nóng.
- Dòng cuối: "Xem bản đầy đủ trong ứng dụng, mục Bản tin sau phiên" (không gửi link, xem quyết định 11).
- Vẫn theo cài đặt "Gửi tự động theo lịch" hiện có.

## Điều không được xảy ra
- **Không có khuyến nghị mua bán.** Phần thị trường chỉ là số liệu.
- **Không ghi số đoán.**
  - Thiếu nguồn thì ghi rõ "chưa có số liệu" kèm lý do (ví dụ "HOSE chưa công bố").
  - Không lấy số phiên trước điền thay phiên này.
  - Mỗi con số ghi rõ phiên của nó.
- **Không gửi dữ liệu cá nhân ra ngoài.** Lọc tin làm trên máy. Không gọi AI cho phần này.
- **Không đăng nhập, không vượt mã chống tự động, không dùng nguồn bị robots.txt chặn.**
- **Một nguồn hỏng không làm hỏng bản tin.**
  - Mỗi mục báo lỗi riêng.
  - Phần danh mục vẫn phát hành như hiện nay.
  - Phần thị trường thiếu dữ liệu không làm bản tin chuyển sang "chưa đủ dữ liệu".

## Ràng buộc
- **Giới hạn Vnstock:** gói Cộng đồng chỉ cho 60 lần gọi/phút. Bảng giá cả sàn chỉ cần 1 lần gọi (tối đa 500 mã mỗi lần). Danh sách mã và ngành chỉ cần làm mới hằng tuần, cùng lúc với `industries`.
- **Thời điểm:**
  - Bản tin lập ở lượt 15:30 (hoặc lượt sau đó nếu giá chưa về).
  - Số liệu phiên lấy từ bảng giá cả sàn, có ngay sau giờ đóng cửa.
  - Báo cáo khối ngoại của HOSE thường chưa có trong ngày, nên chỉ dùng để đối chiếu khi đã có. Không chờ báo cáo này.
- **Lưu trữ:**
  - Ảnh chụp số liệu thị trường của phiên lưu **trên máy** trong `data/` (dữ liệu công khai).
  - Bản tin trong Firestore chỉ chứa phần đã tính sẵn để hiển thị, cùng danh mục như hiện nay.
- Theo quy trình hiện có: TDD, `verify.ps1`, PR, chủ sở hữu duyệt rồi mới merge.

## Quyết định của người viết (chủ sở hữu có thể đổi)
1. **Số liệu trong phiên lấy từ bảng giá cả sàn của Vnstock**, không chờ HOSE: báo cáo khối ngoại HOSE chưa có lúc 16:13. Khi HOSE có số, trang bản tin hiện số HOSE bên cạnh để đối chiếu; bản Telegram đã gửi thì không sửa.
2. **"Ngành" tính trên toàn HOSE.** Mỗi ngành ICB cấp 2 lấy **trung bình % của các mã có giao dịch**, không gia quyền vốn hóa, để dễ hiểu và khớp cách trang Thị trường đang làm. Ghi kèm số mã của ngành.
3. **Điểm của VN30** lấy từ chuỗi giá `VN30-1d` đã có.
4. **Khoảng thời gian lấy tin:** từ 15:00 phiên trước đến lúc lập bản tin. Tối đa 8 tin trong ứng dụng, 5 tin trên Telegram.
5. **Tổng giá trị giao dịch:** dùng tổng giá trị khớp lệnh cộng thỏa thuận nếu bảng giá có cả hai; nếu không, ghi rõ "khớp lệnh". Khi HOSE đã công bố thì hiện thêm con số của HOSE.
6. **Bản tin cũ không bị sửa.** Phần mới chỉ có ở bản tin từ nay về sau. Bản cũ giữ nguyên nhưng vẫn ẩn cột "Phạm vi" và các mục đã bỏ, vì đó chỉ là cách hiển thị.
7. **Mục "Kết luận"** giữ nguyên ở đầu phần Danh mục, đổi tên thành "Danh mục: kết luận".
8. **Phần thị trường không nằm trong bản tin ở Firestore.**
   - Mỗi phiên có một tệp ảnh chụp số liệu trên máy, `data/` (ví dụ `data/brief/<ngày phiên>.json`).
   - Trang bản tin đọc tệp đó **mỗi khi mở**, theo ngày phiên của bản tin.
   - Vì vậy:
     - bản tin trong Firestore vẫn ghi một lần như hiện nay;
     - mã của bản tin không đổi khi số liệu thị trường về muộn, nên không tạo bản tin thứ hai và không gửi Telegram lần hai;
     - số HOSE về sáng hôm sau, hoặc mục còn thiếu lúc 15:30, sẽ tự hiện khi một lượt chạy sau cập nhật tệp ảnh chụp.
   - Lượt chạy hiện có cập nhật tệp ảnh chụp của phiên gần nhất **mỗi lần thức dậy**. Lượt 07:00 hôm sau sẽ bổ sung số HOSE.
9. **Telegram chỉ gửi một lần**, với những gì có lúc gửi. Mục nào chưa có thì ghi "chưa có số liệu", không gửi bổ sung.
10. **Nội dung Telegram, ngoài mục D:**
    - Giữ **một dòng kết luận danh mục**.
    - Giữ **lời nhắc cập nhật số liệu vĩ mô**, vì chủ sở hữu đã yêu cầu có lời nhắc này trong Telegram.
    - Bỏ hành động theo từng mã (trùng nhau) và các mã kiểm tra dữ liệu.
11. **Không có link trong Telegram:** ứng dụng chỉ chạy trên máy (`127.0.0.1:3000`), nên link mở từ điện thoại sẽ không vào được. Dòng cuối ghi "Xem bản đầy đủ trong ứng dụng, mục Bản tin sau phiên".
12. **"Mã đang theo dõi"** là danh sách trong `data/market-symbols.txt`; trang Theo dõi (`load_watchlist`) cũng đọc đúng tệp này. **Mã đang nắm nhưng ngoài danh sách vẫn hiện** ở mục A7 (đứng đầu) và vẫn dùng để lọc tin.
13. **Bảng giá phải đúng phiên.**
    - Ảnh chụp chỉ ghi số từ bảng giá khi ngày giao dịch trên bảng (`trading_date`) trùng ngày phiên của bản tin.
    - Nếu không trùng (ví dụ lượt chạy bù sau 09:00 hôm sau), các mục lấy từ bảng giá ghi "chưa có số liệu cho phiên này".
    - Chỉ số (A1) vẫn có vì lấy từ chuỗi giá đã lưu. Số HOSE vẫn bổ sung được vì HOSE tra cứu theo ngày.

## Để người lập trình quyết định
- Tên module, hàm, API, cách lưu ảnh chụp số liệu trong `data/`.
- Cột cụ thể của bảng giá dùng cho giá trị khớp lệnh và thỏa thuận.
- Danh sách từ khóa vĩ mô cụ thể và cách bỏ tin trùng.
- Bố cục chi tiết, miễn không cuộn ngang trên điện thoại.

## Tiêu chí hoàn thành
- Bản tin mới có đủ phần A theo đúng thứ tự, với số liệu thật của một phiên. Chạy thử trên phiên gần nhất và đối chiếu vài con số với trang HOSE hoặc CafeF.
- Bỏ cột "Phạm vi"; gọn các mục ở phần C.
- Telegram rút gọn đúng mục D.
- Có kiểm thử cho:
  - tính điểm và % của chỉ số;
  - độ rộng thị trường;
  - khối ngoại (tổng và 3+3 mã);
  - % theo ngành;
  - thứ tự mã theo dõi;
  - lọc, xếp và bỏ trùng tin;
  - từng nguồn hỏng thì mục đó báo "chưa có số liệu", còn bản tin vẫn ra;
  - bản Telegram;
  - trang không cuộn ngang ở 375px.
- `verify.ps1` đạt.
