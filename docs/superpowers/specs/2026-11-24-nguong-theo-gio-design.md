# Ngưỡng nhắc theo giỏ chiến lược (24/11/2026)

Chủ sở hữu chốt ba điểm ngày 24/11/2026: hai ngưỡng được đặt theo giỏ là Kế hoạch sụt giảm và Lãi đã trả lại thị trường; giỏ để trống
dùng mức chung, và có thể tắt nhắc; Kiểm tra sức chịu đựng dùng ngưỡng theo giỏ, Hậu kiểm vẫn dùng mức chung. Đây là mục 5 của Kaizen
từ podcast "Đỉnh – Đáy" (Nguyễn Trần Hải, Trần Quang Hiến), phần còn lại của spec 2026-11-24-thap-mua-va-gio-chien-luoc-design.md: cách
đánh khác nhau thì kế hoạch khi giá đi ngược cũng khác nhau. Ví dụ giỏ Ngắn hạn nhắc khi giá xuống 7% dưới giá vốn, giỏ Dài hạn không
nhắc. Dữ liệu cá nhân, tính trên máy, không gửi cho AI. Chỉ nhắc theo ngưỡng chủ sở hữu tự đặt, không khuyến nghị.

## Ngưỡng của một giỏ
- Mỗi giỏ trong `settings/trade_baskets` có thêm hai mục, mỗi mục chọn một trong ba cách:
  - **Sụt giảm dưới giá vốn**: *mức chung* (mặc định), *riêng* (một % từ 1% đến 95%, cùng giới hạn với mức chung), hoặc *không nhắc*.
  - **Lãi đã trả lại**: *mức chung* (mặc định), *riêng* (cả A và B, cùng giới hạn với mức chung ở Cài đặt; đặt một ô mà bỏ trống ô kia
    thì không lưu), hoặc *không nhắc*.
- Hai mục này ghi cùng bản ghi giỏ, có phiên bản. Giỏ cũ chưa có hai mục thì đọc là *mức chung*, nên không phải chuyển dữ liệu.
- Xóa giỏ thì các đợt nắm của giỏ đó về "Chưa gắn giỏ" và dùng mức chung, như hiện nay.

## Ngưỡng áp cho một mã đang nắm
- Lấy đợt nắm hiện tại của mã (khóa `MÃ@ngày bắt đầu`, như Giỏ chiến lược), rồi giỏ gắn cho đợt đó.
- Có giỏ và giỏ đặt *riêng*: dùng ngưỡng của giỏ. Giỏ để *mức chung*, đợt chưa gắn giỏ, hoặc nhãn không còn khớp đợt nào: dùng mức
  chung ở Cài đặt danh mục. Giỏ *không nhắc*: mã không có ngưỡng.
- Mức chung của Lãi đã trả lại vẫn có thể để trống, và khi đó không nhắc (như spec Lãi đã trả lại). Giỏ đặt A, B *riêng* thì nhắc theo
  A, B đó dù mức chung đang trống.
- Mọi chỗ hiện ngưỡng đều ghi ngưỡng lấy từ đâu: "giỏ Ngắn hạn: 7%", "mức chung: 30%", hoặc "giỏ Dài hạn: không nhắc".

## Chỗ dùng ngưỡng
| Chỗ | Trước | Sau |
|---|---|---|
| Nhắc Telegram Kế hoạch sụt giảm (`drawdown_run`) | mức chung | theo mã |
| Nhắc Lãi đã trả lại (`giveback_run`, tin "Danh mục hôm nay") | mức chung | theo mã |
| Việc cần xem (dòng sụt giảm, dòng lãi đã trả lại) | mức chung | theo mã |
| Bảng Kế hoạch sụt giảm, khối Lãi đã trả lại thị trường | mức chung | theo mã, ghi nguồn ngưỡng |
| Kiểm tra sức chịu đựng ("mã sẽ thấp hơn giá vốn quá ngưỡng") | mức chung | theo mã; mã ở giỏ *không nhắc* ghi "không có ngưỡng" và không đếm |
| Hậu kiểm quyết định ("Giữ khi đang lỗ") | mức chung | **giữ mức chung** |

Hậu kiểm giữ mức chung vì nó chấm các quyết định đã qua. Ngưỡng theo giỏ là luật mới, dùng nó để chấm lại quá khứ là không đúng. Trang
Hậu kiểm ghi rõ: "dùng ngưỡng chung; ngưỡng theo giỏ chỉ áp cho nhắc từ nay".

## Nhắc một lần, nhắc lại
- Vẫn theo luật cũ: một mã nhắc một lần khi chạm ngưỡng, và chỉ nhắc lại sau khi đã ra khỏi ngưỡng (sụt giảm: giá về trên ngưỡng; lãi đã
  trả lại: phần trả lại về dưới B). Trạng thái vẫn lưu ở `settings/drawdown_alerts` và `settings/giveback_alerts`.
- Ngưỡng của mã đổi (đổi giỏ, sửa ngưỡng của giỏ, sửa mức chung) thì xét theo ngưỡng mới ở lượt chạy sau. Đã nhắc rồi mà vẫn trong ngưỡng
  mới thì không nhắc lại; đã ra khỏi ngưỡng mới thì được nhắc lại khi chạm lần sau.
- Mã ở giỏ *không nhắc* thì bỏ khỏi danh sách đã nhắc. Bật lại sau này mà mã vẫn đang quá ngưỡng thì được nhắc một lần.
- Mỗi dòng trong tin nhắc ghi ngưỡng của mã đó và nguồn ngưỡng (giỏ nào hay mức chung). Tiêu đề tin không ghi một con số chung nữa.

## Giao diện
- Trang Danh mục & Giao dịch, khối Giỏ chiến lược: mỗi giỏ có thêm hai ô chọn (mức chung / riêng / không nhắc), chọn *riêng* thì hiện ô %.
  Lưu cùng nút lưu giỏ.
- Bảng Kế hoạch sụt giảm: dưới "So với giá vốn" của mỗi mã ghi ngưỡng và nguồn ngưỡng. Câu giải thích đầu khối nói ngưỡng có thể đặt theo
  giỏ, và chỉ ra giỏ nào đang *không nhắc*.
- Khối Lãi đã trả lại thị trường: mỗi mã ghi A, B đang áp và nguồn.
- Cài đặt danh mục: ngưỡng chung đổi tên thành "Mức chung", kèm câu "giỏ chiến lược có thể đặt riêng".

## Không làm
- Không đặt ngưỡng nhắc xem lại Nhật ký (15%) theo giỏ.
- Không có ngưỡng sẵn cho giỏ nào, kể cả các tên gợi ý.
- Không áp ngưỡng giỏ cho mã chỉ theo dõi mà không nắm.
- Không đổi Hậu kiểm.

## Thứ tự làm
1. Backend: mô hình giỏ có ngưỡng (đọc giỏ cũ được), hàm tra ngưỡng theo mã, các chỗ nhắc, Việc cần xem, route sụt giảm, lãi đã trả lại,
   sức chịu đựng. TDD.
2. Web: ô chọn ngưỡng ở Giỏ chiến lược, nguồn ngưỡng ở hai khối và ở Cài đặt.
Mỗi phần một commit trên nhánh `feat/nguong-theo-gio`, verify rồi merge.
