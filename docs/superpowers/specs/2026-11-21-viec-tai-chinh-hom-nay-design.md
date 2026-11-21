# Việc tài chính hôm nay (21/11/2026)

Chủ sở hữu duyệt ngày 21/11/2026 (kaizen 5).

## Vì sao
Mỗi lượt lịch có tới 5 bước gửi tin cá nhân riêng lẻ. Ngày nhiều việc, điện thoại nhận nhiều tin rời nhau.

## Hành vi
- Bước `wealth-alerts` thay cho 5 bước `deposit-alerts`, `pyramid-alerts`, `loan-alerts`, `contribution-remind` và
  `accumulation-remind`. Bước chạy sau khi đã lấy giá cổ phiếu, NAV và giá vàng.
- Các phần, theo thứ tự trong tin:
  1. Sổ tiết kiệm đến hạn.
  2. Hết lãi ưu đãi của khoản vay.
  3. Phí bảo hiểm đến hạn.
  4. Cho thuê.
  5. Tháp tài sản.
  6. Góp vốn đều.
  7. Kế hoạch tích sản.
- Mỗi phần giữ nguyên quy tắc nhắc và cách tự ghi "đã nhắc" như trước. Phần nào có nội dung thì được ghép vào một tin, mở đầu bằng
  "Việc tài chính hôm nay dd/mm/yyyy".
- Không phần nào có nội dung thì không gửi gì.
- Tin không gửi được thì được xếp đầu hàng chờ Telegram (`data/alerts/telegram_pending.json`) và gửi trước ở lần gửi sau. Như vậy một
  lời nhắc đã ghi "đã nhắc" sẽ được giao muộn hơn, nhưng không mất và không gửi trùng.
- Một phần lỗi (ví dụ không đọc được sổ) không chặn các phần khác.
- Tắt gửi tin theo lịch thì không đọc dữ liệu cá nhân và không gửi gì.
- Các lệnh cũ vẫn còn để chạy tay; lịch chỉ dùng bước gộp.

## Không làm
- Không gộp các tin về cổ phiếu (sụt giảm, luận điểm, giao dịch nội bộ, kế hoạch giải ngân), các tin vĩ mô (đã gộp ở Nhắc vĩ mô),
  hay bản tin phiên.
- Không gửi số liệu cá nhân cho AI.
