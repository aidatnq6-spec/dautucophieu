# Luận điểm đầu tư và Hậu kiểm quyết định — kế hoạch thực hiện

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mỗi mã đang nắm có luận điểm với điều kiện đo được; phần mềm tự kiểm, nhắc qua Telegram với số thật và kịch bản lịch sử, buộc mỗi
lần giữ tiếp phải có lý do; sau đó hậu kiểm các quyết định đã qua (spec: `docs/superpowers/specs/2026-11-01-luan-diem-hau-kiem-design.md`).

**Architecture:** Logic thuần trong `domain/thesis.py` (kiểu điều kiện, đánh giá, trạng thái) và `domain/hindsight.py` (Phần 2); dịch vụ
`services/theses.py` đọc/ghi kho cá nhân (`theses/main`, có phiên bản), gom "dữ kiện" từ dữ liệu đã lưu, soạn lời nhắc; route FastAPI
`/internal/theses`; lệnh CLI `thesis-check --scope price|data` chạy trong `run-alerts.ps1` (5 phút trong phiên) và `run-after-close.ps1`;
Bản tin tuần thêm một mục; web thêm mục "Luận điểm đầu tư" trên Danh mục và "Hậu kiểm quyết định" trên Nhật ký.

**Tech Stack:** Python 3.11, FastAPI, pydantic, pytest; Next.js (React 19), vitest, Playwright.

**Quy ước có sẵn cần nhớ**
- Giá trong `data/trend-sources/<MÃ>-1d` là nghìn đồng; sổ giao dịch tính bằng đồng (×1000 như `services/drawdown.last_close`).
- Giá vốn: `services/drawdown.held_costs(repo, owner)`; mã đang nắm: `services/holdings_view.held_from_repo`.
- Định giá: `services/holdings_view.fair_value_board(...)["rows"]` → `fair`, `quality.f_score` (`kind` f_score|health, `score`, `level`).
- Lợi nhuận quý: `FundamentalsStore(data/fundamentals).read(s)["quarters"]["YYYY-Qn"]["npat"]`.
- Chuỗi giá trị: logic trong `api/routes/value_chains.py` → tách hàm `chain_labels(data_dir, today) -> {symbol: [label…]}` để dùng chung.
- Nội bộ: `market/insider_deals.insider_deals(store, symbol, get, now)["deals"]` (lưu 1 ngày).
- Telegram theo lịch: `cli._scheduled_telegram()`; Nhật ký: `services/journal.append_entry`.
- Test backend: `.venv/Scripts/python.exe -m pytest backend/tests -q -p no:warnings`; web: `npm.cmd --prefix apps/web run test|lint|typecheck`;
  e2e: `npm.cmd --prefix apps/web run test:e2e -- --reporter=line <lọc>`; trước khi merge: `scripts\windows\verify.ps1` (chỉ push khi đạt).

---

## PR 1 — Luận điểm đầu tư (nhánh `feat/luan-diem-dau-tu`)

### Task 1: Kiểu điều kiện và đánh giá (domain)
**Files:** Create `backend/src/investment_agent/domain/thesis.py`; Test `backend/tests/domain/test_thesis.py`
- `REASONS = ("cheap","earnings","trend","industry","fomo")`, `KINDS`: `loss_vs_cost{pct}`, `close_below{level}`, `above_fair{pct}`,
  `fair_cut{pct}`, `f_score{n}`, `health_weak{}`, `profit_drop{n}`, `macd_weekly{}`, `chain_headwind{}`, `insider_sell{}`; mỗi kiểu có
  `scope` ("price" cho `loss_vs_cost`, còn lại "data") và `applies(kind_of_company)` (f_score chỉ phi tài chính; health_weak chỉ tài chính).
- `evaluate(cond, facts) -> {"state": "ok"|"broken"|"unknown", "reading": str|None, "reason": str|None}`; `facts` có thể thiếu từng mục
  → "unknown" kèm lý do tiếng Việt. MACD tuần: dùng `regroup` + `indicators.macd` trên nến ngày; cắt xuống = phiên tuần cuối macd<signal và
  tuần trước macd≥signal **hoặc** đang dưới từ sau ngày đặt (đã bị phá thì giữ).
- `validate_thesis(raw, *, symbol, company_kind)` → lỗi `ThesisError(code, message)`: lý do rỗng, tham số sai, fomo thiếu `loss_vs_cost`,
  điều kiện không áp dụng.
- Test: mỗi kiểu một ca đạt/phá/thiếu; fomo bắt buộc; f_score cho ngân hàng bị từ chối.

### Task 2: Trạng thái, nhắc bậc 5%, giữ tiếp (domain)
**Files:** Modify `domain/thesis.py`; Test cùng file
- `advance(thesis, results, *, now, price) -> (thesis, events)`: điều kiện "ok"→"broken" ghi `broken_on/broken_price/reading` và phát
  sự kiện `first`; đã broken thì **không** về ok (chỉ cập nhật `current`); giá giảm thêm mỗi 5% so với `broken_price` → sự kiện `step` một
  lần mỗi bậc; điều kiện đang `hold` (đến ngày `until` hoặc đến khi điều kiện thay thế bị phá) không phát sự kiện.
- `hold(thesis, cond_id, *, reason, emotion, new_condition|until, today)`: bắt buộc lý do + (điều kiện mới hoặc ngày ≤ 90 ngày); điều kiện
  cũ chuyển vào `history` (giữ mốc bị phá), điều kiện mới thay chỗ.
- `edit(thesis, changes)`: chỉ sửa điều kiện chưa bị phá; mỗi lần sửa tăng `version`, bản cũ vào `history`.
- Lưu khi đã phá sẵn: lần `advance` đầu tiên phát `first` với mốc ngày lưu.
- Test: không tự về ok khi giá hồi; bậc 5% một lần; hold chặn nhắc của đúng điều kiện đó, điều kiện khác vẫn báo; hết hạn hold thì nhắc lại;
  sửa điều kiện bị phá bị từ chối.

### Task 3: Kịch bản lịch sử (domain)
**Files:** Modify `domain/thesis.py`; Test cùng file
- `scenario(points, *, price, shares)`: dùng `domain/drawdown.max_drawdown` → độ sâu, "lỗ thêm" = shares × price × |độ sâu| (đồng).
- `similar(points, kind, params, horizon=126)`: các lần trong lịch sử (giá đóng cửa) thỏa điều kiện lần đầu (`close_below`: cắt xuống
  mức; `macd_weekly`: cắt xuống), không chồng nhau trong `horizon` phiên; trả trung vị thay đổi sau `horizon` phiên và số lần; < 5 lần →
  `{"count": n, "median": None}`.
- Test với chuỗi tổng hợp.

### Task 4: Lưu trữ và dữ kiện (service)
**Files:** Create `services/theses.py`; Modify `api/routes/value_chains.py` (tách `chain_labels`); Test `backend/tests/services/test_theses.py`
- `read_theses / save_thesis / hold_condition / edit_thesis` trên `theses/main` (`expected_version`, `request_id`); lưu luận điểm tạo mục
  Nhật ký loại "buy" (lý do + lời viết) nếu chưa có mục mua liên kết; giữ tiếp tạo mục "hold".
- `snapshot(facts)` lúc lưu (giá, giá vốn, mức hợp lý, F-Score… có thể thiếu).
- `gather_facts(data_dir, repo, owner, symbols, *, scope, prices=None, today, insider)`: giá vốn, giá (trong phiên từ bảng giá; ngoài
  phiên giá đóng cửa), nến ngày, mức hợp lý/F-Score (data), lợi nhuận quý, nhãn chuỗi, giao dịch nội bộ bán sau ngày đặt.
- Luận điểm khép khi mã không còn trong `held_from_repo` (ghi `closed_on`).
- Test với `MemoryDocumentStore` và thư mục dữ liệu tổng hợp.

### Task 5: Lời nhắc và lượt kiểm (service + CLI)
**Files:** Modify `services/theses.py`, `cli.py`, `scripts/windows/run-alerts.ps1`, `scripts/windows/run-after-close.ps1`; Test `test_theses.py`
- `render_first(symbol, cond, thesis, scenario, similar, lesson=None)`: ba phần như spec; "kịch bản nếu lặp lại, không phải dự báo";
  "Không phải khuyến nghị. Phần mềm không đặt lệnh." `render_step(...)`.
- `thesis_check_run(repo, owner, data_dir, *, scope, facts, send, now, request_id)`: `advance` từng luận điểm mở, gửi gộp một tin; chỉ ghi
  trạng thái "đã gửi" khi gửi thành công (gửi lỗi thì lần sau gửi lại).
- CLI `thesis-check --scope price` (trong phiên; giá từ `build_board` một lượt cho các mã có luận điểm mở) và `--scope data` (sau đóng cửa,
  ngay sau `quarter-alerts` ở mốc 20:00 và mỗi lượt với các điều kiện không phụ thuộc báo cáo). Mỗi bước ghi một dòng log như các bước khác.
- Test: tin nhắn có đủ ba phần, không có chữ "sẽ lỗ"; gửi lỗi không đánh dấu đã gửi.

### Task 6: Bản tin tuần
**Files:** Modify `services/weekly_brief.py`, `cli.py` (`weekly_inputs`); Test `backend/tests/services/test_weekly_brief.py`
- Mục "Luận điểm đã bị phá mà vẫn đang giữ": mỗi điều kiện bị phá không ở trạng thái giữ tiếp: ngày báo đầu, thay đổi giá từ đó, lãi/lỗ
  vị thế hiện tại (đồng); dòng "Chưa có luận điểm: …" cho mã đang nắm thiếu luận điểm.

### Task 7: API
**Files:** Create `api/routes/theses.py`; register in `api/app.py`; Test `backend/tests/api/test_theses_route.py`
- `GET /internal/theses` → `{version, theses:[…với trạng thái điều kiện hiện tại], missing:[mã đang nắm chưa có luận điểm], kinds}`.
- `PUT /internal/theses` action `save|edit|hold` (pydantic, `expected_version`, `request_id`); lỗi 422 `ThesisError`, 409 khi lệch phiên bản.

### Task 8: Giao diện
**Files:** Create `apps/web/src/components/thesis-view.tsx` (+ `thesis-view.test.ts` cho hàm thuần); Modify `portfolio-view.tsx`, `globals.css`;
Test e2e `tests/e2e/thesis.spec.ts`; fixture backend nếu cần
- Mục "Luận điểm đầu tư": thẻ mỗi mã đang nắm; form đặt/sửa (lý do, lời viết, điều kiện với tham số kiểu Việt `levelInput`); fomo bắt buộc
  điều kiện lỗ; trạng thái từng điều kiện (đạt / bị phá từ ngày… / chưa kiểm được: lý do; số đo hiện tại); nút "Giữ tiếp, có lý do"
  (lý do, cảm xúc, điều kiện mới hoặc ngày xem lại ≤ 90 ngày); mã chưa có luận điểm ghi rõ.
- e2e: đặt luận điểm fomo thiếu điều kiện lỗ bị chặn; đặt luận điểm có điều kiện đã phá sẵn hiện "bị phá"; giữ tiếp có lý do; không cuộn ngang.

### Task 9: Hoàn tất PR 1
- Cập nhật `docs/operations` nếu có mục lịch chạy; `verify.ps1`; commit `feat: Luận điểm đầu tư …`; merge `--no-ff` vào `main`; verify lại;
  chỉ push và khởi động lại khi đạt.

## PR 2 — Hậu kiểm quyết định (nhánh `feat/hau-kiem-quyet-dinh`)

### Task 10: Tính hậu kiểm (domain)
**Files:** Create `domain/hindsight.py`; Test `backend/tests/domain/test_hindsight.py`
- Từ sự kiện sổ (`replay` theo thứ tự), giá đóng cửa và VN-Index: lệnh mua/bán ở mốc 3/6/12 tháng (ngày giao dịch gần nhất không sau mốc;
  "chưa tới"; "thiếu giá"); vị thế mở đầu bị bỏ qua và đếm.
- Khoảng giữ khi lỗ quá ngưỡng Kế hoạch sụt giảm hiện tại: bắt đầu, kéo dài, kết thúc (hồi về giá vốn / bán lỗ / đang giữ).
- Luận điểm bị phá: giữ (giá hiện tại hoặc giá bán sau đó) so với bán ngay ở ngày báo đầu.
- Thiên kiến: PGR/PLR (Odean) tại mỗi ngày bán; kết quả 6 tháng theo lý do (luận điểm) và cảm xúc (Nhật ký); mua đuổi (>15% trong 20 phiên).
  Mỗi nhóm < 5 lần → "chưa đủ dữ liệu để kết luận".

### Task 11: API, lời nhắc và giao diện
- `GET /internal/hindsight`; dòng "Bài học của chính bạn" trong lời nhắc luận điểm (chỉ khi ≥ 5 lần); mục "Hậu kiểm quyết định" trên Nhật ký;
  e2e với sổ tổng hợp. Hoàn tất như Task 9.
