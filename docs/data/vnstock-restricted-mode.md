# Vnstock — chế độ hạn chế

Chủ sở hữu duyệt ngày 25/10/2026: dùng Vnstock để có **giá đã điều chỉnh, dữ liệu hồi tố, khoảng 8 năm** trong khi đánh giá nguồn trả phí. Chế độ này thấp hơn yêu cầu thiết kế (10 năm, giá gốc, dữ liệu đúng thời điểm công bố), nên mọi dữ liệu từ đây mang nhãn `latest_restated` / `adjusted`. Xem đánh giá tại `docs/data/2026-10-25-source-feasibility.md`.

## Dùng được gì

- Định giá danh mục theo giá đóng cửa gần nhất (nhãn `vnstock_adjusted` trên tổng quan và bản tin). Giá cũ hơn 10 ngày được coi là thiếu.
- Bản tin sau phiên có giá thật thay vì "thiếu dữ liệu".

## Vẫn bị chặn

- Khuyến nghị mua thật: vẫn cần tài liệu nguồn và giả định định giá đã duyệt; danh sách 50 mã không kích hoạt được vì bằng chứng chưa đạt kiểm tra 10 năm.
- Mọi kết luận cần dữ liệu đúng thời điểm (kiểm thử lịch sử, "rẻ nhất 10 năm", P/E theo ngày công bố).
- Giá đã điều chỉnh không dùng làm giá vốn hay giá giao dịch trong sổ; sổ vẫn ghi theo chứng từ.

## Cài đặt (bạn tự làm)

Vnstock v5 không có trên PyPI; được phân phối dạng gói biên dịch sẵn từ chỉ mục của vnstocks.com. Dự án **không** cài gói này mặc định.

1. Đăng ký tài khoản Community và lấy key tại vnstocks.com/download (bạn đọc và tự chấp nhận điều khoản của Vnstock và của nguồn dữ liệu VCI/KBS; giấy phép Community chỉ cho mục đích cá nhân, học tập, nghiên cứu).
2. Cài vào môi trường của dự án:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -U --extra-index-url https://vnstocks.com/api/packages vnstock
   ```
3. Đặt `VNSTOCK_API_KEY=...` trong `.env.local` (không dán vào hội thoại hay mã).

## Lệnh

```powershell
# Đo độ sâu dữ liệu cho các mã đại diện (ghi data\audits\vnstock-audit.json)
.\.venv\Scripts\python.exe -m investment_agent.cli vnstock-audit --symbols FPT,VCB,HPG,VHM,MWG --output-dir data\audits

# Nạp giá 30 ngày gần nhất (chỉ phiên có trong lịch HOSE)
.\.venv\Scripts\python.exe -m investment_agent.cli market-sync --symbols FPT,VCB --data-dir data --calendar config\trading-calendar-hose-2026.json --days 30
```

Để lịch tự động cập nhật giá trước mỗi lần chạy, tạo `data\market-symbols.txt` (mỗi dòng một mã đang nắm giữ hoặc đang theo dõi). Khi có `data\prices`, server và lịch tự động dùng giá đã nạp; nếu không thì giữ chế độ không có dữ liệu.

## Giới hạn theo tài liệu Vnstock v5.0.1

- Giá ngày tối đa 2.920 ngày, 10.000 dòng; đơn vị nghìn đồng (ứng dụng nhân 1.000 và giữ nguyên độ chính xác bằng `floating=None`).
- BCTC 8 kỳ gần nhất mỗi lần gọi; không có ngày công bố, không phân biệt hợp nhất/riêng qua tham số; mã dòng (`IS_NET_REVENUE`…) sẽ được liệt kê trong báo cáo audit trước khi ánh xạ vào phân tích.
- 60 yêu cầu/phút với key Community (20 khi không có key).
