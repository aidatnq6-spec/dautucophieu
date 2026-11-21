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
- Các lệnh một phần cũ (`deposit-alerts`, `pyramid-alerts`, `loan-alerts`, `contribution-remind`, `accumulation-remind`, `buy-plan-check`, `insider-alerts`, `drawdown-check`, cùng `macro-signals`, `liquidity-alerts` đã gộp ở Nhắc vĩ mô) đã bị xóa (chủ sở hữu duyệt 21/11/2026): chạy riêng một phần dễ gửi trùng nội dung với tin gộp.

## Danh mục hôm nay (duyệt cùng ngày)
- Bước `portfolio-alerts` thay cho `buy-plan-check`, `insider-alerts`, `drawdown-check` và `thesis-check --scope data`.
- Bước chạy sau mọi nguồn mà các phần này đọc (báo cáo, kế hoạch, sự kiện, giá vàng) và trước bản tin phiên. Giới hạn 15 phút, vì
  phần sụt giảm lấy lịch sử giá có giãn cách.
- Thứ tự trong tin:
  1. Kế hoạch giải ngân.
  2. Giao dịch nội bộ mới.
  3. Kế hoạch sụt giảm.
  4. Luận điểm đầu tư.
- Tin mở đầu bằng "Danh mục hôm nay dd/mm/yyyy". Cách gộp, xếp hàng chờ khi gửi lỗi và một phần lỗi không chặn phần khác giống như
  Việc tài chính hôm nay.
- Tắt gửi tin theo lịch: vẫn lấy lịch sử giá cho Kế hoạch sụt giảm và vẫn ghi trạng thái luận điểm (đóng luận điểm của mã đã bán),
  như trước; không gửi gì, nên các lời nhắc vẫn còn chờ.
- Luận điểm theo giá trong phiên (mỗi 5 phút) vẫn gửi riêng, vì cần báo ngay.

## Không làm
- Không gộp các tin vĩ mô (đã gộp ở Nhắc vĩ mô), bản tin phiên, hay các cảnh báo trong phiên.
- Không gửi số liệu cá nhân cho AI.
