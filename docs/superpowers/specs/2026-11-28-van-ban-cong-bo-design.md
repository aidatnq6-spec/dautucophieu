# Văn bản công bố cho Claude (MCP)

Bản nháp ngày 28/11/2026, chờ chủ sở hữu duyệt. Chủ sở hữu đã chọn phương án A và chỉ làm cho các mã đang theo dõi.

## Mục đích

Claude cần tự trả lời được ba loại câu hỏi về một mã đang theo dõi, từ văn bản công bố của chính công ty:

1. Khoản lãi bất thường đến từ đâu (thuyết minh doanh thu tài chính, thu nhập khác, các sự kiện quan trọng trong kỳ).
2. Công ty vay ai, bao nhiêu, kỳ hạn, tài sản đảm bảo (thuyết minh vay).
3. HĐQT hoặc Tổng Giám đốc vừa quyết định gì (nghị quyết, quyết định, công bố thông tin bất thường).

Hôm 28/11/2026 các câu hỏi này với KDH phải tải tay và đọc OCR từng tệp. Mục tiêu là lượt chạy tối tự làm việc đó và Claude chỉ việc tìm trong chữ đã lưu.

## Không làm

- Không tóm tắt hay diễn giải bằng AI ở bước lưu; chỉ lưu chữ đọc được, theo trang.
- Không làm cho mã ngoài danh sách theo dõi; không tìm văn bản của cả sàn.
- MCP không tải, không OCR, không ghi gì (giữ đúng spec MCP 26/11: chỉ đọc tệp trong `data/`).
- Không đoán số khi OCR mờ: trả nguyên đoạn chữ kèm số trang để kiểm lại.

## Ràng buộc

- Danh sách mã theo dõi là dữ liệu riêng: tệp nguồn của từng mã nằm ở `data/report-sources.json` (không vào Git); MCP không liệt kê mã nào có văn bản, và với mã không có văn bản chỉ trả "chưa có văn bản công bố của <mã> trong kho", không nói vì sao.
- Nguồn đọc theo robots.txt; không lấy VnExpress. User-Agent như các bước khác (`investment-agent/0.1 (personal use)`).
- OCR chạy trên máy (Tesseract, tiếng Việt, `insights/ocr.py`); không gửi tệp hay chữ cho dịch vụ ngoài.
- Lượt 20:00 đã có nhiều bước; bước mới có giới hạn thời gian và số tệp mỗi đêm.

## Nguồn

| Loại văn bản | Nguồn | Cách chọn tệp |
|---|---|---|
| Báo cáo tài chính (quý, soát xét 6 tháng, kiểm toán năm) | Trang cổ đông của công ty, đường dẫn ghi trong `data/report-sources.json` | Liên kết `.pdf` trên trang có nhãn chứa "BCTC" hoặc "Báo cáo tài chính"; ưu tiên bản hợp nhất; bỏ bản công ty mẹ khi cùng kỳ có bản hợp nhất |
| Nghị quyết, quyết định, công bố bất thường | (1) Trang công bố thông tin của công ty nếu có trong tệp nguồn; (2) luồng tin VNDirect theo mã (`v4/news?q=tagCodes:<MÃ>`, tệp đính kèm) | Nhãn hoặc tiêu đề chứa "Nghị quyết", "NQ HĐQT", "Quyết định", "ĐHĐCĐ"; loại tin VNDirect `resolutions`, `meeting`, `other_rights`, `management_reports` |

- Hôm 28/11 quyết định chuyển nhượng vốn Bình Trưng Mới (05/06/2026) chỉ có trên trang của KDH, không có trên VNDirect, nên trang công bố thông tin của công ty là nguồn chính cho nghị quyết khi có.
- Cùng một văn bản từ hai nguồn (cùng ngày, tiêu đề gần giống) chỉ lưu một lần.
- `data/report-sources.json`: `{"<MÃ>": {"bctc": "<url>", "cbtt": "<url>" | null, "kiem_tra": "YYYY-MM-DD", "robots": "allow"}}`. Mã không có trong tệp chỉ dùng nguồn VNDirect. Lệnh CLI kiểm robots.txt và báo liên kết đọc được trước khi thêm một mã.
- Phạm vi lần tải đầu: văn bản từ 01/04/2026 (báo cáo quý II/2026 trở đi); sau đó chỉ văn bản mới.

## Lượt chạy

- Bước `filings-sync` trong lượt 20:00, sau `insider-docs-sync`, `jobs.step --timeout 1800`.
- Mỗi đêm: đọc trang nguồn của từng mã theo dõi (một lần gọi mỗi trang, nghỉ 1 giây), lập danh sách tệp mới, rồi tải và OCR tối đa 4 tệp, mới nhất trước, báo cáo tài chính trước nghị quyết. Hết 25 phút thì dừng và để phần còn lại cho đêm sau.
- Tệp quá 30 MB hoặc quá 120 trang: lưu tên, đường dẫn, lý do bỏ qua; không tải lại.
- Lỗi một tệp không dừng các tệp khác; tệp lỗi được thử lại tối đa 3 đêm.
- Lưu `data/filings/<MÃ>/<id>.json`: `ma`, `loai` (`bctc` | `nghi_quyet`), `tieu_de`, `ngay` (ngày trong nhãn hoặc tin; thiếu thì `null`), `nguon` (url), `trang_nguon`, `lay_luc`, `so_trang`, `ocr` (số trang đọc bằng OCR), `trang` (danh sách chữ theo trang). Không giữ tệp PDF.
- Mỗi bước ghi một dòng vào `logs/scheduler.log` như các bước khác.

## Công cụ MCP

`van_ban_cong_bo(ma, tu_khoa=None, loai=None, tu_ngay=None)` trong `public_tools.py`, đăng ký ở `mcp_server`.

- Không có `tu_khoa`: danh sách văn bản đã lưu của mã (`tieu_de`, `loai`, `ngay`, `so_trang`, `ocr`, `nguon`), mới nhất trước, tối đa 40.
- Có `tu_khoa`: các đoạn khớp (không phân biệt dấu và hoa thường), mỗi đoạn khoảng 600 ký tự quanh chỗ khớp, kèm `tieu_de`, `ngay`, `trang`, `nguon`; tối đa 12 đoạn, văn bản mới trước. Vượt thì ghi `con_nua: true`.
- `loai` lọc `bctc` hoặc `nghi_quyet`; `tu_ngay` lọc theo ngày văn bản.
- Luôn kèm `luu_y`: chữ đọc từ bản scan bằng OCR có thể sai số, ngày, dấu; con số quan trọng thì kiểm ở trang ghi kèm.
- Thiếu: `thieu: true`, lý do "chưa có văn bản công bố của <mã> trong kho" (cùng câu cho mọi trường hợp không có).
- Kèm: hướng dẫn dùng trong `docs/claude-project-instructions.md`, skill `/dautu-ma` (gợi ý tìm "thoái vốn", "thu nhập khác", "vay" khi lợi nhuận có cảnh báo ngoài bán hàng), danh sách công cụ đã duyệt trong test, plugin 0.30.0.

## Các cách đã cân nhắc

| | Cách | Lý do chọn hay không |
|---|---|---|
| **A (chọn)** | Trang cổ đông công ty cho báo cáo tài chính, nghị quyết từ trang công ty và VNDirect; OCR mỗi đêm; MCP tìm trong chữ đã lưu | Trả lời được cả ba loại câu hỏi |
| B | Chỉ luồng tin VNDirect | Không có báo cáo tài chính, không trả lời được hai câu hỏi chính |
| C | Như A nhưng chạy tay | Claude không tự có dữ liệu |
| (loại) | API tin HOSE | `newstype/-1` chỉ có tin của HOSE; không tìm thấy luồng tin doanh nghiệp lọc theo mã (kiểm 28/11/2026) |
| (loại) | MCP tự tải và OCR khi được hỏi | Trái spec MCP (không gọi nguồn ngoài, không ghi); OCR 50–60 trang mất vài phút |

## Các quyết định của người thiết kế (chủ sở hữu kiểm khi đọc)

- 4 tệp và 25 phút mỗi đêm. Với 56 mã, mỗi quý thêm khoảng 56 báo cáo tài chính, nên mùa báo cáo cần khoảng hai tuần để đọc hết.
- Chỉ lưu chữ, không giữ PDF (một báo cáo 8–11 MB, chữ khoảng 100–200 KB).
- Đoạn trích 600 ký tự, tối đa 12 đoạn mỗi lần hỏi, để câu trả lời của công cụ vừa phải.
- Danh sách nguồn 56 mã do Claude tìm và kiểm robots.txt, chủ sở hữu duyệt trước khi bật bước chạy tối.

## Để người làm tự quyết

- Cách nhận diện ngày trong nhãn liên kết (ví dụ "(29/07/2026)") và trong đường dẫn.
- Ngưỡng "tiêu đề gần giống" khi bỏ trùng.
- Cách chia nhỏ mã nguồn giữa các tệp `market/…`, miễn `public_tools.py` chỉ import `investment_agent.market…`.
