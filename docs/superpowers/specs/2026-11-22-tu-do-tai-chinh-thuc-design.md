# Mốc tự do tài chính theo lợi suất thực và Lợi suất cần có (chủ sở hữu duyệt 22/11/2026)

Kaizen từ tài liệu của chủ sở hữu "1 triệu USD có phải con số phù hợp để tự do tài chính?" (VWA). Nằm trong khối Mục tiêu dòng tiền thụ động
(Hồ sơ). Dữ liệu cá nhân, chỉ tính trên máy, không gửi AI. Mọi con số là giả định do chủ sở hữu đặt hoặc số đã lưu; không phải dự báo, không
phải khuyến nghị.

## 1. Mốc tự do tài chính theo lợi suất thực
- Hiện nay: vốn cần có = chi tiêu tháng × 12 ÷ lợi suất danh nghĩa; lạm phát không tính (ghi trong code).
- Thêm hai ô lưu cùng mục tiêu: **lạm phát giả định** (%/năm; để trống thì dùng CPI Việt Nam so cùng kỳ mới nhất ở Vĩ mô, ghi tháng của số)
  và **biên an toàn** (%; để trống là 0).
- **Vốn cần có theo lợi suất thực** = chi tiêu năm ÷ (lợi suất − lạm phát) × (1 + biên an toàn). Lợi suất không vượt lạm phát: không tính,
  ghi "lợi suất không vượt lạm phát: tiền mất sức mua, không có mốc".
- Hiện song song với cách tính danh nghĩa đang có. Thời gian đạt theo lợi suất thực: cùng cách gộp lãi hằng tháng nhưng với lợi suất thực,
  tiền góp giữ nguyên (tính theo sức mua hôm nay).
- Một dòng so với con số rập khuôn: "Quy tắc 4%: chi tiêu này cần X; 1 triệu USD ≈ Y tỷ đồng (tỷ giá bán Vietcombank ngày …)". Không có tỷ giá
  thì bỏ phần USD.

## 2. Lợi suất cần có để đạt đúng hạn
- Chủ sở hữu nhập **năm muốn đạt** (lưu cùng mục tiêu). Mốc cần đạt là vốn cần có theo lợi suất thực (mục 1); không có thì dùng mốc danh nghĩa,
  ghi rõ đang dùng mốc nào.
- Từ vốn hiện có (Tháp tài sản trừ quỹ dự phòng, như Đường tăng trưởng) và mức Góp vốn đều, tìm **lợi suất năm cần có** để đạt mốc vào cuối năm
  đó (gộp lãi hằng tháng, góp cuối tháng; giải bằng chia đôi, chính xác 0,01 điểm %). Đã đủ vốn: ghi "đã đạt". Cần trên 50%/năm: ghi "không
  khả thi với số vốn và mức góp hiện tại".
- Đặt cạnh ba mốc có thật, mỗi mốc ghi nguồn:
  - lãi tiết kiệm 12 tháng mới nhất (Vĩ mô);
  - **VN-Index bình quân năm** từ phiên đầu tiên đã lưu đến phiên mới nhất (chỉ giá, chưa gồm cổ tức; ghi khoảng thời gian);
  - **lợi suất danh mục của bạn** quy ra năm từ Hiệu suất, chỉ khi sổ có từ 1 năm trở lên (không thì ghi "chưa đủ một năm").
- Lợi suất cần có cao hơn VN-Index bình quân: ghi thẳng "cao hơn mức VN-Index đã đạt bình quân từ năm …; cân nhắc lùi hạn hoặc tăng mức góp",
  kèm hai phương án tính sẵn: (a) đạt vào năm nào nếu lợi suất bằng VN-Index bình quân; (b) cần góp thêm bao nhiêu mỗi tháng để đạt đúng hạn với
  lợi suất đó.

## Thứ tự
1 → 2, mỗi phần một nhánh, TDD, verify rồi merge.

## Đã làm (22/11/2026)
- Phần 1: `real_target`, `rule_of_four` (domain/passive_income.py); ô Lạm phát giả định, Biên an toàn; dòng "Vốn cần có theo lợi suất thực" và
  "So với con số rập khuôn".
- Phần 2: `domain/required_return.py`; ô Năm muốn đạt (từ năm nay đến 60 năm sau); dòng "Lợi suất cần có" với ba mốc đối chiếu và hai phương án.
  Lợi suất danh mục của bạn là Hiệu suất (gộp theo thời gian, đã trừ nộp rút) quy ra năm, chỉ khi sổ từ một năm.
