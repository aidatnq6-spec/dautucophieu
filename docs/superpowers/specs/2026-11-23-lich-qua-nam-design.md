# Lịch giao dịch qua mốc đổi năm (chủ sở hữu duyệt 23/11/2026)

Hiện trạng (kiểm 23/11/2026): mỗi file `config/trading-calendar-hose-<năm>.json` chỉ phủ một năm. `TradingCalendar` báo lỗi "date outside the
calendar's verified range" với mọi ngày ngoài năm của file. Lịch chạy (`run-after-close.ps1`, `run-alerts.ps1`) và trang web
(`api/app.py`) chỉ nạp file của năm hiện tại. App mới chạy từ tháng 10/2026, nên chưa từng đi qua mốc đổi năm. Hệ quả:

- **Thiếu file năm mới:** từ 01/01, 11 bước nhận `--calendar` sẽ đọc một file không tồn tại, gồm đồng bộ giá, bản tin, Xu hướng, cảnh báo danh
  mục và chạy theo lịch. Lỗi ghi vào log là `FileNotFoundError`, không nói rõ thiếu gì.
- **Có file năm mới:** những ngày đầu tháng 1, bước nào cần nhìn lại tháng 12 năm trước vẫn có thể báo lỗi ngoài khoảng. Ví dụ: bản tin tuần
  vắt qua hai năm, phần kiểm tra bản tin trong Tình trạng hệ thống (nhìn lùi 14 ngày), sổ giá của `StoreMarket` trên web.

Không đổi: lịch chỉ dựng từ thông báo của HOSE, có nguồn. Phần mềm không tự lấy và không đoán ngày nghỉ (xem `docs/decisions/market-rules.md`).
Tình trạng hệ thống vẫn cảnh báo từ 01/12 khi chưa có lịch năm sau.

## 1. Nạp gộp các năm liền nhau
- `load_calendar(path)`: khi tên file có dạng `trading-calendar-hose-<năm>.json`, nạp thêm file của năm trước và năm sau cùng thư mục, nếu có và
  liền khoảng (năm trước hết ngày 31/12, năm sau bắt đầu ngày 01/01). Ngày nghỉ là hợp của các file. Khoảng phủ kéo từ ngày đầu của file sớm nhất
  đến ngày cuối của file muộn nhất. `version` và `source` ghi đủ các file đã dùng.
- Hai file không liền khoảng thì không gộp. Ngày nằm trong khoảng trống vẫn báo lỗi ngoài khoảng như bây giờ, không coi là ngày giao dịch.
- `data/trading-calendar.json` (file chủ sở hữu tự lập) giữ nguyên cách dùng hiện tại, không gộp thêm.
- Trang web nạp lịch qua cùng hàm này, nên đầu tháng 1 vẫn đọc được giá tháng 12.

## 2. Thiếu lịch năm hiện tại thì báo rõ
- Lịch chạy vẫn trỏ tới file của năm hiện tại. Nếu file không có, `load_calendar` báo lỗi bằng câu rõ ràng: "chưa có lịch giao dịch HOSE <năm>
  (config/trading-calendar-hose-<năm>.json); tạo từ thông báo của HOSE". Câu này hiện trong `logs/scheduler.log` (dòng stderr của bước).
- Không lùi về lịch năm cũ hay coi mọi ngày trong tuần là ngày giao dịch cho các bước này. Các bước dừng, và Tình trạng hệ thống đã cảnh báo
  từ 01/12.

## 3. Kiểm thử
- Test với lịch giả có `source` cho hai năm liền nhau:
  - ngày 31/12 và 04/01 có phiên trước và phiên sau đúng;
  - tuần vắt qua hai năm có đủ phiên;
  - hai năm không liền khoảng thì không gộp;
  - thiếu file năm hiện tại thì báo đúng câu trên.
- Chạy thử thật các bước theo lịch với ngày 04/01/2027 và một lịch 2027 giả đặt trong thư mục tạm (không ghi vào `config/`), chỉ in trạng thái
  từng bước.

## Ngoài phạm vi
- Tự lấy lịch từ hsx.vn: thông báo là lời văn, được sửa sau khi công bố, và các bài đăng lại không thống nhất (kiểm 23/11/2026).
- Công cụ tạo file lịch.

## Đã làm (23/11/2026)
- `load_calendar` (`cli.py`) gộp các năm liền nhau và báo `CalendarMissing` (một loại `FileNotFoundError`) với câu ở mục 2.
- Test `backend/tests/market/test_calendar_years.py`:
  - `decide` sáng 04/01 chạy bù phiên cuối năm cũ;
  - tối 05/01 đếm đúng 2 phiên bị lỡ;
  - kiểm tra bản tin nhìn lùi qua năm cũ.
- Với cách cũ (chỉ một năm), ba trường hợp trên lần lượt cho `no_session`, `ValueError`, `ValueError`.
- Mục 3 không chạy thật các bước theo lịch ngày 04/01/2027, vì như vậy sẽ gửi Telegram và ghi vào `data/`. Thay vào đó là test trên chính các
  hàm nhìn lùi.

- Bản tin tuần trước đây coi mọi ngày trong tuần là ngày giao dịch khi thiếu lịch, nên 01/01 bị đếm là một phiên thiếu số khối ngoại. Nay bước
  này dừng với câu ở mục 2, trước khi đọc dữ liệu cá nhân hay chạm tới Telegram.

## Thứ tự
1 → 2 → 3 trên một nhánh, TDD, verify rồi merge.
