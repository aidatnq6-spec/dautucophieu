# Lãi đã trả lại thị trường và Mục tiêu đã đủ tiền (24/11/2026)

Chủ sở hữu duyệt ngày 24/11/2026 (cổ tức tính theo giá điều chỉnh; ngưỡng A, B để trống đến khi đặt ở Cài đặt). Kaizen từ podcast "Đỉnh – Đáy" (Nguyễn Trần Hải, Trần Quang Hiến), mục 4.1: lãi tạm tính 80 tỷ trả
lại gần hết vì chờ thêm, và chuyện lùi mua chiếc xe đã đủ tiền mua để chờ giá lên 300. Hai khối mới ở trang Danh mục & Giao dịch, ngay sau
Kế hoạch sụt giảm. Dữ liệu cá nhân, tính trên máy, không gửi cho AI. Chỉ đưa số đã xảy ra: không nói nên bán, không dự báo.

## Cách tính lãi của một ngày (chung cho hai khối)
- Dùng đúng cách Hậu kiểm quyết định đã dùng cho "Giữ khi đang lỗ" (`domain/hindsight.py`, `_Book`): giá đã lưu là giá điều chỉnh, nên
  giá của một phiên chỉ được so với giá vốn điều chỉnh (bình quân giá đóng cửa điều chỉnh của các ngày mua còn nắm).
- Tỷ lệ lãi ngày d = giá đóng cửa điều chỉnh ngày d ÷ giá vốn điều chỉnh ngày d − 1. Lãi ngày d (đồng) = tỷ lệ đó × giá vốn thật đang nắm
  ngày d (sổ giao dịch). Vì giá điều chỉnh đã tính cổ tức, số này gồm cả cổ tức tiền và cổ phiếu thưởng đã nhận, nên có thể khác cột "Lãi
  chưa chốt" của bảng danh mục; trang ghi rõ điều này.
- Chỉ tính phiên có giá đóng cửa đúng ngày đó. Ngày mua không có giá đã lưu thì mã ghi "chưa tính" kèm lý do, không lấp.

## Khối 1: Lãi đã trả lại thị trường
- Với mỗi mã đang nắm, trong **đợt nắm hiện tại** (từ lần số cổ phiếu đi từ 0 lên lớn hơn 0 gần nhất):
  - lãi cao nhất từng có (đồng và %), ngày đạt;
  - lãi hôm nay theo cùng cách tính;
  - phần đã trả lại = lãi cao nhất − lãi hôm nay (đồng), và bằng bao nhiêu % của lãi cao nhất;
  - số phiên từ ngày đạt lãi cao nhất.
  Lãi cao nhất không dương (chưa từng có lãi) thì ghi "chưa từng có lãi trong đợt nắm này", không có phần trả lại.
- **Cả danh mục**: cộng lãi từng ngày của các mã đang nắm hôm đó. Chỉ tính ngày mọi mã đang nắm hôm đó đều có giá; số ngày bị bỏ vì thiếu
  giá được ghi kèm. Chỉ là lãi chưa chốt của phần đang nắm; lãi đã chốt của mã đã bán không thuộc phép tính này.
- **Nhắc** (Telegram, trong tin gộp "Danh mục hôm nay", và một dòng ở Việc cần xem nhóm cần quyết định): khi một mã có lãi cao nhất từ
  mức tối thiểu A% giá vốn trở lên và đã trả lại từ B% lãi cao nhất trở lên. Chủ sở hữu tự đặt A và B ở Cài đặt danh mục; phần mềm không
  đặt sẵn, để trống thì không nhắc. Mỗi mã nhắc một lần mỗi đợt; chỉ nhắc lại sau khi phần trả lại đã xuống dưới B%. Trạng thái ở kho cá
  nhân `settings/giveback_alerts`. Tin nhắc nêu số đồng, % và ngày đạt lãi cao nhất, kèm lý do mua trong Luận điểm nếu có.

## Khối 2: Mục tiêu đã đủ tiền
- Chủ sở hữu ghi tối đa 10 mục tiêu chi tiêu: tên, số tiền (đồng), và cách đếm: **lãi chưa chốt của danh mục** hoặc **giá trị danh mục
  theo thị giá**. Lưu ở `settings/spend_goals` (ghi có phiên bản).
- Với mỗi mục tiêu, từ chuỗi ngày của Khối 1 (giá trị ngày d = giá vốn thật + lãi ngày d):
  - hôm nay đủ hay còn thiếu bao nhiêu đồng;
  - lần gần nhất bắt đầu đủ, đã đủ bao nhiêu ngày;
  - nếu từng đủ rồi lại thiếu: đủ từ ngày nào đến ngày nào, và mức cao nhất đã vượt mục tiêu bao nhiêu.
  Ngày tạo mục tiêu được ghi kèm; trạng thái trước ngày đó vẫn hiện nhưng ghi "trước khi bạn đặt mục tiêu".
- Nhắc một lần khi mục tiêu bắt đầu đủ, và một lần khi đã đủ rồi lại thiếu, theo lượt chạy lịch (Telegram như trên, cùng Việc cần xem).
- Chủ sở hữu bấm "đã thực hiện" hoặc "bỏ mục tiêu", có ghi ngày; mục tiêu đã đóng không còn nhắc nhưng còn trong danh sách.
- Không đụng Sổ tài sản, Tháp tài sản, Mục đích từng khoản tiền hay số tiền dành cho cổ phiếu.

## API và giao diện
- `GET /internal/giveback`: các mã, dòng cả danh mục, ngưỡng đang dùng, các lý do "chưa tính".
- `GET /internal/spend-goals`, `PUT /internal/spend-goals` (kèm `expected_version`).
- Ngưỡng A, B thêm vào `PUT` cài đặt danh mục hiện có (cạnh ngưỡng sụt giảm).
- Trang: bảng Lãi đã trả lại, xếp theo phần đã trả lại (đồng) giảm dần, kèm đường lãi theo ngày của mỗi mã khi mở dòng; khối Mục tiêu
  với ô nhập, trạng thái từng mục tiêu và dòng chú thích cách tính.

## Không làm
- Không tính khuyến nghị chốt lời, không ước "nếu bán ở đỉnh thì được bao nhiêu".
- Không đọc sổ giao dịch trước đợt nắm hiện tại cho Khối 1.
- Không gửi danh mục, mục tiêu hay số tiền cho AI.
