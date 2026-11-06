# Sổ tiền gửi, lịch đáo hạn và thanh khoản

Ngày: 05/11/2026 · Trạng thái: chủ sở hữu chọn mục 1 và 2 của đề xuất (học từ bảng tài sản VI-TECH), "viết spec trước, rồi làm theo
TDD"; các lựa chọn dưới đây là quyết định của người làm.

## Mục tiêu
Thay con số "Tiền gửi" nhập tay của Tháp tài sản bằng danh sách sổ tiết kiệm thật, để thấy tiền về tháng nào, và biết bao nhiêu tiền rút
được ngay so với quỹ dự phòng. Sổ chưa đến hạn hay đang phong tỏa không bao giờ được tính là tiền dùng ngay.

## Dữ liệu (`settings/deposit_book`, dữ liệu cá nhân, không gửi cho AI)
- **Tài khoản tiền mặt** ngoài tài khoản chứng khoán (tối đa 30): tên (≤ 60 ký tự), số tiền (đồng, ≥ 0), rút ngay được hay không.
- **Sổ tiền gửi** (tối đa 100): ngân hàng (≤ 40 ký tự), ngày đáo hạn, tiền gốc (đồng, > 0), lãi suất %/năm (tùy chọn, 0–30),
  lãi dự kiến khi đáo hạn (đồng, tùy chọn), cách trả lãi: **cuối kỳ** hoặc **đầu kỳ** (đã nhận khi mở sổ), phong tỏa đến hạn hay không.
- Lựa chọn **cộng tiền mặt sổ giao dịch** (mặc định có). Chủ sở hữu bỏ chọn khi các tài khoản đã là toàn bộ tiền mặt (05/11/2026: tiền
  trong tài khoản chứng khoán là iPower), để không đếm hai lần: lớp Tiền mặt và Rút ngay chỉ lấy các tài khoản; số của sổ giao dịch vẫn
  hiện, ghi "không cộng".
- **Trái phiếu và chứng chỉ quỹ, Vàng, Tiền số** (05/11/2026, chủ sở hữu yêu cầu; tối đa 30 dòng mỗi loại): tên (≤ 80 ký tự), số tiền
  (đồng, ≥ 0); trái phiếu thêm lợi suất kỳ vọng %/năm (tùy chọn, 0–30). Hiệu suất năm trước không tự điền thành lợi suất.
- Mục đổi tên thành **Sổ tài sản**.
- Mỗi dòng có mã do trình duyệt tạo; lưu cả danh sách một lần, có `expected_version` như các bản ghi khác.
- Ô bỏ trống là **chưa nhập**, không phải 0; không suy lãi từ lãi suất hay ngược lại.

## Lịch đáo hạn
- Gom sổ theo tháng đáo hạn: số sổ, tổng gốc, tổng lãi sẽ nhận khi đáo hạn. Lãi chỉ cộng cho sổ trả **cuối kỳ** có nhập lãi; sổ trả đầu kỳ
  đã nhận lãi nên không cộng lại; sổ cuối kỳ chưa nhập lãi được đếm và ghi "chưa nhập lãi".
- Sổ đáo hạn trong 30 ngày tới được đánh dấu "sắp đến hạn".
- Sổ đã qua ngày đáo hạn: **quá hạn, cần cập nhật** (tái tục hay tất toán). Phần mềm không đoán ngân hàng đã tái tục hay chưa, nên gốc vẫn
  ở lớp tiền gửi nhưng không tính là rút ngay.

## Thanh khoản so với quỹ dự phòng
- **Rút ngay** = tiền mặt trong tài khoản chứng khoán (từ sổ giao dịch) + tài khoản tiền mặt đánh dấu rút ngay.
- **Chưa rút ngay** (nêu riêng): tài khoản đánh dấu chưa rút được, sổ chưa đến hạn (phong tỏa hay không), sổ quá hạn chưa cập nhật.
  Sổ không phong tỏa ghi thêm "rút trước hạn được, thường mất lãi" nhưng vẫn không cộng vào rút ngay.
- So với **quỹ dự phòng và khoản chi 12 tháng** đang dùng ở Tháp tài sản (nhập ở Sổ tài sản, hoặc theo hồ sơ khi để trống): đủ, hoặc thiếu bao nhiêu đồng; kèm
  tổng gốc sẽ đáo hạn trong 90 ngày để tham khảo. Không chuyển tiền, không khuyên rút sổ.

## Ảnh hưởng tới phần đã có
- **Tháp tài sản** (cập nhật 2026-11-06): khi Sổ tài sản đã được lưu, tháp lấy mọi lớp từ sổ: Tiền gửi = tổng gốc các sổ (kể cả sổ quá
  hạn), Trái phiếu, Vàng, Tiền số = tổng danh sách tương ứng, danh sách trống là 0. Các số nhập tay của Tháp tài sản (từng lớp và quỹ dự
  phòng) không còn được tính và form nhập tay được ẩn; tháp tính được cả khi chưa từng nhập tay. **Quỹ dự phòng và khoản chi 12 tháng**
  nhập ở Sổ tài sản; để trống thì theo hồ sơ đã xác nhận. Lớp Tiền mặt = tiền mặt sổ giao dịch (trừ khi bỏ chọn) + mọi tài khoản tiền mặt.
  Mục tiêu và cách tính tháp không đổi.
- **Dòng tiền thụ động**: khi có sổ, thu nhập tiền gửi mỗi tháng = Σ gốc × lãi suất của sổ / 12 cho sổ có lãi suất; sổ chưa nhập lãi suất
  dùng lãi suất 12 tháng thị trường như trước, và trang nêu số sổ dùng lãi suất thị trường.
- Dòng tiền thụ động tính trái phiếu theo lợi suất từng dòng; dòng chưa nhập dùng lãi suất trái phiếu của mục đó (mặc định 7%) và được đếm.
- Chưa lưu Sổ tài sản lần nào: mọi trang giữ nguyên hành vi cũ (số nhập tay).

## Giao diện
Hồ sơ & rủi ro, mục "Sổ tiền gửi và tiền mặt", ngay trước Tháp tài sản: bảng tài khoản tiền mặt, bảng sổ (thêm, sửa, xóa, rồi Lưu),
lịch đáo hạn theo tháng, ô thanh khoản. Lưu xong, Tháp tài sản và Dòng tiền thụ động tải lại.

## Ngoài phạm vi (việc sau)
Nhắc sổ sắp đáo hạn qua Telegram; nhập file JSON xuất từ VI-TECH; chứng chỉ quỹ theo số đơn vị và NAV công khai; vàng theo khối lượng
và giá công khai; tiền số theo số lượng và giá.
