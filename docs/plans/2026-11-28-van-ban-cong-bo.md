# Văn bản công bố — kế hoạch thực hiện

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lượt 20:00 tự tải và OCR báo cáo tài chính và nghị quyết của các mã đang theo dõi vào `data/filings/`, và công cụ MCP `van_ban_cong_bo` tìm trong chữ đã lưu.

**Architecture:** `market/filings.py` gồm các hàm thuần (đọc liên kết PDF trên trang cổ đông, phân loại, ngày, bỏ trùng, kho lưu, tìm đoạn) và `sync_filings` nhận mọi thao tác mạng và OCR qua tham số. `cli.py` nối HTTP và OCR thật (`filings-sync`, `filings-check`). `public_tools.PublicData.van_ban_cong_bo` chỉ đọc `data/filings/`.

**Tech Stack:** Python 3.11, httpx, pypdf (`insights/pdf.py`), Tesseract (`insights/ocr.py`), FastMCP, pytest.

**Spec:** [docs/superpowers/specs/2026-11-28-van-ban-cong-bo-design.md](../superpowers/specs/2026-11-28-van-ban-cong-bo-design.md)

## Global Constraints

- MCP chỉ đọc tệp trong `data/`; `public_tools.py` chỉ import `investment_agent.market…`.
- Mã không có văn bản: `{"thieu": True, "ly_do": "chưa có văn bản công bố của <MÃ> trong kho"}`, cùng câu cho mọi trường hợp (mã sai định dạng vẫn dùng "Mã không hợp lệ." như các công cụ khác).
- `data/report-sources.json` không vào Git; test dùng `tmp_path`. Không có mã thật nào trong test ngoài các mã công khai đã dùng ở test khác (FPT, HPG, KDH là mã HOSE công khai; không gắn chúng với danh sách theo dõi).
- Mỗi đêm tối đa 4 tệp, 25 phút (1.500 giây) cho cả bước; tệp > 30 MB hoặc > 120 trang bỏ qua và ghi lý do; tệp lỗi thử lại tối đa 3 đêm; chỉ văn bản có ngày ≥ 2026-04-01 (văn bản không đọc được ngày vẫn lấy).
- User-Agent `investment-agent/0.1 (personal use)`; nghỉ 1 giây giữa các lần gọi trang; robots.txt kiểm ở `filings-check`.
- Đoạn trích 600 ký tự, tối đa 12 đoạn, danh sách tối đa 40 văn bản; `luu_y` về OCR luôn có.
- Plugin 0.30.0 (công cụ mới).

## Review Focus

1. Trang cổ đông có liên kết PDF tương đối (`/wp-content/...`) → phải ghép thành đường dẫn tuyệt đối theo trang nguồn.
2. Cùng kỳ có cả "BCTC Công ty Mẹ" và "BCTC Hợp nhất" → chỉ lấy bản hợp nhất.
3. Từ khóa có dấu ("thoái vốn") phải khớp chữ OCR sai dấu ("thoái vón") ở mức bỏ dấu; không khớp thì không bịa.
4. Một mã có văn bản, mã khác không: kết quả công cụ không để lộ mã nào khác có văn bản.
5. Hết thời gian giữa chừng: tệp chưa đọc giữ trạng thái "chưa đọc", không bị tính là lỗi.

---

### Task 1: Kho và các hàm thuần (`market/filings.py`)

**Files:** Create `backend/src/investment_agent/market/filings.py`; Test `backend/tests/market/test_filings.py`

**Interfaces — Produces:**
- `links_on_page(html: str, page_url: str) -> list[dict]` → `{"url", "nhan"}` (nhãn đã bỏ thẻ, khoảng trắng gộp; url tuyệt đối; chỉ `.pdf`).
- `classify(nhan: str) -> str | None` → `"bctc"` (có "BCTC"/"Báo cáo tài chính", không chứa "Công ty Mẹ"/"Riêng"), `"nghi_quyet"` (có "Nghị quyết"/"NQ HĐQT"/"Quyết định"/"ĐHĐCĐ"), hoặc `None`.
- `label_date(nhan: str, url: str) -> str | None` → `YYYY-MM-DD` từ "(dd/mm/yyyy)" trong nhãn, không có thì từ `/YYYYMMDD-` trong url.
- `doc_id(url: str) -> str` → 16 ký tự hex đầu của sha1(url).
- `FilingStore(root: Path)`: `read(ma, id) -> dict | None`, `save(record)`, `list(ma) -> list[dict]` (không gồm `trang`, mới nhất trước), `state() / save_state(dict)` ở `root/_state.json`.
- `snippets(records, tu_khoa: str, *, width=600, limit=12) -> tuple[list[dict], bool]` khớp bỏ dấu, không phân biệt hoa thường.

- [ ] **Step 1: Viết test** `test_links_are_absolute_pdf_links_with_their_labels`, `test_consolidated_statements_and_resolutions_are_classified_parent_only_is_not`, `test_the_date_comes_from_the_label_then_the_url`, `test_snippets_match_without_accents_and_say_when_there_are_more`, `test_the_store_lists_newest_first_without_page_text`. Ví dụ giá trị: nhãn `"BCTC Hợp nhất Q2.2026 + Giải trình trong TM (29/07/2026)"` → `bctc`, `"2026-07-29"`; nhãn `"BCTC Công ty Mẹ Q2.2026 (29/07/2026)"` → `None`; url `.../2026/06/20260605-kdh-quyet-dinh...pdf`, nhãn không ngày → `"2026-06-05"`; trang chữ `"Lãi từ thoái vón công ty con 896.333.984"` khớp `tu_khoa="thoái vốn"`.
- [ ] **Step 2:** `.venv/Scripts/python.exe -m pytest backend/tests/market/test_filings.py -q -p no:warnings` → FAIL (module chưa có).
- [ ] **Step 3:** Viết `market/filings.py` (dùng `html.parser` của thư viện chuẩn hoặc regex; `urllib.parse.urljoin`; bỏ dấu bằng `unicodedata` như `insider_docs._plain`).
- [ ] **Step 4:** Chạy lại → PASS; chạy toàn bộ test backend → PASS.
- [ ] **Step 5:** Commit `feat: Văn bản công bố store and page parsing for watched tickers' filings`.

### Task 2: `sync_filings`

**Files:** Modify `market/filings.py`; Test `backend/tests/market/test_filings.py`

**Interfaces — Consumes:** Task 1. **Produces:** `sync_filings(data_dir: Path, symbols: list[str], *, get_text: Callable[[str], str], get_bytes: Callable[[str], bytes], read_pdf: Callable[[bytes], tuple[list[str], int]], now: datetime, clock: Callable[[], float] = time.monotonic, sleep=time.sleep, max_files=4, budget_seconds=1500, since="2026-04-01") -> dict` → `{"read": [ids], "skipped": {id: reason}, "errors": {id: "error:<Type>"}, "pending": int}`.

- Nguồn: `data/report-sources.json` (`bctc`, `cbtt` của từng mã có trong `symbols`) và VNDirect `https://api-finfo.vndirect.com.vn/v4/news?q=tagCodes:<MÃ>~newsDate:gte:<since>&size=100&sort=newsDate:desc`, loại tin `resolutions|meeting|other_rights|management_reports`, tệp từ `attachments[].url`.
- Bỏ trùng: cùng `ngay` và nhãn bỏ dấu giống nhau sau khi bỏ phần trong ngoặc; ưu tiên trang công ty.
- Thứ tự: `bctc` trước `nghi_quyet`, ngày mới trước.
- `_state.json`: `{"<id>": {"attempts": n, "skipped": reason?}}`; bỏ tệp đã lưu, đã `skipped`, hoặc `attempts >= 3`.
- Tệp > 30 MB (`len(bytes)`) hoặc `read_pdf` trả > 120 trang → `skipped`.

- [ ] **Step 1: Viết test** `test_new_statements_are_read_first_up_to_four_a_night`, `test_a_file_seen_on_both_sources_is_read_once`, `test_too_big_files_are_skipped_with_the_reason_and_not_fetched_again`, `test_a_failing_file_is_tried_three_nights_then_left`, `test_the_time_budget_leaves_the_rest_pending_not_failed`, `test_files_before_april_are_left_out`, `test_only_the_given_symbols_are_read`. Dùng `get_text`/`get_bytes` giả theo url, `clock` giả tăng 600 giây mỗi lần `read_pdf`.
- [ ] **Step 2:** Chạy → FAIL.
- [ ] **Step 3:** Viết `sync_filings`; lưu bản ghi đúng các trường ở spec (`ma`, `loai`, `tieu_de`, `ngay`, `nguon`, `trang_nguon`, `lay_luc`, `so_trang`, `ocr`, `trang`).
- [ ] **Step 4:** PASS; toàn bộ test backend PASS.
- [ ] **Step 5:** Commit `feat: filings-sync reads up to four new filings of watched tickers a night`.

### Task 3: CLI và lượt 20:00

**Files:** Modify `backend/src/investment_agent/cli.py`, `scripts/windows/run-after-close.ps1`; Test `backend/tests/test_filings_cli.py`, `backend/tests/test_scheduler_script.py`

**Interfaces — Consumes:** `sync_filings`, `links_on_page`, `classify`. **Produces:** lệnh `filings-sync --data-dir` (exit 0 khi không lỗi, 1 khi có lỗi hoặc thiếu Tesseract) và `filings-check --url <trang>` (in robots.txt cho phép hay không, và các liên kết `bctc`/`nghi_quyet` đọc được; không ghi gì).

- `read_pdf` thật: `pages = extract_pages(data, max_pages=121)`; >120 trang → báo cho `sync_filings` bỏ qua; `with_ocr(data, pages, read=default_reader(), max_pages=120, max_seconds=900)`; trả `(pages, len(ocr_pages))`.
- `run-after-close.ps1`: sau dòng `insider-docs-sync`, `jobs.step --timeout 1800 filings-sync --data-dir $data`, ghi `filings-sync exit=… …` vào log.

- [ ] **Step 1: Viết test** `test_filings_sync_prints_what_it_read_and_exits_1_on_errors` (truyền `read`/`get` giả như `insider_docs_sync`), `test_filings_check_lists_readable_links_and_robots` (get giả), và trong `test_scheduler_script.py` một test rằng `filings-sync` chạy sau `insider-docs-sync` với `--timeout 1800`.
- [ ] **Step 2:** Chạy → FAIL.
- [ ] **Step 3:** Viết lệnh CLI và dòng PowerShell.
- [ ] **Step 4:** PASS; toàn bộ test backend PASS.
- [ ] **Step 5:** Commit `feat: filings-sync in the 20:00 run and filings-check for a company's shareholder page`.

### Task 4: Công cụ MCP `van_ban_cong_bo`

**Files:** Modify `public_tools.py`, `mcp_server.py`, `docs/claude-project-instructions.md`, `plugins/dautucophieu/skills/dautu-ma/SKILL.md`, `plugins/dautucophieu/.claude-plugin/plugin.json`; Test `backend/tests/test_filings_public.py`, `backend/tests/test_public_tools.py` (danh sách công cụ đã duyệt)

**Interfaces — Consumes:** `FilingStore`, `snippets`. **Produces:** `PublicData.van_ban_cong_bo(ma, tu_khoa=None, loai=None, tu_ngay=None) -> dict`:
- không `tu_khoa`: `{"ma", "van_ban": [≤40 bản, không `trang`], "luu_y"}`;
- có `tu_khoa`: `{"ma", "tu_khoa", "doan": [{"tieu_de","ngay","loai","trang","nguon","doan"}], "con_nua", "luu_y"}`; không khớp → `doan: []`, không phải thiếu;
- `loai` ngoài `bctc|nghi_quyet` → `thieu` "loai cần là bctc hoặc nghi_quyet."; `tu_ngay` sai định dạng → `thieu` "Ngày không hợp lệ (cần YYYY-MM-DD).".
- `luu_y`: "Chữ đọc từ bản PDF, phần lớn là bản scan đọc bằng OCR trên máy: số, ngày và dấu có thể sai. Con số quan trọng thì kiểm lại ở trang ghi kèm trong văn bản nguồn."

- [ ] **Step 1: Viết test** `test_without_a_keyword_the_tool_lists_filings_newest_first`, `test_a_keyword_returns_passages_with_page_and_source`, `test_a_ticker_without_filings_is_missing_with_one_reason`, `test_bad_type_or_date_is_missing`, và thêm `van_ban_cong_bo` vào danh sách công cụ đã duyệt.
- [ ] **Step 2:** Chạy → FAIL.
- [ ] **Step 3:** Viết công cụ, đăng ký ở `mcp_server` (mô tả nói rõ dùng cho lãi bất thường, khoản vay, quyết định HĐQT; gợi ý từ khóa "thoái vốn", "thu nhập khác", "vay", "nghị quyết"); thêm vào `docs/claude-project-instructions.md` và bước dùng trong `/dautu-ma` khi `bao_cao_tai_chinh` có `canh_bao_loi_nhuan_ngoai_ban_hang`; plugin 0.30.0. Tên snake_case trong tài liệu chỉ là tên công cụ thật (test_plugin_dautu).
- [ ] **Step 4:** PASS; toàn bộ test backend PASS.
- [ ] **Step 5:** Commit `feat: van_ban_cong_bo on the public MCP searches watched tickers' filings; plugin 0.30.0`.

### Task 5: Kiểm toàn bộ, merge, dữ liệu nguồn

- [ ] `verify.ps1` đạt → merge vào main, push, `update-app.ps1` (MCP từ xa khởi động lại).
- [ ] Lập `data/report-sources.json` cho các mã đang theo dõi bằng `filings-check` từng trang. Việc này để Claude thấy mã của danh sách theo dõi (không phải danh mục nắm giữ), nên chủ sở hữu chọn trước: Claude tự tra, hoặc chủ sở hữu tự điền đường dẫn rồi Claude chỉ chạy `filings-check`. Kết quả báo theo số lượng (số mã có nguồn, số mã chỉ có VNDirect, trang robots chặn), không in danh sách mã ra ngoài máy; chủ sở hữu duyệt rồi lượt 20:00 tự chạy.
