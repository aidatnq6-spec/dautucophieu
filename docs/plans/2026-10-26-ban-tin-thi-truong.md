# Bản tin: phần "Thị trường phiên" Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Spec:** `docs/superpowers/specs/2026-10-26-ban-tin-thi-truong-design.md` (owner-approved 2026-10-26). The spec is the authority.

**Goal:** Put a market section at the top of the after-close brief, covering:
- indices (points and %);
- HOSE trading value;
- breadth;
- foreign flows (totals and top 3+3);
- proprietary trading ("chưa có nguồn miễn phí");
- sectors across all of HOSE;
- watched and held tickers;
- filtered news.

Drop the "Phạm vi" column in the brief, tidy the old sections, and send a short Telegram version.

**Architecture:**
- A new `brief` package builds a **per-session public snapshot** at `data/brief/<YYYY-MM-DD>.json`. It is written by a new CLI step `brief-snapshot` on every scheduler wake-up, and each section fails on its own. Sources:
  - one Vnstock `price_board` call for all HOSE stocks;
  - the stored `VNINDEX-1d` and `VN30-1d` series;
  - HOSE statistics, when published;
  - RSS from CafeF, Vietstock and Vneconomy.
- Personal ordering happens **at render time**, on the machine: held tickers first, and news filtered by watched or held tickers, their sectors and macro keywords.
- The report page reads the snapshot by session date through the reports API. Telegram gets the snapshot passed into `deliver()` / `render_report()`.
- Firestore reports stay write-once and unchanged.

**Tech Stack:** Python 3.11, httpx, Vnstock 5.2 (owner-installed), FastAPI, Next.js, pytest, Playwright.

## Global constraints
- No AI and no personal data leave the machine. The snapshot holds public data only.
- No guessed numbers: a missing source gives `{"status": "missing", "reason": "..."}` for that section only.
- Board rows are used only when `listing.trading_date == session_date`; otherwise the board sections are "chưa có số liệu cho phiên này".
- Units (checked live 2026-10-26):
  - `price_board` prices are in đồng;
  - `match.accumulated_value` is in **million đồng** (matched only, no put-through);
  - `match.foreign_*_value` is in **đồng**;
  - HOSE reports are in million đồng and thousand shares (strings with `,` thousands separators);
  - `VNINDEX-1d`/`VN30-1d` closes are in points.
- Robots: CafeF, Vietstock and Vneconomy allow their RSS. Never fetch VnExpress.
- Vnstock pacing: one `price_board` call per run (it accepts ≤ 500 symbols). The HOSE symbol list and ICB names are cached weekly in `data/hose-listing.json`.
- Process:
  - TDD with each RED watched.
  - Full backend suite before each commit; `verify.ps1` **must pass before the PR is opened**.
  - Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Branch `feat/brief-market` from `origin/main`; carry the spec and plan commits over by cherry-picking `docs/brief-market-design`.

## Snapshot shape (`data/brief/2026-10-26.json`)
```json
{"session_date": "2026-10-26", "updated_at": "...",
 "indices": {"status": "ok", "rows": [{"id": "VNINDEX", "close": "1650.12", "change": "-8.40", "pct": "-0.0051"}, {"id": "VN30", ...}]},
 "board": {"status": "ok", "trading_date": "2026-10-26",
           "value_matched_bn": "13528.79", "volume_matched": 605225925,
           "breadth": {"up": 107, "down": 205, "flat": 65, "no_trade": 30},
           "foreign": {"buy_volume": 0, "sell_volume": 0, "buy_value_bn": "0", "sell_value_bn": "0", "net_value_bn": "0",
                       "top_sell": [{"symbol": "VHM", "net_value_bn": "-210.5"}], "top_buy": [...]},
           "sectors": [{"sector": "Ngân hàng", "pct": "-0.0123", "count": 27}],
           "symbols": {"FPT": {"price": 56000, "ref": 57000, "change": -1000, "pct": "-0.0175", "sector": "Công nghệ Thông tin"}}},
 "hose": {"status": "missing", "reason": "HOSE chưa công bố"},
 "news": {"status": "ok", "items": [{"title": "...", "url": "https://...", "source": "CafeF", "published": "2026-10-26T15:20:00+07:00"}]},
 "proprietary": {"status": "missing", "reason": "Chưa có nguồn miễn phí"}}
```
The board section stores every HOSE symbol (about 407 rows), so any held ticker can be shown.

---

### Task 1: Board maths (`brief/board.py`)

**Files:** Create `backend/src/investment_agent/brief/__init__.py` and `backend/src/investment_agent/brief/board.py`. Test: `backend/tests/brief/test_brief_board.py`.

`summarise_board(records, *, session_date, icb_names) -> dict`. `records` are flat dicts, one per HOSE stock, built by the adapter in Task 5 with keys `symbol, trading_date, ref_price, match_price, accumulated_value, accumulated_volume, foreign_buy_volume, foreign_sell_volume, foreign_buy_value, foreign_sell_value, icb_code2`.
- **Status:** `missing` with reason "Bảng giá chưa phải phiên này" if no record has `trading_date == session_date`.
- **Breadth:** traded means `match_price > 0`. Up, down and flat compare against `ref_price`; untraded records count as `no_trade`.
- **Totals:**
  - `value_matched_bn` = Σ accumulated_value / 1000 (million → billion), 2 decimals;
  - `volume_matched` = Σ accumulated_volume.
- **Foreign:**
  - volume sums, plus value sums in billions (đồng / 1e9, 2 decimals);
  - `net_value_bn` = buy − sell;
  - per symbol, net = buy_value − sell_value; top 3 most negative (`top_sell`) and top 3 most positive (`top_buy`), skipping zeros.
- **Sectors:** for traded symbols only, average of `(match − ref) / ref` grouped by `icb_names.get(icb_code2, "Khác")`, 4 decimals as a string; sorted by pct descending; each with `count`.
- **Symbols:** symbol → `{price, ref, change, pct, sector}`. `pct` is a string with 4 decimals; `None` if not traded.

**Tests (RED first):** a 6-record fixture, one of them untraded and one on a wrong date, checking:
- breadth counts;
- the value and volume sums with unit conversion;
- foreign totals and top lists, with zeros skipped;
- sector averages and order;
- the symbols map;
- the missing case when every `trading_date` differs.

Commit `feat: brief board maths (breadth, foreign, sectors)`.

### Task 2: Index changes (`brief/indices.py`)

`index_rows(series_by_id: dict[str, list[tuple[datetime, float]]], *, session_date) -> dict`:
- For each id in (`VNINDEX`, `VN30`), take the close dated `session_date` and the previous close: `change = close − prev` (2 decimals), `pct = change / prev` (4 decimals).
- If there is no close on `session_date`, the row gets `status` "missing" with reason "Chưa có giá chỉ số phiên này".
- The section is `ok` if at least one row is present.

**Tests:** normal case, a missing session close, and a single point (no previous close). Commit `feat: brief index changes`.

### Task 3: News (`brief/news.py`)

- `parse_rss(xml: str, source: str) -> list[dict]`:
  - reads title, link and pubDate (RFC 822 to ISO with timezone);
  - strips CDATA and HTML entities;
  - keeps only `http(s)` links (reuse `insights.sources.safe_url`).
- `FEEDS`: the 5 URLs from the spec, each labelled CafeF, Vietstock or Vneconomy.
- `window_items(items, *, since, until)`: keeps items published in the window, deduplicated by normalised title (casefold, collapsed whitespace, punctuation removed), newest first.
- `pick_news(items, *, watched, held, sector_names, limit) -> list[dict]`: render-time and local.
  - An item matches when its title contains a held or watched ticker as a whole word (uppercase match), the name of a sector of those tickers (casefold), or a macro keyword (`MACRO_KEYWORDS`: lãi suất, tỷ giá, Fed, FED, GDP, CPI, lạm phát, NHNN, Ngân hàng Nhà nước, thuế quan, xuất khẩu, nhập khẩu, FDI, trái phiếu Chính phủ, room tín dụng).
  - Score: held ticker 3, watched ticker 2, sector 1, macro 1. Sort by score, then newest.
  - Each item carries `reason` (e.g. "HPG", "Ngân hàng", "vĩ mô").

**Tests:**
- parse a 3-item RSS fixture, with CDATA and a `javascript:` link that is dropped;
- the window and dedupe across two sources;
- a held ticker outranks a watched one, which outranks macro;
- "MBB" does not match "MBBANK" as a whole word? MBB inside "MBBank" is a substring with no word boundary, so it is **not** matched;
- the limit.

Commit `feat: brief news parsing and local filtering`.

### Task 4: HOSE statistics (`brief/hose.py`)

`parse_hose(value_json: str, volume_json: str) -> dict`:
- From the value report, take the rows "Mua", "Bán" and "Mua - Bán" via `foreign_trading_value`, plus `market_value` on the "Mua" row (the total trading value).
- From the volume report, take `foreign_trading_volumn` for Mua and Bán, plus `market_volumn`.
- Strip `,`. Values are in million đồng → `*_bn` = /1000. Volumes are in thousand shares → ×1000 as an int.
- Empty `data` gives `{"status": "missing", "reason": "HOSE chưa công bố"}`; anything malformed gives `missing` with reason "HOSE đổi định dạng".

**Tests:** use the real 2026-10-23 payloads captured in the probe (copy from the plan appendix) and the empty case. Commit `feat: brief HOSE statistics parser`.

### Task 5: Adapter, store and builder

**Files:** Modify `market/providers/vnstock_adapter.py`:
- `hose_listing()`: returns `{"symbols": [...], "icb_names": {code: name}}` from `Listing(source="VCI").symbols_by_exchange()`, where exchange is `HSX` and type is `STOCK`, plus `industries_icb()` level-2 names.
- `price_board(symbols)`: returns flat records from `Trading(source="VCI").price_board(symbols)`, with the MultiIndex columns `('listing', …)` and `('match', …)` flattened to the record keys of Task 1.

Create `brief/snapshot.py`:
- `BriefStore(data_dir)` with `read(session) -> dict | None` and `write(snapshot)` (atomic, like `InsightStore.save`).
- `build_snapshot(*, session_date, now, listing, board, series, hose_get, rss_get, store, previous_close) -> dict`:
  - Each section is computed inside its own `try`; an exception gives `{"status": "missing", "reason": "<short Vietnamese>"}`.
  - Read the existing snapshot and keep sections that were `ok` before and are `missing` now. A later wake-up can fill gaps, never erase them.
  - `proprietary` is always `{"status": "missing", "reason": "Chưa có nguồn miễn phí"}`.
  - News window: `since` = 15:00 on the previous session date (VN time), `until` = now.
- `latest_session(now, cal)`: today if it is a session and at or after 15:00 VN time; otherwise the previous session.

**Tests** (fakes for every callable):
- all sections ok;
- the board on a wrong date → missing;
- each source raising → only that section missing;
- an `ok` section is kept when a later run fails;
- `latest_session` before and after 15:00, and over a weekend.

Commit `feat: brief snapshot builder and store`.

### Task 6: CLI `brief-snapshot` and scheduler step

- **CLI** `brief-snapshot --data-dir --calendar`:
  - Refresh `data/hose-listing.json` if it is older than 7 days.
  - Build with the real adapter, `SeriesStore(data/trend-sources)`, and httpx with the project User-Agent and 30 s timeout. Use HOSE URLs `.../foreign-trading-value-report?fromDate=D&toDate=D` and `...-volumn-report...`.
  - Print `{"status": "ok", "session": ..., "sections": {name: status}}`.
  - Exit 2 if Vnstock is unavailable; the other sections are still written.
- **Scheduler:** in `run-after-close.ps1`, add the step after `trend-run` and before `scheduled-run`, logged like the other steps.
- **Tests:**
  - a CLI-level test with monkeypatched builders that checks the printed sections;
  - `test_scheduler_script.py` gains a check that `brief-snapshot` runs before `scheduled-run`.

Commit `feat: brief-snapshot step on every wake-up`.

### Task 7: Render-time view (`brief/view.py`)

`market_view(snapshot, *, watched: list[str], held: set[str]) -> dict | None`:
- returns `None` when there is no snapshot;
- passes indices, board totals, breadth, foreign, proprietary, sectors and hose through;
- builds `tickers`: held tickers first (even outside watched), then watched ones by |pct| descending. Each row is `{symbol, price, change, pct, held, sector}`, with `pct None` when not traded;
- builds `news = pick_news(..., limit=8)`.

**Tests:** held ordering, a held ticker outside watched, untraded handling, and news limited to 8. Commit `feat: brief market view for the page and Telegram`.

### Task 8: Telegram short version

- `render_report(report, market=None)`. When `market` is a dict, the body is:
  - `BẢN TIN SAU PHIÊN dd/mm/yyyy`;
  - A1: indices with points and %;
  - A2: value;
  - A3: breadth;
  - A4: foreign, with net and top 3/3;
  - A5: proprietary;
  - A6: sectors, all of them on one compact line each;
  - up to 3 held tickers;
  - up to 5 news items (title, source);
  - one line "Danh mục: <headline>";
  - the reminders section, unchanged;
  - "Xem bản đầy đủ trong ứng dụng, mục Bản tin sau phiên".
- No per-ticker actions and no verification flags. With `market=None`, the current text stays (back-compat for old reports).
- `deliver(report, settings, sender, store, market=None)` passes it through.
- `scheduled_tick(..., market_for: Callable[[str], dict | None] = lambda d: None)`: `_send_queued` calls `market_for(report["session_date"])`.
- The CLI wires `market_for` with `BriefStore` + `load_watchlist` + `held_from_repo`.
- The notifications preview and test-send routes do the same with `app.state.data_dir`.

**Tests:**
- the rendered text has the sections in order, and missing sections read "chưa có số liệu";
- it contains no "outside_research_universe" and no flag codes;
- the old path is unchanged;
- `scheduled_tick` passes the snapshot for the report's session.

Commit `feat: short Telegram brief with the market section`.

### Task 9: Reports API

`GET /internal/reports/{id}` adds `"market": market_view(BriefStore(data_dir).read(report["session_date"]), watched=..., held=...)`, which is `None` when no snapshot or `data_dir` exists. The Firestore record stays untouched.

**Test:** seed a report with a snapshot file, check `market` is present with held first; without a file, `market` is `null`. Commit `feat: reports API serves the market section`.

### Task 10: Report page

- `report-view.tsx`: a new "Thị trường phiên dd/mm" block at the top with A1–A8.
  - Points and % use green/red text plus a sign; colour is never the only signal.
  - Missing sections show the reason in muted text.
  - Watched tickers: the held ones and the top 10 by move, then a "Xem thêm" toggle.
- Section C:
  - **"Cơ hội và cảnh báo":** when every item has the same reasons, render one line "Tất cả mã: <reason>"; otherwise per item.
  - Remove the narrative ("Nhận định") section.
  - **"Kiểm tra dữ liệu":** moved last, as `caption` text, with `universe_incomplete`, `market_provenance:*` and `ai_not_configured` mapped to Vietnamese in `labels.ts`.
- `HoldingsTable` gets a `showScope` prop (default `true`); the report passes `false`, so the "Phạm vi" column disappears in the brief only.
- **e2e** (`tests/e2e/report-market.spec.ts`), with the fixture writing a snapshot for the fixture report's session:
  - the market block shows VN-Index with points and %;
  - breadth, foreign top lists, a sector, the proprietary missing note and a news link;
  - no "Phạm vi" header;
  - no horizontal scroll at 375px.

Commit `feat: market section on the report page`.

### Task 11: Live check, PR

- Run `brief-snapshot` once against the live sources for 26/10.
- Compare VN-Index points, breadth and foreign net with CafeF's "Phiên 26/10: Khối ngoại bán ròng gần 900 tỷ" headline and with the HOSE page; report any gap.
- `verify.ps1` must pass, then open the PR. Merge only after the owner approves.

## Appendix: HOSE payload (2026-10-23, from the probe)
- **Value report rows:**
  - Mua: `foreign_trading_value` "1,896,838.66", `market_value` "17,010,236.60";
  - Bán: "2,374,562.09";
  - Mua - Bán: "-477,723.43".
- **Volume report rows:**
  - Mua: `foreign_trading_volumn` "707,544.22", `market_volumn` "8,438,955.55";
  - Bán: "903,951.66".
