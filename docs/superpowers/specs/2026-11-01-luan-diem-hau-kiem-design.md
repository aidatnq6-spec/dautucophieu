# Luận điểm đầu tư và Hậu kiểm quyết định

Ngày: 01/11/2026 · Trạng thái: chủ sở hữu đã đồng ý cách làm trong trao đổi; chờ duyệt bản này

## Vì sao

Chủ sở hữu kể lần gần nhất: mã đang lỗ, không bán vì sợ lỗ. Khi mua, họ dựa vào giá rẻ so với định giá, kết quả kinh doanh tốt, xu hướng
giá đẹp, câu chuyện ngành — và cả sợ bỏ lỡ khi thấy người khác có lời. Điều họ cần nghe đúng lúc đó: **vì sao cần bán, nếu không bán thì
hậu quả là gì, sẽ lỗ nặng thêm bao nhiêu.**

Hai phần làm cùng nhau:
1. **Luận điểm đầu tư** — lúc còn tỉnh táo, ghi lý do mua và điều kiện đo được cho biết mình đã sai; phần mềm tự đối chiếu và báo.
2. **Hậu kiểm quyết định** — đo bằng số các quyết định đã qua của chính chủ sở hữu, để thấy giá của thói quen "giữ vì sợ lỗ".

## Mục tiêu, không làm, và điều tránh

- Mục tiêu: mỗi lần giữ một mã đã phá luận điểm là một **quyết định có ghi lại**, không phải sự im lặng; mỗi lời nhắc có số thật.
- Không làm: không đặt lệnh, không khuyến nghị mua/bán, không dự báo giá.
- Điều tránh (thất bại dù chạy đúng):
  - Viết hay ngụ ý "sẽ lỗ thêm X". Không ai biết; quy tắc dự án là không đoán số. Chỉ đưa số đã xảy ra và kịch bản lịch sử có ghi rõ là kịch bản.
  - Kết luận thiên kiến từ quá ít quan sát.
  - Gửi danh mục, sổ giao dịch, luận điểm hay Nhật ký cho AI. Mọi thứ tính trên máy; Telegram chỉ gửi cho chủ sở hữu.
  - Một nút "tắt nhắc" không cần lý do.

## Phần 1: Luận điểm đầu tư

### Nội dung một luận điểm
Mỗi mã **đang nắm** (theo sổ giao dịch) có tối đa một luận điểm đang mở:
- **Lý do mua** (chọn một hay nhiều): Giá rẻ so với định giá · Kết quả kinh doanh tốt · Xu hướng giá đẹp · Câu chuyện ngành · Sợ bỏ lỡ.
- **Lời của chủ sở hữu**: một đoạn tự viết "vì sao mua, điều gì xảy ra thì tôi sai". Đoạn này được trích lại nguyên văn trong lời nhắc.
- **Điều kiện** (một hay nhiều), mỗi điều kiện có tham số do chủ sở hữu đặt:

| Loại | Điều kiện bị phá khi | Dữ liệu có sẵn |
|---|---|---|
| Lỗ so với giá vốn | Giá hiện tại ≤ giá vốn bình quân × (1 − X%) | Sổ giao dịch, bảng giá |
| Giá dưới mức | Giá đóng cửa < mức đặt | Bảng giá / giá đóng cửa đã lưu |
| Hết rẻ | Giá ≥ mức hợp lý × (1 + X%) — luận điểm "rẻ" đã xong | Định giá tham khảo |
| Mức hợp lý bị hạ | Mức hợp lý mới thấp hơn mức lúc đặt luận điểm quá X% | Định giá tham khảo |
| F-Score | F-Score năm gần nhất ≤ n (phi tài chính) | Chất lượng báo cáo |
| Điểm sức khỏe | Ngân hàng/chứng khoán/bảo hiểm: "yếu" | Điểm sức khỏe |
| Lợi nhuận quý | Lợi nhuận sau thuế quý giảm so với cùng kỳ n quý liên tiếp | Chỉ số ngành theo quý / báo cáo đã lưu |
| MACD tuần | MACD tuần cắt xuống đường tín hiệu | Nến tuần (gộp từ nến ngày) |
| Chuỗi giá trị | Chuỗi giá trị của ngành chứa mã chuyển sang "xấu" | Chuỗi giá trị |
| Nội bộ bán | Có thông báo người nội bộ/cổ đông lớn bán (mới, sau ngày đặt) | Giao dịch nội bộ (HOSE qua VNDirect) |

- Chọn lý do **Sợ bỏ lỡ** thì **bắt buộc** có điều kiện "Lỗ so với giá vốn" trước khi lưu.
- Thiếu dữ liệu cho một điều kiện (ví dụ mã chưa có F-Score) thì điều kiện ở trạng thái **"chưa kiểm được"** kèm lý do — không coi là đạt,
  không coi là phá. Không chọn được điều kiện không áp dụng cho loại doanh nghiệp (F-Score cho ngân hàng…).
- Lúc lưu, phần mềm ghi **ảnh chụp** số liệu nền (giá, giá vốn, mức hợp lý, F-Score… mỗi số có thể thiếu) để so sánh về sau.
- Luận điểm khép lại khi mã về 0 cổ phiếu trong sổ; lưu lại để hậu kiểm, không xóa.
- Mã đang nắm chưa có luận điểm: hiện "Chưa có luận điểm" trên trang và một dòng trong Bản tin tuần.
- Lưu ở kho cá nhân, có phiên bản chống ghi đè như các bản ghi khác. Ghi luận điểm cũng tạo một mục Nhật ký loại "buy" (hoặc liên kết với
  mục đã có của lệnh mua) để lý do mua nằm một chỗ.

### Kiểm tra
- "Lỗ so với giá vốn": giá khớp mới nhất, mỗi 5 phút trong phiên cùng lượt Cảnh báo giá; giá chưa khớp thì không kiểm.
- "Giá dưới mức": **giá đóng cửa** (tránh nhiễu trong phiên), kiểm trong lượt sau giờ đóng cửa; thống kê "tình trạng tương tự" cũng theo
  giá đóng cửa.
- Điều kiện theo dữ liệu (còn lại): trong lượt sau giờ đóng cửa, sau bước cập nhật số liệu lúc 20:00.
- "Chuỗi giá trị chuyển sang xấu" = nhãn "bất lợi" (headwind) của chuỗi đã duyệt; mã thuộc nhiều chuỗi thì **một** chuỗi bất lợi là đủ.
  Chuỗi chưa duyệt hoặc thiếu dữ liệu: "chưa kiểm được".
- Mỗi lần kiểm ghi trạng thái từng điều kiện: đạt / bị phá (kèm ngày, số đo) / chưa kiểm được (kèm lý do).

### Trạng thái của một điều kiện (quyết định của người làm)
- **Đã bị phá thì giữ trạng thái bị phá**, kể cả khi số đo hồi lại (giá lên lại, F-Score cải thiện): trang hiện thêm số đo hiện tại,
  nhưng lời nhắc không tự tắt — hy vọng giá hồi chính là lý do của thói quen cần sửa. Trạng thái chỉ đổi khi luận điểm khép (về 0 cổ phiếu)
  hoặc chủ sở hữu chọn "Giữ tiếp, có lý do" cho điều kiện đó.
- Mỗi điều kiện bị phá là **một lần** trong hậu kiểm, tính từ ngày và giá lúc báo đầu tiên.
- **Lưu luận điểm khi điều kiện đã bị phá sẵn** (ví dụ mã đang lỗ sâu ngay hôm đặt): vẫn lưu được; điều kiện ghi "bị phá ngay lúc đặt",
  lời nhắc gửi ngay, mốc tính là ngày và giá lúc lưu.
- **Sửa**: điều kiện chưa bị phá sửa tự do. Điều kiện đã bị phá chỉ thay đổi qua "Giữ tiếp, có lý do" (không có đường sửa/xóa không lý do).
  Mỗi lần sửa tạo phiên bản mới; phiên bản cũ, ảnh chụp và lịch sử bị phá được giữ cho hậu kiểm.

### Lời nhắc khi điều kiện bị phá (Telegram, chỉ khi "gửi theo lịch" đang bật)
Gửi một lần khi điều kiện chuyển sang bị phá. Ba phần:
1. **Vì sao cần xem lại**: điều kiện chủ sở hữu đã đặt, số đo hiện tại và lúc đặt; trích nguyên văn lời của họ.
2. **Nếu giữ tiếp — kịch bản từ lịch sử, không phải dự báo**:
   - Đợt giảm sâu nhất từng có của mã (Kế hoạch sụt giảm, toàn bộ lịch sử đã lưu): −X%. Nếu lặp lại từ giá hiện tại, vị thế hiện tại
     lỗ thêm Y đồng. Ghi rõ "kịch bản nếu lặp lại, không phải dự báo".
   - Với điều kiện có lịch sử tính được (F-Score, MACD tuần, giá dưới mức): những lần trước mã này rơi vào tình trạng tương tự, giá 6 tháng
     sau thay đổi trung vị bao nhiêu, trên bao nhiêu lần. Dưới 5 lần: "chưa đủ lần để thống kê".
3. **Bài học của chính bạn** (từ Phần 2): những lần trước bạn giữ sau khi luận điểm bị phá, kết quả so với bán ngay. Dưới 5 lần: không
   hiện dòng này.

Kết bằng: "Không phải khuyến nghị. Phần mềm không đặt lệnh."

### Nhắc lại khi chưa bán
- **Bản tin tuần**: mục "Luận điểm đã bị phá mà vẫn đang giữ": mỗi mã, ngày báo đầu tiên và **số đã xảy ra từ đó** (thay đổi giá %, lãi/lỗ
  của vị thế hiện tại bằng đồng).
- **Nhắc thêm** khi giá giảm thêm mỗi 5% so với giá lúc báo đầu tiên (mỗi bậc một lần).
- Nhắc dừng chỉ khi:
  - **Đã bán**: chủ sở hữu nhập lệnh bán vào sổ như thường lệ; luận điểm khép khi về 0 cổ phiếu (bán một phần thì vẫn mở).
  - **Giữ tiếp, có lý do**: bắt buộc viết lý do (lưu thành mục Nhật ký loại "hold", kèm cảm xúc) **và** đặt điều kiện mới hoặc ngày xem lại.
    Áp cho **từng điều kiện** bị phá: điều kiện mới **thay** điều kiện đó (bản cũ giữ trong lịch sử); nhắc bậc 5% và dòng Bản tin tuần của
    điều kiện đó dừng đến khi điều kiện mới bị phá hoặc đến ngày xem lại (tối đa 90 ngày). Các điều kiện khác của luận điểm vẫn kiểm và
    báo bình thường.
- Mọi lần "Giữ tiếp" được lưu để hậu kiểm.

### Quan hệ với tính năng đã có
- Kế hoạch sụt giảm vẫn giữ lời nhắc riêng khi mã đang nắm giảm quá ngưỡng chung so với giá vốn (không đổi). Điều kiện "Lỗ so với giá vốn"
  của luận điểm là ngưỡng riêng của từng mã.
- Cảnh báo giá, Nhật ký, Bản tin tuần giữ nguyên hành vi; chỉ thêm mục mới.

## Phần 2: Hậu kiểm quyết định

Tính trên máy từ sổ giao dịch, Nhật ký, luận điểm và giá đóng cửa đã lưu (toàn bộ lịch sử). Mốc: 3, 6, 12 tháng (ngày giao dịch gần nhất
không sau mốc). Chưa tới mốc: "chưa tới". Thiếu giá: "thiếu giá" kèm lý do.

1. **Lệnh mua**: thay đổi giá của mã sau 3/6/12 tháng so với giá mua; VN-Index cùng khoảng; chênh lệch.
2. **Lệnh bán**: giá đi tiếp ra sao sau khi bán (3/6/12 tháng) — để thấy bán đúng lúc hay bán non. So với VN-Index cùng khoảng.
3. **Giữ khi đang lỗ**: những khoảng một mã lỗ quá ngưỡng của Kế hoạch sụt giảm mà vẫn giữ — kéo dài bao lâu, kết thúc ra sao (hồi về giá
   vốn / bán lỗ / vẫn đang giữ). Dùng ngưỡng hiện tại cho mọi khoảng trong quá khứ (phần mềm không lưu lịch sử ngưỡng); ghi rõ trên trang.
4. **Luận điểm bị phá**: mỗi lần bị phá, so "giữ" (giá hiện tại hoặc giá bán sau đó) với "bán ngay tại ngày báo đầu tiên". Gồm cả các lần
   "Giữ tiếp, có lý do".
5. **Thiên kiến**, mỗi dòng có số lần quan sát; dưới 5 lần thì "chưa đủ dữ liệu để kết luận", không nhận xét:
   - **Bán lời sớm, giữ lỗ lâu** (Odean): tại mỗi ngày bán, đếm vị thế lãi/lỗ đã chốt và đang để; so tỷ lệ chốt lãi (PGR) với tỷ lệ chốt lỗ
     (PLR). Lãi/lỗ theo giá vốn bình quân của sổ.
   - **Theo lý do mua và cảm xúc**: kết quả 6 tháng trung bình của lệnh mua theo lý do (luận điểm) và cảm xúc (Nhật ký).
   - **Mua đuổi**: lệnh mua sau khi mã tăng hơn 15% trong 20 phiên trước đó, so với các lệnh mua khác.
- Vị thế mở đầu (số dư đầu kỳ, không có ngày mua) không vào hậu kiểm lệnh mua; ghi rõ số vị thế bị bỏ qua.
- Không phí, thuế trong so sánh giá (ghi rõ); số tiền lãi/lỗ thực của vị thế lấy từ sổ.

## Giao diện (quyết định của người làm)
- **Danh mục & Giao dịch**: mục "Luận điểm đầu tư" — mỗi mã đang nắm một thẻ: lý do, lời đã viết, từng điều kiện với trạng thái
  (đạt / bị phá / chưa kiểm được), nút Sửa; khi bị phá có nút "Giữ tiếp, có lý do". Mã chưa có luận điểm ghi rõ.
- **Nhật ký**: mục "Hậu kiểm quyết định" với các bảng của Phần 2.
- Ngôn ngữ, định dạng số và cách ghi "thiếu" như các trang khác.

## Ràng buộc
- Không gửi gì cho AI. Telegram chỉ gửi khi "gửi theo lịch" đang bật, như các cảnh báo khác.
- Không đặt lệnh, không khuyến nghị; mỗi lời nhắc kết bằng câu "Không phải khuyến nghị".
- Giới hạn nguồn: không gọi thêm nguồn ngoài; dùng dữ liệu các lượt hiện có đã lưu.
- Test chỉ dùng số liệu tổng hợp; không chép số liệu cá nhân vào code, test, commit.

## Để người làm quyết định
- Cấu trúc lưu trữ, tên endpoint, cách chia module; cách tính "tình trạng tương tự" cho từng loại điều kiện có lịch sử.
- Có thể giao hai phần thành hai PR (Phần 1 trước), miễn lời nhắc không hiện dòng "bài học của chính bạn" khi Phần 2 chưa có.
