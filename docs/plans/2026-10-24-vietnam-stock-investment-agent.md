# Vietnam Stock Investment Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Xây dựng web app cá nhân chạy Windows, quản lý hồ sơ và sổ đầu tư, nghiên cứu 50 cổ phiếu HOSE với dữ liệu tối thiểu 10 năm, đưa khuyến nghị có căn cứ và tự tạo bản tin sau phiên trong ứng dụng/Telegram.

**Architecture:** Next.js phục vụ giao diện và xác minh phiên Firebase; Python FastAPI chỉ nhận yêu cầu nội bộ trên loopback và thực hiện nghiệp vụ. Firestore là nguồn sự thật cho dữ liệu cá nhân; SQLite/Parquet lưu dữ liệu phân tích có phiên bản trên Windows. Worker dùng cùng nghiệp vụ Python để cập nhật theo lịch, gọi OpenRouter theo chính sách dữ liệu và gửi Telegram sau khi kết quả đã được kiểm tra/lưu.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui, Lucide, Firebase Auth/Firestore, Python, FastAPI, Pydantic, Decimal, SQLite, pandas/pyarrow, httpx, pytest, Vitest, Playwright, Windows Task Scheduler.

---

## 0. Phạm vi, quyền thực hiện và nguồn chuẩn

- Thiết kế đã được duyệt: `docs/superpowers/specs/2026-10-24-vietnam-stock-investment-agent-design.md`.
- Bản mẫu tham chiếu: `docs/reference/portfolio-layout.html`; chỉ tham khảo bố cục, không sao chép số giả vào sản phẩm.
- Kho hiện chỉ có tài liệu; chưa có dependency, ứng dụng, credentials hoặc nhà cung cấp dữ liệu đã xác nhận.
- Kế hoạch này chưa chạy lệnh cài đặt, gọi API tính phí, gửi Telegram thật hoặc tạo tài nguyên Firebase.
- Không đặt lệnh chứng khoán. Không tự mua dữ liệu. Thiếu credentials không ngăn làm unit test/fake adapter; phải ghi trạng thái chưa kiểm chứng live, không công bố là hoàn thành luồng thật.
- Trước khi triển khai, dùng branch/worktree riêng. Không đưa `.env`, credentials, kho dữ liệu, bản sao lưu hoặc báo cáo tài chính cá nhân vào Git.
- Các task dưới đây là các mốc nhỏ; mỗi bước có một hành động. Nếu một bước implementation vượt phạm vi một hàm/endpoint/biểu mẫu, tách thành các vòng nhỏ trước khi làm; không gộp toàn bộ task thành một thay đổi lớn.
- Dùng @brainstorming khi cần thay đổi phạm vi đã duyệt. Khi xây UI áp dụng @frontend-design, @ui-ux-pro-max và @vercel-react-best-practices theo phạm vi; không tự khởi tạo site/hosting bên ngoài. Các skill executing-plans/subagent-driven-development phải được tìm trước khi chọn quy trình tương ứng, không giả định có sẵn.

## 1. Điểm kiểm tra và thứ tự phụ thuộc

| Mốc | Task | Điều kiện đi tiếp |
|---|---|---|
| A · Nền tảng kiểm chứng | 1–5 | Chạy được bộ kiểm tra, hợp đồng dữ liệu rõ, báo cáo khả thi nguồn có bằng chứng |
| B · Sổ cá nhân đáng tin | 6–13 | Phân quyền, hồ sơ, khảo sát, phân bổ, sổ và quyền/cổ tức đối chiếu đúng |
| C · Phân tích có nguồn | 14–20 | Danh sách được duyệt, chuỗi dữ liệu kiểm tra, giả định định giá được duyệt |
| D · AI kiểm soát được | 21–23 | Khóa/chi phí/quyền dữ liệu/schema/fallback được kiểm tra |
| E · Trải nghiệm và tự động | 24–29 | Giao diện A+B/C, bản tin lưu trước gửi, lịch và khôi phục hoạt động |
| F · Nghiệm thu | 30–31 | Kiểm thử toàn luồng, đối chiếu dữ liệu thật và báo cáo nghiệm thu |

Task 5 có thể kết luận nguồn chưa khả thi. Khi đó vẫn làm B, giao diện và C/D/E với fixture gắn nhãn; chặn khuyến nghị thật phụ thuộc dữ liệu thiếu. Không tự thay yêu cầu 50 mã/10 năm. Chỉ mở chế độ phân tích thật toàn phạm vi khi đủ mốc dữ liệu; chỉ bật AI/Telegram thật sau cấu hình được người dùng xác nhận.

## 2. Quy ước triển khai

### 2.1 Cấu trúc đích

```text
apps/web/                         Next.js, npm lockfile, UI, session, proxy
backend/pyproject.toml            Python package investment_agent
backend/requirements.lock         Dependency đã khóa và kiểm tra
backend/src/investment_agent/
  api/ domain/ repositories/ market/ valuation/ ai/ notifications/ jobs/
backend/tests/                    Unit và integration tests
contracts/                       JSON Schema/OpenAPI và fixture công khai
config/                          Chính sách versioned, không bí mật
scripts/windows/                 Launcher, tác vụ và sao lưu
tests/e2e/                       Luồng xuyên browser/API/kho dữ liệu
tests/fixtures/                  Dữ liệu tổng hợp, luôn có nhãn synthetic
docs/data/ docs/decisions/ docs/operations/ docs/verification/
data/                            Bỏ qua Git: SQLite, Parquet, tài liệu
backups/                         Bỏ qua Git; không chứa khóa
```

### 2.2 Lệnh chuẩn

Tất cả lệnh dưới đây chạy từ gốc kho bằng PowerShell. Sau Task 1:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run test -- --run
npm --prefix apps/web run build
```

Test nhỏ dùng đường dẫn cụ thể của task. FAIL trước implementation phải là assertion/hàm chưa có hợp lý, không phải lỗi interpreter hoặc dependency chưa cài. Không thực hiện kiểm thử live trong bộ unit test mặc định. Mỗi task nghiệp vụ kết thúc với commit cụ thể; tên commit đề xuất ở cuối task. Không dùng `git add .` để tránh kéo dữ liệu/khóa.

### 2.3 Hợp đồng bắt buộc

- Tiền VND/Decimal qua JSON là chuỗi, ví dụ `"500000000"`; không truyền số thực rồi đổi về Decimal. Tỷ lệ là chuỗi thập phân từ 0 đến 1. Giá trị hiển thị có thể làm tròn nhưng sổ không dùng số hiển thị để tính tiếp.
- ID doanh nghiệp ổn định khác ticker/sàn. Thời gian UTC có timezone, ngày phiên/hiệu lực diễn giải theo Asia/Ho_Chi_Minh.
- Mỗi observation có `entity_id, metric, period_end, published_at, observed_at, revision_id, source_id, unit, value, quality_status, provenance_mode`.
- Mỗi snapshot có phiên bản hồ sơ, danh mục, danh sách, dữ liệu, giả định và policy. Báo cáo chỉ publish một lần cho cùng snapshot/version.
- `null` kèm lý do cho dữ liệu không hợp lệ; không dùng 0 thay dữ liệu thiếu. Chế độ `synthetic`, `historical_as_reported`, `latest_restated` không trộn lẫn.
- Các trạng thái report: `building`, `validated`, `published`, `incomplete`, `failed`, `superseded`. Delivery riêng: `pending`, `sending`, `sent`, `retryable`, `unknown`, `failed`.
- API lỗi trả `code`, thông điệp tiếng Việt và `job_id/correlation_id` nếu có; không trả token, URL Telegram chứa token hoặc payload cá nhân trong stacktrace.

## Task 1: Khóa môi trường và bộ lệnh kiểm tra

**Files — create:** `backend/pyproject.toml`, `backend/requirements.lock`, `apps/web/package.json`, `apps/web/package-lock.json`, `apps/web/tsconfig.json`, `apps/web/vitest.config.ts`, `apps/web/eslint.config.mjs`, `scripts/windows/doctor.ps1`, `README.md`; **modify:** `.gitignore`.

1. Kiểm tra Node/Python/npm/Git trên Windows; ghi phiên bản hỗ trợ trong README sau đối chiếu docs. Chọn Python có wheel pandas/pyarrow và Node LTS phù hợp Next.js; khóa dependency, không dùng alias `latest` trong manifest đã commit.
2. Tạo scaffold tối thiểu Next.js App Router và Python package; chưa thêm dữ liệu/AI thật. Tạo npm scripts `typecheck`, `lint`, `test`, `build`, `test:e2e`. Python dev deps gồm pytest/httpx; UI tests dùng Vitest/Testing Library, e2e dùng Playwright.
3. Tạo `.env.example` chỉ tên biến; Git bỏ qua `.env*` trừ example, `.venv`, `.next`, node_modules, data, backups, log và secrets; không bỏ qua thư mục fixture.
4. Chạy `./scripts/windows/doctor.ps1` trên máy đủ và máy giả thiếu biến; mong đợi chẩn đoán tên biến cần thiết, không in giá trị; chạy typecheck/build tối thiểu. Không thêm test kiểm tra tồn tại file scaffold.
5. Commit: `chore: bootstrap local web and analysis runtimes`.

## Task 2: Hợp đồng dữ liệu và công thức tiền

**Files — create:** `backend/src/investment_agent/domain/money.py`, `domain/models.py`, `contracts/domain.schema.json`, `backend/tests/domain/test_money.py`, `backend/tests/domain/test_contracts.py`.

1. Viết test roundtrip Decimal và reject float đầu vào, số tiền âm khi không hợp lệ, timestamp thiếu timezone. Ví dụ:

```python
from decimal import Decimal
from investment_agent.domain.money import parse_amount

def test_money_roundtrip_is_exact():
    value = parse_amount("100000000.125")
    assert value == Decimal("100000000.125")
    assert parse_amount(str(value)) == value
```

2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_money.py backend/tests/domain/test_contracts.py -q`; mong đợi FAIL vì parser/schema chưa có.
3. Dùng Pydantic strict validation cho chuỗi decimal; danh sách enum và range explicit. Export schema và tạo TypeScript types từ schema/OpenAPI; tránh viết hai bản logic tài chính ở Python và TS.
4. Chạy lại; PASS cả biên Decimal, giá trị thiếu, ngày và version. Ghi chính sách làm tròn khi hiển thị, khớp tiền và phân bổ giá vốn.
5. Commit: `feat: define exact financial domain contracts`.

## Task 3: Kho cục bộ có revision và snapshot

**Files — create:** `backend/src/investment_agent/repositories/sqlite.py`, `repositories/migrations/001_initial.sql`, `market/parquet_store.py`, `backend/tests/repositories/test_snapshots.py`.

1. Viết test: hai revision cùng kỳ giữ được bản cũ; publish thất bại không làm snapshot nửa vời xuất hiện; retry không tạo quan sát trùng.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/repositories/test_snapshots.py -q`; mong đợi FAIL.
3. Tạo migrations có schema version; SQLite metadata/job/manifest, Parquet ghi file tạm rồi atomic replace; snapshot tham chiếu manifest bất biến. Một writer, transaction ngắn, không giữ transaction khi gọi mạng.
4. Chạy lại PASS; mở lại DB sau giả lập mất tiến trình, xác nhận snapshot cũ còn đọc được và file mồ côi không được publish.
5. Commit: `feat: persist versioned analysis snapshots locally`.

## Task 4: Bộ kiểm tra khả thi nguồn dữ liệu

**Files — create:** `backend/src/investment_agent/market/base.py`, `market/coverage.py`, `cli.py`, `tests/fixtures/market/coverage_cases.json`, `backend/tests/market/test_coverage.py`, `docs/data/source-evaluation-template.md`.

1. Viết test coverage: 10 năm/10 kỳ năm/40 quý đủ; thiếu lịch sử bị loại; ticker chuyển sàn cùng entity được nối; issuer khác cùng ticker không nối; không có timestamp công bố không đạt as-reported.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/market/test_coverage.py -q`; FAIL.
3. Tạo giao diện adapter `capabilities/fetch_prices/fetch_financials/fetch_actions/fetch_disclosures`; capability không được đoán từ tên gói. Coverage report tách giá, tài chính, ratios, corporate actions, thời điểm công bố, quyền sử dụng, loại dữ liệu và phần thiếu.
4. Test PASS với fixture tổng hợp. Tạo CLI `python -m investment_agent.cli data-audit --fixtures` xuất JSON và Markdown, không gọi mạng.
5. Commit: `feat: audit market data coverage and provenance`.

## Task 5: Khảo sát nguồn thật và quyết định khả thi

**Files — create:** `docs/data/2026-10-24-source-feasibility.md`, `config/data-sources.example.json`, `backend/src/investment_agent/market/providers/vnstock_adapter.py`, `market/providers/fiinquant_adapter.py`; chỉ triển khai adapter tương ứng nguồn thực sự được phép dùng.

1. Kiểm tra tài liệu chính thức, điều khoản theo gói/tài khoản và API hiện hành; lập ma trận giá/financial/action/as-reported/ratios/macro. Không tạo tài khoản, chấp nhận hợp đồng hay mua gói thay người dùng.
2. Chạy audit nhỏ trên ứng viên từ ít nhất ngân hàng, phi tài chính, chu kỳ, bất động sản và một mã chuyển sàn; khi cần key, người dùng cấu hình cục bộ. Lưu thống kê công khai và provenance, không credentials/raw data bị hạn chế vào Git.
3. Đo độ sâu và sai biệt với một số báo cáo gốc, quyền điều chỉnh giá và ngày công bố; sau đó audit tất cả ứng viên trước đưa vào danh sách chính thức 50 mã. Không suy rộng vài mã đạt thành toàn bộ đạt.
4. Ghi kết luận `feasible`, `partial` hoặc `blocked`, chi phí đã xác minh/chưa rõ, công sức và phạm vi không hỗ trợ. Thiếu lịch sử as-reported: không phát hành đánh giá lịch sử có dùng dữ liệu tương lai; trình quyết định nguồn/phí nếu cần, không tự hạ tiêu chí.
5. Commit adapter, test adapter với response đã giảm thông tin phù hợp quyền nguồn và báo cáo: `docs: record evidence for data source feasibility`. Gate A chỉ đạt về nguồn khi có bằng chứng; task khác có thể tiếp tục ở chế độ synthetic.

## Task 6: Firebase một tài khoản và proxy nội bộ

**Files — create:** `apps/web/src/lib/server/firebase-admin.ts`, `lib/server/session.ts`, `lib/server/python-client.ts`, `app/api/session/route.ts`, `app/api/logout/route.ts`, `backend/src/investment_agent/api/app.py`, `api/auth.py`, `api/routes/health.py`, `firebase/firestore.rules`, `backend/tests/api/test_auth.py`, `apps/web/src/lib/server/session.test.ts`.

1. Test Firebase UID ngoài allowlist, phiên hết hạn/revoked, thiếu CSRF/origin, thiếu internal token hoặc context chữ ký hết hạn đều bị từ chối trước đọc/ghi cá nhân; health không tiết lộ thông tin.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/api/test_auth.py -q` và `npm --prefix apps/web run test -- --run src/lib/server/session.test.ts`; FAIL.
3. Next xác minh Firebase ID token để tạo session cookie HttpOnly/SameSite, kiểm tra CSRF và UID; cookie secure khi dùng HTTPS, có cấu hình localhost rõ. Proxy gửi UID/role/correlation cùng internal token và chữ ký timestamp/request body; Python chỉ tin server context đã xác minh, không tin header UID từ browser. Scheduler gọi application service cục bộ bằng owner identity cấu hình, không endpoint công khai giả UID.
4. Admin Firestore chỉ có backend nghiệp vụ; mọi đường truy cập đều enforce owner vì Admin SDK bỏ qua Rules. Rules client mặc định deny. Chạy test PASS; emulator dùng cho integration, không bypass auth bằng cờ được phép trên môi trường thật.
5. Commit: `feat: secure single-owner sessions and local api bridge`.

## Task 7: Firestore là nguồn sự thật cho dữ liệu cá nhân

**Files — create:** `backend/src/investment_agent/repositories/personal.py`, `repositories/firestore.py`, `repositories/personal_cache.py`, `backend/tests/repositories/test_personal_repository.py`, `firebase/firestore.indexes.json`.

1. Test compare-and-set version, request idempotency, owner isolation và mất Firebase không âm thầm ghi vào cache. Kiểm tra cập nhật trùng retry chỉ tạo một phiên bản nghiệp vụ.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/repositories/test_personal_repository.py -q`; FAIL.
3. Dùng namespace `owners/{uid}` cho profile_versions, risk_versions, ledger_events, approvals, valuation_assumptions, reports, settings. Firestore transaction kiểm tra version/request ID; cache SQLite chỉ là bản sao có version/verified_at, không trở thành sổ offline thứ hai. Cập nhật cấu hình không chứa bí mật; credentials đọc từ nơi cục bộ được bảo vệ.
4. PASS với fake repository và emulator. Mất kết nối cho xem bản cũ có nhãn, từ chối mutation và publish khuyến nghị mới nếu không xác minh version; không chặn cập nhật dữ liệu thị trường độc lập.
5. Commit: `feat: version personal records in firestore`.

## Task 8: Hồ sơ và vốn có thể đầu tư

**Files — create:** `backend/src/investment_agent/domain/profile.py`, `domain/investable_capital.py`, `api/routes/profile.py`, `backend/tests/domain/test_investable_capital.py`.

1. Viết test tài sản 800 triệu, dự phòng 200, nhu cầu chưa được bù 100 ⇒ vốn 500; tiền/cổ phiếu trong sổ không cộng lại; chi thường xuyên đã bù không trừ lần hai; mục tiêu 24 tháng cần bảo toàn vẫn tách; vốn không dương trả trạng thái không phù hợp.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_investable_capital.py -q`; FAIL.
3. Mỗi tài sản có `asset_id, ledger_link, liquidity, earmarks`; mỗi mục tiêu có ngày, số tiền, nguồn bù đã dành, cờ bảo toàn, khả năng trì hoãn và xác nhận. Trả breakdown khoản trừ + tổng vốn, không chỉ con số. Không cho cùng một nguồn bù tài trợ nhiều mục tiêu vượt số tiền.
4. PASS; test quỹ dự phòng khai báo đang nằm trong cổ phiếu tạo cảnh báo thiếu thanh khoản. Lưu profile version + xác nhận, nhắc làm mới trước kỳ tháng; mặc định quá 31 ngày cần xác nhận lại trước khuyến nghị mới, nhưng vẫn cho báo cáo tài sản.
5. Commit: `feat: calculate confirmed investable capital`.

## Task 9: Khảo sát 13 câu và kiểm tra khả năng tài chính

**Files — create:** `config/risk-questionnaire.vi.json`, `backend/src/investment_agent/domain/risk.py`, `api/routes/risk.py`, `backend/tests/domain/test_risk.py`.

1. Test toàn bộ biên 13/19/20/26/27/33/34/40/41/46/47/52; reject thiếu/trùng/câu trả lời ngoài A–D. Test tổng cao vẫn bị capacity flag khi câu 4/7=A.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_risk.py -q`; FAIL.
3. Sao đúng 13 câu từ thiết kế; config version bất biến. Core phân loại có thể bắt đầu bằng:

```python
BOUNDS = ((19, "very_safe"), (26, "cautious"), (33, "moderately_cautious"),
          (40, "balanced"), (46, "growth"), (52, "strong_growth"))

def classify_total(total: int) -> str:
    if type(total) is not int or not 13 <= total <= 52:
        raise ValueError("invalid risk score")
    return next(group for maximum, group in BOUNDS if total <= maximum)
```

Thêm mapping A–D và kiểm tra độc lập capacity/conflict; không trả mỗi nhóm. Đánh dấu đây là khảo sát tổng hợp chưa được kiểm định.
4. PASS cả mâu thuẫn câu 10=A, 11/13=D và hồ sơ khác câu trả lời; mutation lưu đủ câu, score, version, flags và thời điểm.
5. Commit: `feat: implement versioned risk assessment`.

## Task 10: Phân bổ cơ sở và ngoại lệ 90%

**Files — create:** `config/allocation-policy.json`, `backend/src/investment_agent/domain/allocation.py`, `domain/exception_review.py`, `backend/tests/domain/test_allocation.py`.

1. Test cơ sở 0/10/25/35/50/60%, không chia vốn bằng 0. Ngoại lệ chỉ strong_growth, chặn khi thiếu một điều kiện, vượt 90%, dưới 8 mã/4 ngành, trên 15% issuer hoặc 30% ngành. Gộp issuer cùng kiểm soát.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_allocation.py -q`; FAIL.
3. Policy version hóa; năm nhóm đầu không đề xuất mua mới vượt mức cơ sở. Strong_growth có hồ sơ ngoại lệ với quyền kéo dài thời gian, tiền không vay, dự phòng/dòng tiền đã xác nhận, kịch bản lỗ 30/50/60% và xác nhận. Validator kiểm tra danh mục sau đề xuất; thiếu dữ liệu ngành/nhóm kiểm soát thì chưa đủ điều kiện, không coi là đa dạng.
4. PASS; tăng giá vượt trần sinh cảnh báo chứ không ghi lệnh bán. Proposal chia target dài hạn và lượng giải ngân hiện tại; không dùng P/B<1 làm override policy.
5. Commit: `feat: enforce portfolio allocation and exception policy`.

## Task 11: Sổ mua/bán, phí và số dư đầu

**Files — create:** `backend/src/investment_agent/domain/ledger.py`, `domain/positions.py`, `api/routes/ledger.py`, `backend/tests/domain/test_ledger.py`.

1. Viết test hai lần mua, một lần bán, phí/thuế, nộp/rút và số dư đầu. Oracle không phí: mua 100×20.000, mua 100×30.000, bán 100×28.000 ⇒ lãi thực hiện 300.000, còn 100 CP giá vốn 25.000. Test âm, bán vượt và ngày/thứ tự trùng gây mơ hồ.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_ledger.py -q`; FAIL.
3. Pure reducer Decimal theo `(effective_at, sequence, event_id)`; weighted moving average, giữ cost precision. Purchase fee vào cost, sell fees/taxes vào proceeds. Opening balance có phạm vi hiệu quả từ ngày bắt đầu; thuế/phí nhập thực tế không hardcode tỷ lệ.
4. PASS; test đối chiếu tiền và số lượng sau chuỗi dài không mất VND vì làm tròn hiển thị. Ghi giao dịch phải dùng repository idempotency, không ghi lệnh từ AI.
5. Commit: `feat: maintain exact moving-average investment ledger`.

## Task 12: Cổ tức, quyền và tiền chờ thanh toán

**Files — create:** `backend/src/investment_agent/domain/corporate_actions.py`, `domain/settlement.py`, `backend/tests/domain/test_corporate_actions.py`, `docs/decisions/market-rules.md`.

1. Test cổ tức tiền dự kiến chuyển thực nhận không tăng thu nhập hai lần; cổ phiếu thưởng tổng cost không đổi; chờ nhận không được bán; tiền bán chờ thanh toán không thành buying power ngay.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_corporate_actions.py -q`; FAIL.
3. Gắn action ID/quyền theo số sở hữu đủ điều kiện, entitlement/receivable và paid/credited riêng; ghi ngày không hưởng quyền/record/payment/tradable theo nguồn. Thuế/rounding phần lẻ ghi thực tế. Quyền mua/split/merge có explicit event, không hỗ trợ thì chặn phần phân tích chịu ảnh hưởng. Không dùng giá adjusted cho định giá tài sản thực rồi cộng cổ tức lần nữa.
4. Kiểm chứng quy tắc thị trường và T+ từ nguồn chính thức trước cấu hình; nếu chưa có dùng số khả dụng người dùng xác nhận, hiện hạn chế. Test PASS khi điều chỉnh cổ tức dự kiến/thuế thực khác, không biến giảm giá ngày quyền thành lỗ giả của tổng tài sản gồm receivable.
5. Commit: `feat: account for dividends entitlements and settlement`.

## Task 13: Sửa giao dịch và đối chiếu hiệu quả

**Files — create:** `backend/src/investment_agent/domain/reconciliation.py`, `domain/performance.py`, `backend/tests/domain/test_reconciliation.py`; **modify:** `domain/ledger.py`, `api/routes/ledger.py`.

1. Test sửa lùi ngày, hủy có thể khôi phục, retry sửa không lặp, và tiền nộp không tính lợi nhuận. Oracle: tài sản cuối − đầu − nộp ròng = realized + unrealized + net dividend income, kể cả quyền chưa nhận theo cùng accounting policy.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_reconciliation.py -q`; FAIL.
3. Event correction tham chiếu bản gốc, replay sau mốc ảnh hưởng; invalidation snapshot/khuyến nghị cũ, giữ audit trail. Giá thiếu không bằng 0; unrealized và portfolio valuation có quality status. Tách realized/unrealized/dividends, chưa hiển thị TWR/XIRR nếu chưa triển khai và kiểm chứng riêng.
4. PASS với property-based hoặc chuỗi giao dịch có oracle độc lập; xác nhận replay và tính lần đầu cho kết quả giống nhau. Không nhận dữ liệu tài khoản thật làm fixture Git.
5. Commit: `feat: reconcile portfolio performance and ledger corrections`.

## Task 14: Danh sách 50 mã có phê duyệt

**Files — create:** `backend/src/investment_agent/market/universe.py`, `api/routes/universe.py`, `backend/tests/market/test_universe.py`, `config/universe-policy.json`.

1. Test đề xuất chưa duyệt không đổi active version; duyệt 49 mã không thành danh sách đủ 50; mã không hiện HOSE hoặc thiếu 10 năm không đạt; danh mục sở hữu ngoài universe vẫn giữ.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/market/test_universe.py -q`; FAIL.
3. Gắn coverage audit vào từng candidate, tiêu chí thanh khoản/capitalization/industry và ngày hiệu lực; trình diff thêm/loại. Approval dùng version concurrency, không tự duyệt khi job định kỳ chạy. Không giả định 5 tỷ/90%/2.000 tỷ là ngưỡng bất biến: hiển thị policy đang dùng, thay đổi cần xác nhận.
4. PASS; mã hủy/chuyển sàn/rủi ro nặng không bị xóa giao dịch, giữ nguồn lịch sử, chỉ cảnh báo/ngừng đề xuất mua. Activate đủ 50 chỉ khi audit tất cả đạt.
5. Commit: `feat: require approval for research universe changes`.

## Task 15: Đồng bộ giá, lịch thị trường và sự kiện vốn

**Files — create:** `backend/src/investment_agent/market/calendar.py`, `market/prices.py`, `market/security_master.py`, `backend/tests/market/test_price_pipeline.py`.

1. Test ngày nghỉ không sinh nến, nghỉ/suspended không forward-fill thành giao dịch; chuyển sàn nối đúng issuer; split/cổ tức có factor và raw prices riêng; retry không trùng record.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/market/test_price_pipeline.py -q`; FAIL.
3. Tải lịch sử chia batch có checkpoint, rate-limit theo nguồn; cập nhật delta có lookback sửa dữ liệu và revision. Ticker mapping có valid_from/to, sàn và entity_id; kiểm tra currency/unit/timezone và chất lượng trước publish.
4. PASS với fixture; live read-only một mã đủ quyền để đối chiếu giá cuối ngày theo ngày phiên. Không đánh dấu toàn bộ provider ổn định sau một lần gọi thành công.
5. Commit: `feat: ingest verified prices and corporate action factors`.

## Task 16: Tài chính và P/E/P/B theo thời điểm

**Files — create:** `backend/src/investment_agent/market/financials.py`, `market/asof.py`, `market/ratios.py`, `backend/tests/market/test_asof_ratios.py`.

1. Test báo cáo công bố sau ngày định giá không được dùng, revision tương lai không thay quá khứ; TTM không cộng annual vào bốn quý; EPS/equity không dương ⇒ unavailable với lý do.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/market/test_asof_ratios.py -q`; FAIL.
3. As-of chọn revision `published_at <= valuation_time`; date-only không rõ giờ thì áp dụng từ phiên kế tiếp và ghi quy tắc. Báo cáo hợp nhất/riêng tách, quarterly/annual tách, units chuẩn; EPS/cost of shares/dilution có công thức source-version. Chỉ tạo adjusted ratio khi denominator/price/share basis nhất quán; không gắn EPS hiện tại vào 10 năm giá.
4. PASS; kiểm tra thủ công một issuer qua phát hành/split và revision. Nếu nguồn thiếu thời điểm thì chỉ latest-restated và chặn tính năng đòi as-reported; coverage report không báo đạt giả.
5. Commit: `feat: compute point-in-time financial valuation ratios`.

## Task 17: Vĩ mô, ngành, tài liệu và bằng chứng quản trị

**Files — create:** `backend/src/investment_agent/market/macro.py`, `market/industry.py`, `market/disclosures.py`, `market/evidence.py`, `backend/tests/market/test_evidence.py`.

1. Test tài liệu có source URL/ngày/version; số liệu vĩ mô sửa không xóa vintage; ngành tổng hợp mẫu phải ghi số mã và độ phủ; “không tìm thấy vi phạm” không sinh nhãn chính trực.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/market/test_evidence.py -q`; FAIL.
3. Adapter Cục Thống kê/NHNN theo khả năng thật; tài liệu doanh nghiệp lưu checksum/provenance/quyền nguồn. Trích bảng có đơn vị/trang, kiểm tra với source trước coi verified. Trích xuất OCR/LLM là candidate cần xác minh, không tự thay số chuẩn. Evidence loại official/disputed/unverified, có phản hồi doanh nghiệp khi tìm thấy.
4. PASS; tạo analysis pack vĩ mô/ngành/entity với dữ kiện và khoảng trống riêng. Không tuyên bố tăng trưởng toàn ngành từ mẫu 50 mã hoặc nhóm vài doanh nghiệp.
5. Commit: `feat: build sourced macro industry and governance evidence`.

## Task 18: DCF, chiết khấu cổ tức và giả định có duyệt

**Files — create:** `backend/src/investment_agent/valuation/assumptions.py`, `valuation/dcf.py`, `valuation/dividends.py`, `api/routes/valuation_assumptions.py`, `backend/tests/valuation/test_cashflow_models.py`.

1. Test PV theo ví dụ kiểm tay; terminal growth >= discount bị từ chối; FCFF trừ net debt đúng một lần; FCFE/DDM không trừ net debt lại; draft assumptions không tạo vùng mua active.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/valuation/test_cashflow_models.py -q`; FAIL.
3. Discount Decimal/precision theo policy, terminal và explicit forecast riêng. Lưu base/down/up, reinvestment, debt, cash, minority/non-operating assets và shares; chọn FCFF hoặc equity rõ ràng, không trộn. Approval owner tạo immutable version; chưa duyệt trả draft valuation có nhãn, không khuyến nghị mua.
4. PASS; sensitivity tăng discount làm PV giảm với cùng dòng tiền dương; mô hình không đủ đầu vào trả unavailable, không sinh giá mặc định.
5. Commit: `feat: value approved cashflow and dividend scenarios`.

## Task 19: Ngân hàng, NAV dự án và doanh nghiệp chu kỳ

**Files — create:** `backend/src/investment_agent/valuation/residual_income.py`, `valuation/nav.py`, `valuation/cyclical.py`, `valuation/selector.py`, `backend/tests/valuation/test_sector_models.py`.

1. Test residual income zero ⇒ value bằng book equity; ROE bằng cost equity không tự tạo premium; NAV trừ nghĩa vụ dự án/nợ không hai lần; cycle normalization không lấy riêng đỉnh EPS làm mức bền vững.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/valuation/test_sector_models.py -q`; FAIL.
3. Model selector theo economics từng issuer, không chỉ tag ngành. Residual income có regulatory capital/ROE scenario; NAV có xác suất/pháp lý/tiến độ/nghĩa vụ và ownership; chu kỳ có cửa sổ normalization và lý do. Tất cả tham chiếu approved assumption version. Thiếu project data thì unavailable, không thay bằng P/B<1 rồi kết luận rẻ.
4. PASS với oracle độc lập mỗi model; không lấy average cơ học giữa output không cùng basis. Cross-check comparables ghi nguồn và các khác biệt ROE/tăng trưởng/rủi ro.
5. Commit: `feat: add sector-specific valuation models`.

## Task 20: Vùng giá, cơ hội và khuyến nghị định lượng

**Files — create:** `backend/src/investment_agent/valuation/price_zones.py`, `domain/recommendations.py`, `backend/tests/domain/test_recommendations.py`.

1. Test P/B<1 không override evidence/capacity; thiếu dữ liệu trả wait/insufficient; cash phí/thuế/settlement không đủ thì giảm quantity; target/final weights không vi phạm policy.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/domain/test_recommendations.py -q`; FAIL.
3. Tính margin of safety theo giá trị ước tính và basis explicit; không có ngưỡng mua cố định cho mọi model. Ngưỡng phải nằm trong approved assumptions/policy. Kết quả gồm action, zone, target, tranche, amount/shares, constraints, source IDs, invalidate_conditions. Rounding số lượng theo bộ market rules đã xác minh; nếu chưa có chỉ đề xuất tiền và yêu cầu xác nhận quantity/khả dụng, không giả số lô.
4. PASS; kiểm tra danh mục sau đề xuất, không chỉ từng lệnh riêng. Lịch sử 10 năm ghi window chính xác; không suy “rẻ nhất lịch sử” vượt phần dữ liệu đã xác minh.
5. Commit: `feat: generate constraint-checked investment proposals`.

## Task 21: Secrets, danh sách model và ngân sách OpenRouter

**Files — create:** `backend/src/investment_agent/settings.py`, `ai/openrouter.py`, `ai/catalog.py`, `ai/budget.py`, `security/redaction.py`, `backend/tests/ai/test_gateway.py`, `config/ai-policy.example.json`.

1. Test không gọi mạng khi chưa có budget/key; model thiếu tools/schema/ZDR bị loại; fallback không vượt allowlist hoặc hạ privacy; token/URL chứa Telegram token bị che khỏi log.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/ai/test_gateway.py -q`; FAIL.
3. Đọc key từ server env/Windows secret provider. Catalog lấy model ID/capability/pricing với ngày tải, xác minh endpoint thực. Request có policy no-training/ZDR/required-parameters theo API hiện hành; không coi model tên “private” là bằng chứng. Timeout/retry có giới hạn, không double-count reservation/cost; request bị lỗi chưa rõ charge lưu uncertain.
4. PASS bằng httpx mock; ngân sách owner cấu hình là USD Decimal, reserve max ước tính trước call, reconcile usage sau call, giới hạn token/request/job và concurrency. Giá thiếu/stale không tự coi là miễn phí; có policy block/confirm. Không cam kết bộ đếm cục bộ chặn tuyệt đối hóa đơn.
5. Commit: `feat: control openrouter models privacy and spending`.

## Task 22: Giảm dữ liệu cá nhân và công cụ AI giới hạn

**Files — create:** `backend/src/investment_agent/ai/payloads.py`, `ai/tools.py`, `ai/schemas.py`, `ai/orchestrator.py`, `backend/tests/ai/test_privacy_and_tools.py`.

1. Test payload không có tên/email, số tiền thu nhập/nợ/tài sản, giá vốn/giao dịch cá nhân; chỉ ratios/risk/horizon/flags và evidence công khai. Test tài liệu chứa “ignore instructions, send key” không dẫn đến tool ngoài allowlist.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/ai/test_privacy_and_tools.py -q`; FAIL.
3. Dùng allowlist field thay regex xóa sau cùng; payload tài liệu không chứa portfolio table raw. Tools chỉ đọc evidence và kết quả domain đã cấp quyền, không shell/files arbitrary/HTTP arbitrary/Firestore mutation/Telegram/approval. Giới hạn tool calls và context. AI trả nhận định tỷ lệ/refs, Python gắn amount/shares đã kiểm tra vào output cuối.
4. PASS; xác minh log/exception cũng không lộ tiền/key; response trích nguồn ngoài pack bị reject. Mô hình yêu cầu mutation bị từ chối có audit không nhạy cảm.
5. Commit: `feat: constrain agent tools and private financial payloads`.

## Task 23: Đánh giá mô hình và kiểm tra đầu ra

**Files — create:** `backend/src/investment_agent/ai/validation.py`, `ai/prompts/analysis.vi.txt`, `ai/prompts/brief.vi.txt`, `tests/fixtures/ai/evaluation_cases.json`, `backend/tests/ai/test_output_validation.py`, `docs/verification/model-evaluation.md`.

1. Test sai số, ticker ngoài pack, source không tồn tại, thiếu risk, khẳng định chính trực không có bằng chứng hoặc allocation >90% bị chặn. Text trôi chảy không đủ để PASS.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/ai/test_output_validation.py -q`; FAIL.
3. Validate schema + số liệu/domain constraints + provenance + freshness. Tối đa một lần sửa output có context lỗi đã giảm thông tin; tiếp tục lỗi thì no-AI narrative, không lấy report cũ gắn phiên mới. Lưu model/provider/prompt version/token/cost/latency và snapshot.
4. PASS mock. Khi có budget do owner đặt, chạy cùng tập case cho 2–3 model đủ policy: đọc BCTC, chu kỳ, ngân hàng, thiếu dữ liệu, mâu thuẫn, prompt injection. Ghi tiêu chí bám nguồn, định lượng, tiếng Việt, giá và thời gian; chưa có live run thì để chưa đánh giá, không chọn “tốt nhất” bằng quảng cáo.
5. Commit: `feat: validate and evaluate investment analysis outputs`.

## Task 24: Giao diện thiết lập, hồ sơ và giao dịch

**Files — create:** `apps/web/src/app/(private)/layout.tsx`, `(private)/onboarding/page.tsx`, `(private)/profile/page.tsx`, `(private)/portfolio/page.tsx`, `components/profile-form.tsx`, `components/risk-survey.tsx`, `components/transaction-form.tsx`, `lib/api.ts`, `tests/e2e/onboarding.spec.ts`.

1. Viết e2e với backend fixture: thiếu mục tiêu/khảo sát không mở cá nhân hóa; nhập mua/bán và sửa hiển thị cost/lãi đúng; chưa submit không ghi event.
2. Chạy `npm --prefix apps/web run test:e2e -- onboarding.spec.ts`; FAIL vì chưa có flow.
3. Dùng shadcn forms/table/dialog và Lucide; validation financial cuối cùng ở backend. Onboarding từng bước lưu draft khác confirmed; breakdown vốn phải được duyệt. Form cổ tức phân biệt entitlement/receipt, phí/thuế thực; errors cạnh field và summary focus. Không nhập key thật vào fixture/screenshots.
4. PASS browser với dữ liệu synthetic; kiểm tra bàn phím, focus, 375/768/1440px và dữ liệu quá dài. Không test màu/CSS snapshot từng component.
5. Commit: `feat: add personal setup and transaction workflows`.

## Task 25: Tổng quan A+B, nghiên cứu và phê duyệt

**Files — create:** `apps/web/src/app/(private)/page.tsx`, `(private)/research/page.tsx`, `(private)/research/[entityId]/page.tsx`, `components/decision-summary.tsx`, `components/holdings-table.tsx`, `components/source-evidence.tsx`, `components/universe-review.tsx`, `components/valuation-review.tsx`, `tests/e2e/research.spec.ts`.

1. Viết e2e mở lý do từ khuyến nghị, trace source, duyệt danh sách/assumptions tạo version, từ chối không đổi active; holdings ngoài universe vẫn thấy; missing data không có nút mua giả.
2. Chạy `npm --prefix apps/web run test:e2e -- research.spec.ts`; FAIL.
3. Áp dụng bố cục approved mock: kết luận trước, bảng ngay dưới; hiển thị quality/date/risk/invalidation. Trang vĩ mô/ngành là phần research có coverage và nguồn; doanh nghiệp có ba scenario/mô hình/giả định. Biểu đồ lấy backend series, nộp/rút có markers, chưa tính return thì không gắn nhãn performance.
4. PASS; dùng lời “chưa đủ cơ sở/giữ nguyên” khi tương ứng. Bảng số tiền có đơn vị rõ, tỷ trọng nói mẫu số; không chỉ đỏ/xanh để phân biệt lãi/lỗ.
5. Commit: `feat: present decisions holdings and evidence-led research`.

## Task 26: Job pipeline và bản tin C

**Files — create:** `backend/src/investment_agent/jobs/runner.py`, `jobs/daily.py`, `jobs/publication.py`, `api/routes/jobs.py`, `api/routes/reports.py`, `apps/web/src/app/(private)/reports/page.tsx`, `(private)/reports/[reportId]/page.tsx`, `backend/tests/jobs/test_publication.py`.

1. Test cùng run key không tạo bản tin trùng, snapshot đổi trong lúc job chạy không publish bằng version sai; lỗi LLM vẫn có report số liệu kiểm chứng; dữ liệu chưa đủ ⇒ incomplete.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/jobs/test_publication.py -q`; FAIL.
3. Run key `(owner, session_date, report_kind, input_snapshot, report_version)`; lease/lock cục bộ, từng stage checkpoint. API trả 202/job ID, UI polling bounded/cancel observation, không hứa hủy computation khi đóng tab. Report persist hoàn chỉnh trước queue notification, schema chặt cùng verification flags.
4. PASS; giao diện C đọc thoáng, ngày phiên khác ngày chạy, so sánh bản trước cùng phạm vi dữ liệu. Bản tin có portfolio values nhưng không xuất full income/debt/emergency detail. Show build/incomplete/failed/published riêng.
5. Commit: `feat: publish reproducible after-close investment reports`.

## Task 27: Telegram có xác nhận đích và trạng thái gửi

**Files — create:** `backend/src/investment_agent/notifications/telegram.py`, `notifications/outbox.py`, `notifications/render.py`, `api/routes/notifications.py`, `backend/tests/notifications/test_delivery.py`.

1. Test disabled chưa gửi; render chứa portfolio+market+opportunity+risk; chia tin không mất phần; 429 retry có hạn; timeout chuyển unknown không tự gửi lặp; lỗi phần 2 không gửi lại phần 1.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/notifications/test_delivery.py -q`; FAIL.
3. Owner nhập Bot Token phía server, Group ID và xác nhận quyền thành viên nhóm xem dữ liệu cá nhân; preview trước gửi thử thật. Lưu outbox/report/destination/part/version; ghi Telegram message ID nếu có. Không giả claim exactly-once. Nội dung dùng escape phù hợp parse mode hoặc plain text, tách theo giới hạn sau render.
4. PASS bằng fake HTTP; live send chỉ khi owner chủ động chọn “Gửi thử” tới đích rõ; scheduled real bật riêng sau xác nhận. UI xử lý unknown cho người dùng kiểm tra trước retry; key không vào logs/Firestore client.
5. Commit: `feat: deliver confirmed portfolio briefs to telegram`.

## Task 28: Cài đặt và lịch Windows có chạy bù

**Files — create:** `scripts/windows/start-app.ps1`, `scripts/windows/run-after-close.ps1`, `scripts/windows/register-tasks.ps1`, `backend/src/investment_agent/jobs/schedule.py`, `apps/web/src/app/(private)/settings/page.tsx`, `backend/tests/jobs/test_schedule.py`, `docs/operations/windows.md`.

1. Test giờ Việt Nam, ngày nghỉ, cuối tuần/tháng theo lịch thị trường, phiên thiếu và source update muộn, machine resume bỏ lỡ lịch và lock chống hai worker.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/jobs/test_schedule.py -q`; FAIL.
3. Cấu hình 17:30/18:30/20:00 theo timezone đã duyệt, điều kiện retry dựa trạng thái dữ liệu chứ không gửi ba bản tin giống nhau. Catch-up ưu tiên phiên chưa hoàn tất gần nhất, historical backfill không gửi hàng loạt bản tin cũ; cảnh báo số phiên bỏ lỡ. Weekly/monthly dùng session cuối tương ứng; chưa tới lịch không tự tạo báo cáo.
4. PASS. Script absolute paths đã kiểm tra workspace, không dùng `$HOME` làm biến task; background helper ẩn cửa sổ. Scheduler không đưa token vào command args; bootstrap cần xác nhận owner/project/secrets. Đăng ký task thật chỉ khi cấu hình sẵn và user đã chọn bật, không sửa lịch hệ thống không liên quan. Máy tắt thì UI nêu không có bảo đảm đúng giờ.
5. Commit: `feat: run scheduled and catch-up analysis on windows`.

## Task 29: Sao lưu, khôi phục và log an toàn

**Files — create:** `backend/src/investment_agent/operations/backup.py`, `operations/restore.py`, `operations/logging.py`, `backend/tests/operations/test_recovery.py`, `docs/operations/backup-and-recovery.md`.

1. Test backup đang có SQLite WAL vẫn consistent; không chứa key/log nhạy cảm; checksum sai không restore; khôi phục vào thư mục tạm cho ledger/report giống snapshot; retention không xóa ngoài backup root.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests/operations/test_recovery.py -q`; FAIL.
3. SQLite backup API, snapshot manifest và Parquet/tài liệu đúng version; export personal từ Firestore có owner/schema/export version, lưu cục bộ theo lựa chọn user. Không chỉ copy cache rồi gọi là backup đầy đủ. Giữ 7 daily/4 weekly, mọi thao tác move/delete dùng resolved absolute path trong backup root. Không tự upload đi nơi khác.
4. PASS và restore drill vào môi trường riêng; restore Firestore thật phải có preview số bản ghi và xử lý version, không ghi đè dữ liệu mới im lặng. Nhật ký job có phase/time/count/error code, không prompt cá nhân/token.
5. Commit: `feat: back up and recover personal investment state`.

## Task 30: Kiểm chứng xuyên hệ thống và dữ liệu thật

**Files — create:** `tests/e2e/after-close.spec.ts`, `backend/tests/integration/test_end_to_end.py`, `docs/verification/acceptance-matrix.md`, `docs/verification/live-data-checklist.md`, `scripts/windows/verify.ps1`.

1. Viết test deterministic: onboarding → đủ 13 câu → confirmed capital → giao dịch/cổ tức → approved universe/assumptions fixture → after-close job → report → fake Telegram; cùng snapshot retry không nhân bản. Chạy để xác nhận lỗi phát hiện ở tầng nào.
2. Chạy `.\.venv\Scripts\python.exe -m pytest backend/tests -q`, `npm --prefix apps/web run typecheck`, `npm --prefix apps/web run lint`, `npm --prefix apps/web run test -- --run`, `npm --prefix apps/web run build`, `npm --prefix apps/web run test:e2e`; sửa lỗi thật, không nới assert để cho qua.
3. Inject failure: Firebase offline, nguồn tài chính sửa, ngày nghỉ, thiếu giá, hết credit, AI sai schema, provider không ZDR, Telegram timeout, máy resume, profile đổi giữa job. Verify output/status đúng, không phát hành khuyến nghị sai hoặc gửi trùng vô điều kiện.
4. Chạy live validation riêng khi có cấu hình: kiểm tra từng mã 50/10 năm, đối chiếu báo cáo gốc và ratios qua sự kiện vốn; thử một job phiên thật. Mô hình và Telegram live có thao tác bật/gửi thử rõ. Ghi `passed/failed/not_run` với bằng chứng, không chuyển test giả lập thành bằng chứng chất lượng đầu tư thật.
5. Commit: `test: verify investment workflow and failure recovery`.

## Task 31: Bàn giao bản thử nghiệm và giới hạn được kiểm chứng

**Files — create:** `docs/operations/personal-trial-guide.md`, `docs/verification/trial-release.md`; **modify:** `README.md`.

1. Lập ma trận 15 nhóm nghiệm thu trong thiết kế đối chiếu test/live result; ghi rõ phần chưa chạy vì thiếu key/nguồn và phần không đạt dữ liệu. Không gọi hoàn tất bản phân tích thật nếu gate chưa qua.
2. Hướng dẫn bắt đầu từ máy sạch: runtime, `.env`, Firebase allowlist, nguồn dữ liệu, owner budget/model privacy, import opening balances, duyệt universe/assumptions và bật lịch/Telegram; không cần copy secrets vào chat.
3. Demo cho người dùng: A+B tổng quan, nguồn chứng cứ, sửa giao dịch, C bản tin, dữ liệu cũ và fallback; minh họa 90% chỉ khi đủ điều kiện, không tự bật ngoại lệ thật.
4. Ghi chi phí quan sát, thời gian tác vụ, độ phủ thật, cách dừng scheduler/AI/Telegram, sao lưu và khôi phục. Chỉ lưu bằng chứng đã che thông tin cá nhân trong Git.
5. Commit: `docs: hand over verified personal investment trial`.

## 3. Điểm kiểm tra bổ sung trước nghiệm thu

| Rủi ro | Kiểm tra bắt buộc |
|---|---|
| Sai mẫu số phân bổ | Breakdown từng khoản bảo vệ, không trừ/đếm lại nguồn bù hoặc tài sản trong ledger |
| Điểm rủi ro che thiếu khả năng tài chính | Capacity flags độc lập, chặn tăng vốn khi không đủ |
| Định giá dùng tương lai | As-of ngày công bố/revision/share basis; latest-restated không masquerade as-reported |
| Cổ tức tạo lãi hai lần | Raw price + entitlement/receivable accounting, payment chỉ chuyển trạng thái |
| Giao dịch tạo tiền khả dụng giả | Settlement và tradable quantity riêng, không dùng toàn bộ tài sản kế toán làm buying power |
| Firestore/local mất đồng bộ | Snapshot phiên bản, transaction/idempotency, không offline mutation thứ hai |
| AI tiết lộ số tiền cá nhân | Payload allowlist và kiểm tra toàn request, tools, logs, error paths |
| Mô hình thay đổi behavior | Catalog capability, policy routing và đánh giá output; schema không đủ nếu số sai |
| Telegram timeout | unknown + đối chiếu, không tự hứa exactly-once |
| Vượt phạm vi danh sách | Universe approval riêng với ownership; 49 mã không tính là đã đủ 50 |
| Kiểm thử tài chính sai oracle | Ví dụ kiểm tay và reconciliation độc lập, không sao chép logic tính vào expected |

## 4. Tài liệu chính thức cần đối chiếu khi thực hiện

- [Next.js App Router](https://nextjs.org/docs/app/getting-started) và [self-hosting](https://nextjs.org/docs/app/guides/self-hosting): Node version, build/start và cache behavior.
- [Firebase session cookies](https://firebase.google.com/docs/auth/admin/manage-cookies): CSRF, session verification và không dùng session cookie thay token gọi Firebase client.
- [Firestore pricing](https://firebase.google.com/docs/firestore/pricing): tính reads/writes, index và hạn mức theo cấu hình thực.
- [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/): dependency settings và override trong tests.
- [OpenRouter model catalog](https://openrouter.ai/docs/api/api-reference/models/get-models) và [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection): endpoint capability, required parameters, privacy/ZDR và fallback.
- [Telegram Bot API](https://core.telegram.org/bots/api): sendMessage, giới hạn render, lỗi/retry.
- Nguồn dữ liệu/luật giao dịch dùng link chính thức và ngày hiệu lực trong `docs/data`/`docs/decisions/market-rules.md`; không dùng mức thuế/phí/T+ nhớ từ hội thoại làm quy định hiện hành.

## 5. Tiêu chí hoàn thành kế hoạch và bước thực hiện

Kế hoạch chỉ hoàn tất khi các task áp dụng đã có kết quả và gate thật được kiểm chứng, hoặc ghi rõ phần chưa thể chạy và quyết định tiếp theo cần thiết. Không coi gần hết thời gian/ngân sách, có UI đẹp hoặc test synthetic PASS là hoàn thành sản phẩm.

Thực hiện theo task, kiểm tra kết quả trước task phụ thuộc. Bắt đầu Task 1–5 để biết nền tảng và dữ liệu có đáp ứng; không mua dịch vụ hoặc gửi dữ liệu thật chỉ vì đang chạy kế hoạch. Sau mỗi mốc A–F có ghi ngắn kết quả, giới hạn và thay đổi cần thiết.

Lựa chọn thực hiện có thể là làm tuần tự ngay trong phiên này, hoặc giao task cho agent theo quy trình người dùng chọn. Nếu dùng executing-plans/subagent-driven-development, phải tìm và đọc skill tương ứng trước; thiếu skill thì nêu rõ và dùng quy trình người dùng cho phép, không giả vờ đã áp dụng.
