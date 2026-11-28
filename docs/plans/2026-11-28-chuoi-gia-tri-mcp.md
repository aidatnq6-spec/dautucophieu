# Chuỗi giá trị cho Claude (MCP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public-data MCP tool `chuoi_gia_tri(ma)` that gives every value chain of the ticker's ICB level-2 sector: stages with sources, each macro factor's reading, the weighted shares, the label (approved only), the chain's average returns by period and its median P/E, P/B against five years. It never names a member.

**Architecture:** A new module `services/value_chain_public.py` turns `scored_chains` (api/routes/value_chains.py, called with `held=set()`), `chain_board` and `chain_valuation_board` into Vietnamese public output. It removes every symbol and keeps counts only. `PublicData.chuoi_gia_tri` calls it, and `mcp_server` registers it. The Project instructions, the `/dautu-ma` skill and the plugin version follow.

**Tech Stack:** Python 3.11, pytest, FastMCP (existing `mcp_server`).

**Spec:** `docs/superpowers/specs/2026-11-28-chuoi-gia-tri-mcp-design.md` (owner-approved 28/11/2026)

## Global Constraints

- Chains are chosen by the ticker's ICB level-2 name (`hose-listing.json` `icb_codes` → `icb_names`) equal to the chain's `icb`, in file order. Never by `symbols`.
- No symbol in the output: no member list, no `leader`, no `no_data`/`stale` symbol lists. Counts only.
- No personal data: `held` is always `set()`. No watchlist, no Firestore. `data/value-chain-approvals.json` may be read.
- A label only when approved (`scored_chains` already gives `label=None` for drafts). A draft carries the note "chuỗi chưa được chủ sở hữu duyệt; không có nhận định tổng".
- Missing values are `null` with a reason, never estimated. Numbers stay strings as the stores give them.
- Plugin version 0.28.0.

## Review Focus

- A ticker whose sector has no chain (Y tế): `thieu: true`, "chưa có chuỗi giá trị cho ngành Y tế", `nganh: "Y tế"`. Tested in Task 1.
- A ticker of a sector with two chains (Tài nguyên Cơ bản: Thép, Tôn mạ): both chains are returned, in file order, and two tickers of the sector get identical output. Tested in Task 1.
- A chain whose members have no stored closes or valuations: `hieu_suat` periods `thay_doi: null`, `so_ma: 0`; `dinh_gia` `pe.hien_tai: null`. No error. Tested in Task 1.
- A lowercase or padded ticker (`" hpg "`) works like `HPG`; `"!!"` gives `thieu`. Tested in Task 1.
- An app approval of older content is not approved (`da_duyet: false`, `nhan: null`). This comes from `scored_chains`; tested in Task 1.

---

### Task 1: `chuoi_gia_tri` in PublicData

**Files:**
- Create: `backend/src/investment_agent/services/value_chain_public.py`
- Modify: `backend/src/investment_agent/public_tools.py` (method after `so_sanh_nganh`)
- Test: `backend/tests/test_value_chain_public.py`

**Interfaces:**
- Produces: `chains_for_sector(data_dir: Path, symbol: str, *, today: date, config_path: Path = VALUE_CHAINS_PATH) -> dict`
- Produces: `PublicData.chuoi_gia_tri(self, ma, *, today: date | None = None, config_path: Path | None = None) -> dict`. `today` defaults to the date in Asia/Ho_Chi_Minh.

Output (Vietnamese keys, mapped from the English values):
- Top level: `{"ma", "nganh", "ngay", "chuoi": [...], "nguon", "luu_y"}`.
- `nhan`: tailwind→`thuan_loi`, neutral→`trung_tinh`, headwind→`bat_loi`, insufficient→`chua_du_du_lieu`, None→`null`.
- Chain: `{"id", "ten", "da_duyet": bool, "duyet_ngay", "nhan", "ghi_chu_duyet" (draft note or null), "ty_trong": {"tot","xau","trung_tinh","chua_danh_gia"}, "cac_khau": {"dau_vao","trung_gian","dau_ra"}, "yeu_to": [...], "hieu_suat", "dinh_gia", "so_ma"}`.
- Stage item: `{"ten", "ghi_chu", "ty_trong", "nguon": [{"tieu_de","don_vi","ngay","trang","url"}]}`.
- Factor: `{"ten", "khau", "chi_bao", "chieu": "tang"|"giam"|"di_ngang"|null, "tac_dong": "tot"|"xau"|"trung_tinh"|"chua_danh_gia"|"su_kien", "trong_so": "chinh"|"phu"|"nho", "so_moi_nhat": {"ngay","gia_tri"}|null, "thay_doi", "ly_do", "thieu": str|null, "nguon"}`.
- Missing reasons (`thieu`): no_series→"ứng dụng chưa có chuỗi số cho chỉ báo này", no_data→"chưa có số trong kho", stale→"số mới nhất quá {n} ngày", one_point→"mới có một điểm số, chưa có chiều".
- `hieu_suat`: `{"so_ma_co_gia", "ky": {"tuan","thang","quy","nam","tu_dau_nam": {"thay_doi","so_ma"}}, "phien_gan_nhat": {"tang","giam","dung"}, "vi_tri_52_tuan"}`.
- `dinh_gia`: `{"so_ma_co_dinh_gia", "pe": {"hien_tai","trung_vi_5_nam","vi_tri","so_ma","so_tuan"}, "pb": {...}, "tu_ngay"}`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_value_chain_public.py`. Fixture: a tmp data dir with `hose-listing.json` (HPG, HSG → "1700" Tài nguyên Cơ bản; DHG → "4500" Y tế), a `value-chains.json` with chains `steel` (icb Tài nguyên Cơ bản, symbols ["HPG"], approved in config, one factor on `wti`) and `coated` (same icb, symbols ["HSG"], draft), and `MacroStore` `wti` points +10% over 35 days (the route test's pattern, `TODAY = date(2027, 1, 15)`).
  - `test_a_ticker_gets_every_chain_of_its_sector_and_never_a_member_name`: `out = chains_for_sector(root, "HPG", today=TODAY, config_path=path)`; `[c["id"] for c in out["chuoi"]] == ["steel", "coated"]`; `out["nganh"] == "Tài nguyên Cơ bản"`; `"HPG" not in json.dumps(out["chuoi"])` and `"HSG" not in json.dumps(out)`; `chains_for_sector(root, "HSG", ...)["chuoi"] == out["chuoi"]`.
  - `test_a_draft_has_factor_readings_but_no_label`: coated `da_duyet is False`, `nhan is None`, `ghi_chu_duyet` contains "chưa được chủ sở hữu duyệt"; steel `da_duyet is True`; its wti factor `chieu == "tang"`, `tac_dong == "xau"` (when_up bad), `so_moi_nhat["gia_tri"] == "66"`, `thieu is None`.
  - `test_a_factor_without_a_series_says_why`: a factor with `indicator: None` gives `tac_dong == "chua_danh_gia"` and `thieu == "ứng dụng chưa có chuỗi số cho chỉ báo này"`.
  - `test_members_without_prices_give_empty_returns_and_valuation`: no closes stored: `hieu_suat["so_ma_co_gia"] == 0`, `hieu_suat["ky"]["thang"] == {"thay_doi": None, "so_ma": 0}`, `dinh_gia["pe"]["hien_tai"] is None`, `so_ma == 1`.
  - `test_a_sector_without_a_chain_says_so`: `chains_for_sector(root, "DHG", ...) == {"thieu": True, "ly_do": "Chưa có chuỗi giá trị cho ngành Y tế.", "ma": "DHG", "nganh": "Y tế"}`.
  - `test_a_ticker_without_a_sector_or_invalid_is_missing`: "ZZZ" → `thieu` with "Chưa có ngành ICB của ZZZ"; `PublicData(root).chuoi_gia_tri("!!", today=TODAY, config_path=path)["thieu"] is True`; `PublicData(root).chuoi_gia_tri(" hpg ", today=TODAY, config_path=path)["ma"] == "HPG"`.
  - `test_an_app_approval_of_older_content_is_not_approved`: `approvals.approve(root, "coated", fingerprint="old", note=None, on=TODAY)` → coated still `da_duyet is False`, `nhan is None`.

- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest backend/tests/test_value_chain_public.py -q -p no:warnings`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement `chains_for_sector`.** Filter `scored_chains(data_dir, load_value_chains(config_path), today=today, held=set())` by `icb`. Call `chain_board` and `chain_valuation_board` with only those chains (`{"id","name","symbols"}` from the config). Map the fields as listed above, and resolve each `refs` entry through `config.sources`. `luu_y`: "Chuỗi theo ngành ICB cấp 2 của mã, không cho biết mã có thuộc danh sách của chuỗi hay không: tự xét chuỗi nào sát với hoạt động của mã và nói rõ khi chưa chắc. Nhận định là phép tính trên chiều 1 tháng của chỉ báo theo trọng số đã đặt, không phải dự báo. Hiệu suất là bình quân các mã của chuỗi, không theo vốn hóa; P/E, P/B là trung vị." `nguon`: "config/value-chains.json; chuỗi vĩ mô, giá đóng cửa và định giá trong kho". Add `PublicData.chuoi_gia_tri`, which validates with `self._symbol` and defaults `config_path` to `VALUE_CHAINS_PATH`.

- [ ] **Step 4: Run** the same command. Expected: 7 passed. Then run all backend tests: `.venv/Scripts/python.exe -m pytest backend/tests -q -p no:warnings`. Expected: all pass.

- [ ] **Step 5: Commit** `feat: Chuỗi giá trị for Claude: chuoi_gia_tri gives every chain of the ticker's ICB sector with its factor readings, average returns and median valuation against five years, never a member's name`.

### Task 2: Register the tool, instructions, skill, plugin 0.28.0

**Files:**
- Modify: `backend/src/investment_agent/mcp_server.py` (a `@tool def chuoi_gia_tri(ma: str) -> dict` after `so_sanh_nganh`, returning `vn_times(data.chuoi_gia_tri(ma))`)
- Modify: `docs/claude-project-instructions.md` (add `chuoi_gia_tri` to the "Gọi đủ" list of a ticker analysis, and one usage line)
- Modify: `plugins/dautucophieu/skills/dautu-ma/SKILL.md` (a call step and a section "Ngành và vĩ mô")
- Modify: `plugins/dautucophieu/.claude-plugin/plugin.json` (0.28.0)
- Test: `backend/tests/test_plugin_dautu.py` (existing; these tests enforce that the instructions and skills name exactly the server's tools)

- [ ] **Step 1:** Add the `mcp_server` tool. Docstring: "Chuỗi giá trị của ngành ICB cấp 2 mà mã thuộc về (mọi chuỗi của ngành, không cho biết mã có trong chuỗi hay không): các khâu đầu vào – trung gian – đầu ra kèm nguồn, từng yếu tố vĩ mô (chiều 1 tháng, tốt hay xấu cho ngành, trọng số), tỷ trọng tốt/xấu, nhận định tổng chỉ khi chuỗi đã duyệt, hiệu suất bình quân theo kỳ và P/E, P/B trung vị so với 5 năm."
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest backend/tests/test_plugin_dautu.py -q -p no:warnings`. Expected: FAIL. The instructions do not name `chuoi_gia_tri` yet.
- [ ] **Step 3:** Update the Project instructions. Usage line: "- Ngành có đang hưởng lợi, vĩ mô có ủng hộ không: chuoi_gia_tri; nêu chuỗi nào sát với mã, chuỗi đã duyệt hay chưa (chưa duyệt thì không nói nhận định tổng), các yếu tố tốt và xấu chính kèm ngày số, hiệu suất và định giá so với 5 năm; ngành chưa có chuỗi thì nói là thiếu". Skill `/dautu-ma`: in its call list add "`chuoi_gia_tri`: chuỗi giá trị của ngành", and in its output sections add "**Ngành và vĩ mô** (`chuoi_gia_tri`)" with the same rules. Bump the plugin to 0.28.0.
- [ ] **Step 4: Run** the plugin tests, then all backend tests. Expected: all pass.
- [ ] **Step 5: Commit** `feat: chuoi_gia_tri on the public-data MCP, in the Project instructions and /dautu-ma's Ngành và vĩ mô (plugin 0.28.0)`.

### Finish

- [ ] Run `verify.ps1`. All checks must PASS. Then merge into `main`, push, run `update-app.ps1`, and run `claude plugin marketplace update dautucophieu` followed by `claude plugin update dautucophieu@dautucophieu`.
- [ ] Preview on live public data. Call `chuoi_gia_tri` for one ticker of a sector with two chains and for one ticker of Y tế, and check that no ticker appears in the chain output.
