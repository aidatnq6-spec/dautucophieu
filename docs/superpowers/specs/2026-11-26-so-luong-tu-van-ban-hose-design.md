# Số lượng giao dịch nội bộ đọc từ văn bản HOSE

Chủ sở hữu duyệt ngày 26/11/2026 (cách B). Nhiều báo cáo giao dịch nội bộ trên VNDirect không có chiều mua bán và số lượng; số đó nằm trong văn bản PDF đính kèm tin HOSE. Ứng dụng tải văn bản, đọc chữ trên máy và chỉ nhận số khi phép cộng trừ trong chính văn bản khớp.

## Nguồn

- Tin HOSE: `doc_url` của báo cáo (`https://www.hsx.vn/vi/tin-tuc/<tên>/<mã tin>`), lấy từ v4/news của VNDirect như hiện nay. Chỉ hsx.vn; tin HNX không đọc.
- Danh sách tệp đính kèm: `https://api.hsx.vn/m/api/v1/1/mediafiles/1/<mã tin>?pageIndex=1&pageSize=100&year=0` (API mà trang hsx.vn tự gọi). Tệp: `https://staticfile.hsx.vn/<filePath bỏ "~/">`. robots.txt của hsx.vn cho phép mọi user agent.
- Văn bản thường là bản quét: chữ đọc bằng Tesseract trên máy (`insights/ocr.py`, tiếng Việt, 300 dpi). Không gửi gì cho AI hay dịch vụ ngoài.

## Văn bản nào được đọc

- Chỉ báo cáo đã thực hiện: tiêu đề bắt đầu bằng "Báo cáo" (kết quả giao dịch, thay đổi sở hữu của cổ đông lớn). "Thông báo giao dịch" là đăng ký, tức ý định, không đọc.
- Chỉ báo cáo mà VNDirect thiếu chiều hoặc số lượng, của các mã đang theo dõi, đã có trong `data/insider/<MÃ>.json`.
- Mỗi tin một tệp `data/insider-docs/<mã tin>.json`, đọc một lần (văn bản đã công bố không đổi). Lỗi tải thì lần sau đọc lại; đọc được mà không nhận số thì giữ kết quả, không đọc lại.

## Khi nào nhận số (chủ sở hữu chọn: chỉ khi cộng trừ khớp)

- Mỗi tệp PDF phải có đủ ba số: nắm giữ trước giao dịch, số đã giao dịch, nắm giữ sau giao dịch (của người hay nhóm thực hiện giao dịch, không phải tổng gồm người có liên quan), và trước ± đã giao dịch = sau, đúng từng cổ phiếu.
- Số đã giao dịch nằm ở "Số lượng cổ phiếu đã giao dịch" (người nội bộ), "Số lượng cổ phiếu đã Mua/đã Bán" (tổ chức) hoặc "Số lượng cổ phiếu đã mua/bán" (nhóm cổ đông lớn). Số là số in kiểu Việt Nam có dấu chấm ngăn nghìn, hoặc 0.
- Chiều: lấy loại đã nêu ("Loại giao dịch đã thực hiện" hay "đã Mua/đã Bán") và chiều đó phải khớp với trước → sau; không đọc được dòng loại thì lấy chiều từ trước → sau (phép cộng trừ vẫn phải khớp). Báo cáo cổ đông lớn lấy chiều từ trước → sau.
- Cho tặng (bổ sung 26/11/2026 sau khi đọc thử văn bản KDH): loại "Cho/tặng", "Được cho/tặng" hoặc phương thức "do cho/tặng" ghi `Cho tặng` hay `Nhận tặng`; không cộng vào mua bán, chỉ đếm số báo cáo (`gift_reports`), nên điều kiện luận điểm "người nội bộ bán" không tính.
- Đã giao dịch 0 cổ phiếu (đăng ký mà không mua bán): để thiếu, lý do "không giao dịch cổ phiếu nào".
- Nhóm cổ đông lớn vừa mua vừa bán trong một văn bản (chủ sở hữu chọn): ghi số ròng của cả nhóm, kiểm trên tổng nhóm, đánh dấu `rong`.
- ESOP (chủ sở hữu chọn): báo cáo có "ESOP" trong tiêu đề hoặc phương thức "mua trực tiếp từ tổ chức phát hành" có loại `ESOP`; không cộng vào số mua 12 tháng mà đếm riêng.
- Một tin có nhiều tệp (mỗi người một tệp): mọi tệp phải nhận được và cùng loại; số lượng là tổng các tệp. Một tệp không nhận được thì cả tin vẫn thiếu.
- Không nhận thì ghi lý do: "không có tệp đính kèm", "không đọc được chữ", "thiếu số trước, đã giao dịch hoặc sau", "cộng trừ không khớp", "chiều không khớp", "các tệp khác loại".

## Dùng ở đâu

- `insider_deals` điền `kind` và `shares` cho báo cáo VNDirect thiếu, từ các văn bản đã nhận, kèm `tu_van_ban` = {trước, sau, số tệp, ròng hay không, lúc đọc}; số VNDirect có sẵn không bao giờ bị thay. Trang mã, cảnh báo giao dịch nội bộ (nhận diện theo ngày và tiêu đề nên không gửi lại tin cũ), điều kiện luận điểm "Người nội bộ hoặc cổ đông lớn bán", bản tin tuần và `giao_dich_noi_bo` cùng thấy số đó.
- Tổng 12 tháng thêm `esop`, `esop_reports` và `gift_reports`.
- Trang mã: loại "ESOP", số đọc từ văn bản có ghi chú "đọc từ văn bản HOSE, đã kiểm trước ± giao dịch = sau".
- `giao_dich_noi_bo`: báo cáo còn thiếu vẫn có `thieu_so_luong` và `van_ban`; báo cáo đã điền có `tu_van_ban`.

## Lịch

- Lượt 20:00 chạy `insider-docs-sync`: tối đa 30 tin mỗi tối, mới trước; nghỉ 1 giây giữa các lần gọi; tệp trên 15 MB hoặc tin trên 8 tệp thì bỏ, ghi lý do.
