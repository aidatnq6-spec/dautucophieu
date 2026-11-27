# Trung vị ngành cho công ty chứng khoán — Implementation Plan

**Goal:** Công ty chứng khoán có trung vị của các công ty chứng khoán HOSE khác (ICB cấp 4 "Dịch vụ đầu tư") trên Bảng số tài chính và qua `so_sanh_nganh`.

**Spec:** [docs/superpowers/specs/2026-11-27-trung-vi-nganh-chung-khoan-design.md](../superpowers/specs/2026-11-27-trung-vi-nganh-chung-khoan-design.md)

## Global Constraints
- Nhóm so sánh: `icb4_codes[mã] == "8777"`; mã không thuộc 8777 trả `thieu`.
- 5 mã chỉ số = `DISPLAY["securities"]`, đúng thứ tự. Tối thiểu 3 mã; dưới đó ô "—", cột vẫn hiện.
- Không đổi kind_of hay các phần khác đọc `data/financial-ratios/`.

## Review Focus
- `hose-listing.json` cũ chưa có `icb4_codes`: sync không thêm mã nào, so sánh trả `thieu` có lý do, bản lưu được làm mới — Task 1, 2.
- Mã đang theo dõi là EVF (kind securities, cấp 4 khác): không có cột trung vị, không lỗi — Task 2.
- Bảo hiểm vẫn không có cột — Task 3.

### Task 1: Danh sách HOSE có ICB cấp 4; sync tải mọi mã 8777
- Files: `market/providers/vndirect_data.py` (`hose_listing`, `INDUSTRY4_URL`), `cli.py` (`cached_listing` đòi `icb4_codes`; `financial_ratios_sync`), tests `tests/market/test_vndirect_data.py`, `tests/market/test_financial_ratios.py`.
- Produces: `listing["icb4_codes"]: dict[str, str]`.
- Tests: `hose_listing` trả `icb4_codes == {"SSI": "8777", "EVF": "8773"}` cho fake level-4 rows; sync với listing có `icb4_codes` thêm SSI, VND (kind securities) mà không thêm EVF.
- Commit: `feat: ICB cấp 4 in the HOSE listing, and financial-ratios-sync fetches every HOSE investment-services firm`

### Task 2: `compare_sector` cho công ty chứng khoán
- Files: `market/sector_compare.py`, `mcp_server.py` (mô tả), test `tests/test_public_tools.py`.
- Consumes: `icb4_codes`. Produces: `compare_sector` with kind securities → codes `SECURITIES_CODES`, folder `financial-ratios`, `nganh` "Dịch vụ đầu tư (chứng khoán)", `ma_nganh` "8777", peers = other 8777 symbols.
- Tests: SSA vs SSB/SSC/SSD (8777, ROAE) and SSE (8777, older quarter) → median, rank, `chua_co_quy_nay == 1`; EVF-like (8773) → `thieu`; listing without `icb4_codes` → `thieu` "Chưa có ngành ICB cấp 4".
- Commit: `feat: So sánh ngành for securities firms: so_sanh_nganh sets one against the other HOSE investment-services firms`

### Task 3: Route, trang, tài liệu
- Files: `api/routes/fairvalue.py` (sector for securities), `apps/web/src/components/financial-tables.tsx` (`showsSector` adds securities), tests `tests/api/test_fairvalue_route.py`, `financial-tables.test.ts`; skill `/dautu-ma`, `docs/claude-project-instructions.md`, plugin 0.20.0.
- Tests: route gives `sector` for a securities firm with 3 peers; `showsSector("securities")` true, `"insurance"` false; `sectorNote` for securities names "Dịch vụ đầu tư (chứng khoán)" and has no CASA text.
- Commit: `feat: Trung vị ngành for securities firms on Bảng số tài chính, told to Claude (plugin 0.20.0)`

### Task 4: verify.ps1, live check (counts only), final review, merge, update-app, plugin update.
