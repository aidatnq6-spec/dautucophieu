# Số đã công bố bị sửa, Cho vay so với vốn chủ, Dự phòng đi vào lợi nhuận (chủ sở hữu duyệt 22/11/2026)

Kaizen từ tài liệu của chủ sở hữu "Dự phòng phải thu khó đòi và điều chỉnh hồi tố" (ví dụ HAG). Chỉ số liệu công khai của VNDirect, không
gọi AI, không đoán số. Áp dụng cho mã phi tài chính đang theo dõi (ngân hàng, chứng khoán, bảo hiểm có mẫu báo cáo khác: ngoài phạm vi).

## 1. Số đã công bố bị sửa (dấu hiệu điều chỉnh hồi tố)
- Hiện nay mỗi lượt đồng bộ báo cáo tài chính ghi đè số cũ; số bị sửa không để lại dấu vết.
- Từ nay, khi số của một **kỳ đã đóng** (không phải kỳ mới nhất của mã) đổi ở các dòng: LNST công ty mẹ, LNTT, vốn chủ sở hữu, dự phòng
  phải thu (ngắn và dài hạn), và mức đổi vượt **cả** 1% số cũ **và** 1 tỷ đồng, phần mềm ghi một dòng vào `data/statement-revisions/<MÃ>.json`:
  kỳ, dòng, số cũ, số mới, ngày thấy. Số được giữ nguyên như nguồn; không suy ra nguyên nhân.
- Hồ sơ mã: mục "Số đã công bố bị sửa" liệt kê các dòng đó, mới nhất trước, ghi "có thể do điều chỉnh hồi tố hoặc nguồn sửa lỗi nhập;
  xem thuyết minh và báo cáo kiểm toán".
- Mã đang giữ: một dòng trong Danh mục hôm nay (Telegram) cho mỗi lần sửa mới, gửi một lần.
- Giới hạn: chỉ bắt được các lần sửa **từ nay**; điều chỉnh đã xảy ra trước (HAG 2018–2019) không dựng lại được. Lần đồng bộ đầu tiên
  chỉ lưu mốc, không báo.
- Mỗi lượt đồng bộ hằng tuần chỉ đọc lại hai năm gần nhất (730 ngày), nên lần sửa số cũ hơn hai năm không bắt được. Mã đổi bộ dòng
  (đọc lại toàn bộ lịch sử) không so ở lượt đó.

## 2. Cho vay và phải thu khác so với vốn chủ
- Mỗi quý: (phải thu về cho vay ngắn và dài hạn + phải thu khác ngắn và dài hạn) ÷ vốn chủ sở hữu. Vốn chủ không dương thì không tính và
  ghi lý do. Dòng thiếu thì để trống.
- Từ năm 2026 Thông tư 99 gộp phải thu về cho vay vào phải thu khác; cộng hai phần nên tỷ lệ không bị gãy qua năm.
- Hiện trong khối Phải thu (12 quý). Cờ khi quý mới nhất **từ 30%**, hoặc **tăng từ 10 điểm** so với cùng kỳ năm trước.
- Bảng dấu hiệu phải thu (Ngành theo quý) thêm cột này; cờ bật kèm liên kết Sổ phải thu bên liên quan của mã.

## 3. Dự phòng đi vào lợi nhuận bao nhiêu
- Mỗi quý: thay đổi số dư dự phòng phải thu (cuối quý trừ cuối quý trước, theo giá trị tuyệt đối) so với LNTT của quý đó.
  Ví dụ "dự phòng tăng 19 tỷ, bằng 12% LNTT"; "dự phòng giảm 40 tỷ, bằng 35% LNTT".
- Cờ "giảm dự phòng lớn so với lợi nhuận" khi số dư giảm từ **20% LNTT** trở lên (LNTT dương). LNTT không dương: ghi số tiền, không ghi tỷ lệ.
- Luôn ghi kèm: "Số dư giảm có thể do hoàn nhập (làm tăng lợi nhuận) hoặc do xóa nợ (không ảnh hưởng lợi nhuận); nguồn công khai không tách
  được, cần xem thuyết minh."

## Thứ tự làm
1 → 2 → 3, mỗi phần một nhánh, TDD, verify rồi merge.

## Đã làm
- Phần 1 (22/11/2026): `market/statement_revisions.py`; nhật ký `data/statement-revisions/<MÃ>.json`; nhắc mã đang giữ trong Danh mục hôm nay
  (đã báo lưu ở `data/alerts/statement-revisions.json`).
- Phần 2 (22/11/2026): `lending_view` trong khối Phải thu (dòng có nhãn khi bật cờ) và cột "Cho vay lớn so với vốn chủ" trên Bảng dấu hiệu
  phải thu, kèm câu nhắc xem Sổ phải thu bên liên quan. Trước 2026, thiếu dòng cho vay thì để trống; từ 2026 (Thông tư 99) coi là không có.
