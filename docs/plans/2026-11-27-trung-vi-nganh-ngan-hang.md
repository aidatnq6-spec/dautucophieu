# Trung vị ngành cho ngân hàng — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** So sánh một ngân hàng với các ngân hàng HOSE khác trên 9 chỉ số VNDirect, trên Bảng số tài chính và qua `so_sanh_nganh`.

**Architecture:** `financial-ratios-sync` tải thêm mọi ngân hàng HOSE vào `data/financial-ratios/`; `market/sector_compare.compare_sector` nhận ngân hàng và đọc kho đó; route `/fairvalue/ratios/{mã}` và trang dùng lại cột "Trung vị ngành" sẵn có của doanh nghiệp thường.

**Tech Stack:** Python 3.11 (FastAPI, pytest), Next.js/TypeScript (vitest).

**Spec:** [docs/superpowers/specs/2026-11-27-trung-vi-nganh-ngan-hang-design.md](../superpowers/specs/2026-11-27-trung-vi-nganh-ngan-hang-design.md)

## Global Constraints

- Chỉ ngân hàng: sector ICB cấp 2 tên "Ngân hàng" (`financial_ratios.kind_of(...) == "bank"`). Chứng khoán và bảo hiểm vẫn trả `thieu`.
- 9 mã chỉ số = mã các dòng `financial_ratios.DISPLAY["bank"]`, đúng thứ tự đó. Không tính trung vị cho `GROUP2_RATIO`, `CASA` (dòng nhập tay / Vietcap): giá trị `None`.
- Chỉ so với ngân hàng có số ở đúng quý mới nhất của mã đang xem; không gồm mã đó; `MIN_PEERS = 3` như cũ.
- Không đổi điểm sức khỏe, cảnh báo quý mới, `holdings_view`, `early_lights`.
- Không đoán số; không nhãn tốt/xấu. Không in danh mục khi chạy thử.
- Commit một dòng tiếng Anh; chạy toàn bộ test backend trước mỗi commit.

## Review Focus

- Ngân hàng chưa có quý mới nhất (chưa công bố Q3): đếm vào `chua_co_quy_nay`, không dùng quý cũ — test ở Task 2.
- Mã đang theo dõi là chứng khoán/bảo hiểm: vẫn được tải như cũ khi thêm ngân hàng — test ở Task 1.
- `hose-listing.json` chưa có: sync vẫn chạy cho mã theo dõi, không lỗi — test ở Task 1.
- Ngân hàng không có tệp chỉ số: route trả như cũ, `sector` là `None` khi dưới 3 ngân hàng có số — test ở Task 3.
- Trang của chứng khoán/bảo hiểm: không hiện cột trung vị — test ở Task 4.

---

### Task 1: Tải chỉ số cho mọi ngân hàng HOSE

**Files:**
- Modify: `backend/src/investment_agent/cli.py` (`financial_ratios_sync`, ~dòng 762)
- Test: `backend/tests/market/test_financial_ratios.py`

**Interfaces:**
- Produces: `data/financial-ratios/<MÃ>.json` cho mọi mã HOSE có `icb_names[icb_codes[mã]] == "Ngân hàng"`, cùng định dạng hiện nay (`kind: "bank"`).

- [ ] **Step 1: Write the failing tests**

```python
def test_cli_financial_ratios_sync_adds_every_hose_bank_to_the_watched_financials(tmp_path, capsys):
    # watched: SSI (securities), FPT (general); listing: banks VCB, ACB, and FPT
    # get serves _page(symbol, [("2026-09-30", "ROAA_TR_AVG4Q", 0.01)]) for the symbol in the URL
    assert financial_ratios_sync(tmp_path, get=..., today=date(2026, 11, 27)) == 0
    assert json.loads(capsys.readouterr().out)["results"] == {"ACB": "ok", "SSI": "ok", "VCB": "ok"}
    assert FinancialRatioStore(tmp_path / "financial-ratios").read("VCB")["kind"] == "bank"

def test_cli_financial_ratios_sync_without_a_listing_keeps_to_the_watched(tmp_path, capsys):
    # no hose-listing.json: results == {"SSI": "ok"}, exit 0
```

- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest backend/tests/market/test_financial_ratios.py -q -p no:warnings` — expect the first test FAIL (no ACB/VCB).
- [ ] **Step 3: Implement** in `financial_ratios_sync`: after `watched`, read `hose-listing.json` (missing or unreadable → `{}`), and for each listed symbol whose sector name is "Ngân hàng" add `{symbol: "Ngân hàng"}` (a watched entry wins). Pass the merged dict to `fetch_financial_ratios` unchanged.
- [ ] **Step 4: Run** the same command — PASS; then the full backend suite.
- [ ] **Step 5: Commit** `feat: Chỉ số ngân hàng for every HOSE bank: financial-ratios-sync adds the listing's banks to the watched financial tickers`

### Task 2: `compare_sector` cho ngân hàng

**Files:**
- Modify: `backend/src/investment_agent/market/sector_compare.py`
- Modify: `backend/src/investment_agent/mcp_server.py:73-77` (mô tả `so_sanh_nganh`)
- Test: `backend/tests/test_public_tools.py`

**Interfaces:**
- Consumes: Task 1's store.
- Produces: `compare_sector(data_dir, symbol, codes=None) -> dict`. `codes=None` means: `BANK_CODES` for a bank, `SECTOR_CODES` otherwise. `BANK_CODES = tuple(code for code, _, _ in DISPLAY["bank"])`. Same output keys as today; `ten` from the DISPLAY label for a bank; `nguon`/`lay_luc` from the bank's record.

- [ ] **Step 1: Write the failing test** `test_a_bank_set_against_the_other_hose_banks_on_the_same_quarter`: listing with BNK, BA, BB, BC (8300 "Ngân hàng"), BD (8300, only Q2) and SEC (8700 "Dịch vụ tài chính"); `financial-ratios/<sym>.json` with `kind: "bank"`, NPL `BAD_LOANS_RATIO_AQ` values BNK "0.02", BA "0.01", BB "0.03", BC "0.05" on "2026-09-30", BD on "2026-06-30".

```python
out = data.so_sanh_nganh("bnk")
assert out["nganh"] == "Ngân hàng" and out["quy"] == "2026-09-30" and out["so_doanh_nghiep_nganh"] == 4 and out["chua_co_quy_nay"] == 1
npl = next(c for c in out["chi_so"] if c["ma_chi_so"] == "BAD_LOANS_RATIO_AQ")
assert npl == {"ma_chi_so": "BAD_LOANS_RATIO_AQ", "ten": "Tỷ lệ nợ xấu (NPL)", "gia_tri": "0.02", "trung_vi": "0.03",
               "phan_vi_25": "0.02", "phan_vi_75": "0.04", "so_doanh_nghiep": 3, "thu_hang": "3/4 (cao xuống thấp)"}
assert [c["ma_chi_so"] for c in out["chi_so"]] == [code for code, _, _ in DISPLAY["bank"]]
assert data.so_sanh_nganh("SEC")["thieu"] is True
```
  Also change the existing test's last-but-one assert: BNK (no ratio file there) now gives `thieu` with "Chưa có chỉ số" in `ly_do`.
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest backend/tests/test_public_tools.py -q -p no:warnings` — FAIL.
- [ ] **Step 3: Implement**: in `compare_sector`, `kind = kind_of(sector)`; securities/insurance → existing `thieu` text reworded to "…; so sánh ngành có cho doanh nghiệp thường và ngân hàng."; bank → store dir `financial-ratios`, codes `BANK_CODES`, names from DISPLAY; general unchanged. Update the tool docstring: "… 16 chỉ số VNDirect …; ngân hàng: 9 chỉ số (NPL, nợ quá hạn, bao phủ nợ xấu, NIM, LDR, tăng trưởng cho vay, vốn chủ/tài sản, ROAA, ROAE); không cho bảo hiểm, chứng khoán."
- [ ] **Step 4: Run** — PASS; full backend suite.
- [ ] **Step 5: Commit** `feat: So sánh ngành for banks: so_sanh_nganh sets a bank against the other HOSE banks on VNDirect's nine bank ratios`

### Task 3: Route trả trung vị cho ngân hàng

**Files:**
- Modify: `backend/src/investment_agent/api/routes/fairvalue.py` (`_sector_medians` ~190, bank branch ~465-476)
- Test: `backend/tests/api/test_fairvalue_route.py`

**Interfaces:**
- Consumes: Task 2's `compare_sector(data_dir, symbol)`.
- Produces: bank response gains `"sector": {name, quarter, peers, medians, counts} | None`; `medians` has every metric code of the response, `None` for codes `compare_sector` did not give (GROUP2_RATIO, CASA).

- [ ] **Step 1: Write the failing test** `test_a_banks_ratios_carry_the_median_of_the_other_hose_banks`: as the general test at line 520, with four banks in `FinancialRatioStore(tmp_path / "financial-ratios")`; assert `sector["name"] == "Ngân hàng"`, `peers == 3`, `medians["BAD_LOANS_RATIO_AQ"]` equals the median string, and `set(sector["medians"]) == {m["code"] for m in body["metrics"]}`. A second case: a bank with only one peer → `body["sector"] is None`.
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest backend/tests/api/test_fairvalue_route.py -q -p no:warnings` — FAIL.
- [ ] **Step 3: Implement**: `_sector_medians(data_dir, symbol, codes: list[str])` calls `compare_sector(data_dir, symbol)` (default codes), returns `None` on `thieu` or when no code has a median, and fills `medians`/`counts` for every code in `codes` (`None`/0 when absent). General branch passes its 12 codes; bank branch passes its row codes and adds `"sector"` to the response. Securities/insurance responses add `"sector": None`.
- [ ] **Step 4: Run** — PASS; full backend suite.
- [ ] **Step 5: Commit** `feat: Trung vị ngành on Bảng số tài chính for banks: the bank ratios carry the median of the other HOSE banks for the same quarter`

### Task 4: Cột "Trung vị ngành" trên trang của ngân hàng, tài liệu cho Claude

**Files:**
- Modify: `apps/web/src/components/financial-tables.tsx:251` and `:294` (conditions `ratios?.kind === "general"` → a helper)
- Test: `apps/web/src/components/financial-tables.test.ts`
- Modify: `plugins/dautucophieu/skills/dautu-ma/SKILL.md` (mục 4), `docs/claude-project-instructions.md:51`, `plugins/dautucophieu/.claude-plugin/plugin.json` (0.19.0), spec ngày 26/11 `2026-11-26-trung-vi-nganh-trang-ma-design.md` (một dòng trỏ sang spec mới)

**Interfaces:**
- Produces: `export function showsSector(kind: Ratios["kind"] | undefined): boolean` — true for `"general"` and `"bank"`.

- [ ] **Step 1: Write the failing test** `it("the sector median column shows for general companies and banks only")`: `showsSector("general")`, `showsSector("bank")` true; `"securities"`, `"insurance"`, `undefined` false.
- [ ] **Step 2: Run** (from `apps/web`) `npx.cmd vitest run src/components/financial-tables.test.ts` — FAIL.
- [ ] **Step 3: Implement** `showsSector` and use it at both places; the caption keeps its text ("trung vị của N doanh nghiệp cùng ngành Ngân hàng (ICB cấp 2, HOSE) có số ở quý …"). Docs: skill mục 4 says ngân hàng có 9 chỉ số, chứng khoán/bảo hiểm ghi lý do; project instructions line: "16 chỉ số; ngân hàng 9 chỉ số".
- [ ] **Step 4: Run** the vitest command, `npm.cmd --prefix apps/web run typecheck`, and `.venv/Scripts/python.exe -m pytest backend/tests/test_plugin_dautu.py -q -p no:warnings` — PASS.
- [ ] **Step 5: Commit** `feat: Trung vị ngành column for banks on Bảng số tài chính, and so_sanh_nganh's bank ratios told to Claude (plugin 0.19.0)`

### Task 5: Kiểm tra toàn bộ và triển khai

- [ ] `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\verify.ps1` — every line PASS.
- [ ] Live, public data only: run `financial-ratios-sync`, then `so_sanh_nganh` for one bank; expect `so_doanh_nghiep_nganh` 21 and nine rows with medians.
- [ ] Merge to main, push, `scripts\windows\update-app.ps1`; `claude plugin marketplace update dautucophieu`, `claude plugin update dautucophieu@dautucophieu`; confirm the installed 0.19.0 skill names banks.
