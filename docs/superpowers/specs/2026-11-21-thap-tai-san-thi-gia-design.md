# Tháp tài sản theo thị giá và dải chịu đựng (21/11/2026)

Chủ sở hữu duyệt ngày 21/11/2026 (đề xuất 1 + 2).

## Vì sao
Vàng tính theo giá mua vào Phú Quý, chứng chỉ quỹ theo NAV, nhưng cổ phiếu tính theo giá vốn. Khi đang lãi, lớp cổ phiếu bị tính
nhỏ hơn thực tế nên Tháp báo "thiếu" và chia thêm tiền vào cổ phiếu. Khi đang lỗ thì ngược lại: Tháp báo "đủ" đúng lúc tái cân
bằng có lợi nhất.

## Hành vi
- **Cổ phiếu theo thị giá.** Mỗi mã đang nắm tính bằng số lượng (cả số chờ về) × giá đóng cửa gần nhất đã lưu. Đây là cùng nguồn
  giá với trang Tổng quan; giá cũ hơn 10 ngày coi như không có.
- **Mã không có giá gần đây** tính theo giá vốn và được nêu tên ("chưa có giá gần đây, tính theo giá vốn"). Không đoán giá.
- **Dùng chung số này:** Tháp tài sản, Vốn dành cho cổ phiếu (dòng "Đang nắm" và "còn trống/đã vượt", cả ô ở Tổng quan), Tháp
  theo chu kỳ, Tiền mới tháng này đi đâu, Kiểm tra trước khi mua, Dòng tiền thụ động (phần cổ phiếu) và dòng Vàng ở Việc cần xem.
- **Hiển thị:** lớp Cổ phiếu ghi ngày giá và giá vốn bên cạnh. Dòng "Đang nắm (theo thị giá)" cũng ghi giá vốn.
- **Mức tập trung giữ giá mua** như trước. Nền chia của nó (vốn dành cho cổ phiếu) nay tính trên tổng tài sản theo thị giá.
- **Dải chịu đựng 1 điểm %.**
  - Một lớp chỉ "thiếu" khi tỷ trọng thấp hơn mức tối thiểu quá 1 điểm %, và chỉ "vượt" khi cao hơn mức tối đa quá 1 điểm %
    (tính trên phần sau quỹ dự phòng).
  - Khi đã báo, số đồng thiếu hay vượt vẫn tính tới mép khoảng mục tiêu.
  - Phần "Nguồn tiền để mua thêm cổ phiếu" chỉ lấy phần dư của lớp đang "vượt".
  - Tiền mới vẫn chia để đưa từng lớp lên đúng mức tối thiểu, không trừ dải chịu đựng.

## Quỹ dự phòng bằng 0 và chỗ cho cổ phiếu (đề xuất 3 + 4, duyệt 21/11/2026)
- **Quỹ dự phòng bằng 0:**
  - Lớp Dự phòng ghi "chưa có" (màu cảnh báo) thay cho "cố định".
  - Dưới tiêu đề có lời nhắc: quỹ dự phòng và khoản chi 12 tháng đang là 0 đ, nên mục tiêu các lớp đang tính trên toàn bộ tài sản.
  - Lời nhắc dẫn tới Sổ tài sản → Quỹ dự phòng; nếu chưa có Sổ tài sản thì chỉ tới ô Quỹ dự phòng ở trên.
- **Chỗ cho cổ phiếu** là một khối riêng trong "Nguồn tiền để mua thêm cổ phiếu", ghi khoảng mục tiêu, gồm:
  - Tới mức tối thiểu: cổ phiếu đang dưới mức tối thiểu bao nhiêu, 0 nếu đã đạt.
  - Tới mức tối đa: bằng phần còn trống trong vốn dành cho cổ phiếu.
  - Tiền có sẵn để mua: phần dư còn lại sau khi bù các lớp thiếu.
  - Có thể mua thêm: số nhỏ hơn của "Tới mức tối đa" và "Tiền có sẵn để mua".
- **Phần bù lớp thiếu** ghi "Chuyển sang vàng để lên mức tối thiểu trước" kèm số dương, không dùng số âm.

## Không làm
Không đặt lệnh, không nêu mã nên mua hay bán. Không gửi số liệu cá nhân cho AI.
