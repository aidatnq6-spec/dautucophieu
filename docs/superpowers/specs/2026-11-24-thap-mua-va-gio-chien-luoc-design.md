# Soi hình tháp khi mua thêm và Giỏ chiến lược (24/11/2026)

Chủ sở hữu duyệt ngày 24/11/2026 (gắn giỏ theo đợt nắm; giữ nhãn hình tháp). Kaizen từ podcast "Đỉnh – Đáy" (Nguyễn Trần Hải, Trần Quang Hiến): mục 7.1 (lần mua đầu ở vùng thấp phải
là lần lớn nhất, cấm "tháp ngược": mua ít lúc rẻ rồi mua nhiều khi giá đã lên) và mục 7.2 (chia vốn theo cách đánh: ngắn hạn, dài hạn,
theo môi giới, tự quyết, bắt đáy, để biết cách nào thật sự hiệu quả). Dữ liệu cá nhân, tính trên máy, không gửi cho AI. Chỉ đưa số đã
xảy ra, không chấm điểm, không khuyến nghị.

## Đợt nắm (dùng chung)
Một đợt nắm của một mã bắt đầu khi số cổ phiếu đi từ 0 lên lớn hơn 0 và kết thúc khi về lại 0 (như Lãi đã trả lại thị trường). Khóa
của đợt là `MÃ@ngày bắt đầu`. Sửa sổ làm đổi ngày bắt đầu thì đợt thành đợt mới; nhãn cũ không còn khớp được ghi "nhãn không còn khớp
đợt nào" để chủ sở hữu gắn lại.

## Phần 1: Soi hình tháp khi mua thêm (trong Hậu kiểm quyết định, trang Nhật ký)
- Mỗi đợt nắm có từ 2 lần mua trở lên (đang nắm và đã đóng), một dòng.
- Mỗi lần mua: ngày, **tiền bỏ ra** (số lượng × giá + phí + thuế, đồng) và **mức giá so với lần mua đầu** = giá đóng cửa điều chỉnh ngày mua
  ÷ giá đóng cửa điều chỉnh ngày mua đầu − 1. Dùng tiền và giá điều chỉnh (không dùng số cổ phiếu và giá khớp) để cổ phiếu thưởng, chia
  tách giữa hai lần mua không làm sai phép so. Ngày mua không có giá đã lưu thì đợt đó ghi "chưa so được" kèm ngày, không lấp.
- Mỗi đợt ghi ba số và một nhãn mô tả:
  - phần tiền đã bỏ vào ở mức giá **cao hơn** lần mua đầu (% tổng tiền của đợt);
  - lần mua nhiều tiền nhất ở mức giá nào so với lần mua đầu;
  - tiền bình quân mỗi lần mua ở trên so với ở dưới giá lần mua đầu.
  - Nhãn: **"Tháp xuôi"** khi lần mua nhiều tiền nhất là lần ở mức giá thấp nhất của đợt; **"Tháp ngược"** khi lần mua nhiều tiền nhất là
    lần ở mức giá cao nhất và cao hơn lần mua đầu; còn lại **"Xen kẽ"**. Bằng nhau thì lấy lần sớm hơn.
- Tổng kết đầu bảng: số đợt mỗi nhãn và phần tiền bình quân bỏ vào ở mức giá cao hơn lần mua đầu. Dưới 5 đợt thì chỉ đếm, không tính bình
  quân (như quy tắc 5 quan sát của Hậu kiểm).

## Phần 2: Giỏ chiến lược
- Chủ sở hữu tự đặt tên tối đa 8 giỏ (không có sẵn). Gợi ý tên bấm để tạo, không tự tạo: Ngắn hạn, Dài hạn, Theo môi giới, Tự quyết,
  Bắt đáy. Lưu ở kho cá nhân `settings/trade_baskets` (ghi có phiên bản): danh sách giỏ và nhãn của từng đợt nắm.
- **Gắn theo đợt nắm, không theo từng lệnh**: mọi lần mua, bán trong một đợt thuộc một giỏ. Như vậy lãi đã chốt lấy đúng số của sổ (giá vốn
  bình quân, `realised_sells`), không phải tự chia lô. Đánh đổi: trong một đợt không chia một mã ra hai giỏ.
- Gắn ở bảng đợt nắm trên trang Danh mục & Giao dịch (cột Giỏ, chọn từng dòng hoặc chọn nhiều dòng rồi gắn một lần). Đợt chưa gắn nằm ở
  "Chưa gắn giỏ".
- Mỗi giỏ (và "Chưa gắn giỏ") một dòng:
  - số đợt đã đóng, số đợt đang nắm;
  - lãi đã chốt (tiền bán sau phí, thuế − giá vốn sổ đã nhả ra) của các lần bán trong giỏ, và lãi đó chia cho giá vốn đã nhả ra;
  - tỷ lệ đợt đã đóng có lãi (tổng lãi đã chốt của đợt > 0);
  - số ngày nắm bình quân của đợt đã đóng;
  - giá vốn và lãi chưa chốt của đợt đang nắm theo thị giá (như bảng danh mục; mã thiếu giá thì nêu tên, không tính).
  - Dưới 5 đợt đã đóng thì không tính tỷ lệ có lãi và ngày nắm bình quân, ghi "chưa đủ 5 đợt".
- Cổ tức tiền không cộng vào lãi đã chốt (sổ ghi riêng); trang ghi rõ.

## Không làm
- Không chia lô theo lệnh, không gắn giỏ cho lệnh cũ trong nhật ký đã nhập (chưa có số cổ phiếu đang nắm để dựng đợt).
- Không đổi Kế hoạch sụt giảm hay ngưỡng nhắc theo giỏ ở bản này (đó là mục 5, làm sau khi có giỏ).
- Không gửi Telegram: hai phần này chỉ để tự xem lại.
