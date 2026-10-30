# Chuỗi giá trị ngành Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Spec:** `docs/superpowers/specs/2026-10-30-chuoi-gia-tri-nganh-design.md` (owner-approved 2026-10-30). The spec is the authority.

**Goal:** A "Chuỗi giá trị" section on Thị trường & Ngành with one card per value chain, which opens into a sourced diagram (Đầu vào → Trung gian → Đầu ra). The card carries a weighted tốt/xấu bar computed from the stored macro series.

**Architecture:**
- Chain content is a committed public config, `config/value-chains.json`, validated by a pydantic loader in `market/value_chains.py`. A test fails the build on any item without a source.
- A pure scoring module, `domain/value_chain.py`, reads each factor's one-month direction from the `MacroStore` series. It then weights the factors (chính 3, phụ 2, nhỏ 1) and labels the card.
- A new route, `GET /internal/market/value-chains`, joins chains, readings, the watchlist and the held flags.
- The web component `value-chains.tsx` renders cards and the diagram under "Diễn biến theo ngành".

**Tech Stack:** Python 3.11, pydantic, FastAPI, pytest; Next.js, TypeScript, Playwright.

## Builder calls (made here, per the spec's "Để người làm quyết")

**Approval:** done by PR review. Each chain has `"status": "draft" | "approved"`. Chains are committed as `draft`, and the owner flips them to `approved` after reading. A draft shows "Chưa duyệt" and no overall label.

**Bands for "đi ngang":** compare the latest point with the last point at least 30 days earlier, the same base rule as `macro_chain._base`.
- Relative change: `wti` 5%, `dxy` 2%, `usd_vnd_*` 1%, `m2_vn` 1%, `vnindex_value` 15%.
- Point change: `vn_cpi_yoy` and `us_cpi_yoy` 0.2; every rate (`fed_effr`, `deposit_12m`, `us10y`, `vn10y`, `vn_interbank_on`) 0.25; `vn_pmi` and `us_pmi` 1.0.
- `foreign_net`: the sign of the sum over the last 20 sessions. Net buying reads "up".

**Stale:** a point older than the indicator's `max_age_days` in `config/macro-indicators.json` reads "chưa đánh giá được".

**Weight from share:** take the midpoint of the share range. ≥ 0.25 is chính, ≥ 0.10 is phụ, otherwise nhỏ. The loader rejects a factor whose stated `weight` disagrees with its `share`.

**Percentages:** computed as Decimal shares of the total weight and sent as strings with 4 decimals; the UI rounds them.

## Global constraints
- No invented content: every stage item and every factor needs at least one source id that exists in `sources`. The loader rejects anything else.
- Symbols:
  - each symbol belongs to at most one chain;
  - watched symbols with no chain are returned as `uncovered`, and the UI says so;
  - the real config must cover all 50 watched symbols listed in the spec table.
- No AI, no personal data out, no Telegram. Held flags come only from the ledger, as on other pages.
- Process:
  - TDD, with each RED seen;
  - full backend suite before each commit;
  - `scripts\windows\verify.ps1` must pass before the PR;
  - commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Branch: `feat/value-chains` from `origin/main`. The spec commit goes on it too.

**Commodity series (owner approved 2026-10-30):**
- Ten monthly FRED IMF series, kept as `com_<name>` under `data/macro/`. The pairs are: coal `PCOALAUUSDM`, iron_ore `PIORECRUSDM`, rubber `PRUBBUSDM`, sugar `PSUGAISAUSDM`, shrimp `PSHRIUSDM`, lng `PNGASJPUSDM`, aluminium `PALUMUSDM`, copper `PCOPPUSDM`, wheat `PWHEAMTUSDM` and soybean `PSOYBUSDM`.
- They are fetched by `macro-sync` through `fetch_commodities`, with the same retry as `fetch_factors`.
- They are not in `macro-indicators.json`, so they never show on Vĩ mô.
- Reading rules: relative band 5%; stale after 75 days.

**PMI and foreign flows:** reuse the existing rules. PMI reads "up" at ≥ 50 and not falling, "down" below 50 and not rising, otherwise flat. `foreign_net` reads the sign of its 20-session sum.

---

### Task 0: Commodity series

**Files:**
- Modify: `backend/src/investment_agent/market/leading.py` (add `COMMODITIES` and `fetch_commodities`)
- Modify: `backend/src/investment_agent/cli.py` (`macro_sync` also calls `fetch_commodities`)
- Test: `backend/tests/market/test_leading.py`

**Steps:**
1. Write the failing tests:
   - each series is stored under its `com_` key;
   - one failing series does not stop the others;
   - the request includes `cosd` set to three years back.
2. Implement.
3. Run the full suite, then commit.

### Task 1: Scoring module

**Files:**
- Create: `backend/src/investment_agent/domain/value_chain.py`
- Test: `backend/tests/domain/test_value_chain.py`

**Step 1: Write the failing tests.** Cover:
- `weight_for_share` boundaries: `0.0999` is nhỏ, `0.10` is phụ, `0.2499` is phụ, `0.25` is chính, and the range `0.35-0.40` is chính.
- `read_indicator`:
  - WTI up 6% over 30 days reads "up";
  - a rate up 0.1 pp reads "flat";
  - `foreign_net` summing negative over 20 sessions reads "down";
  - a series whose last point is older than `max_age_days` is stale;
  - an empty series reads `None`.
- `factor_status`:
  - `when_up="bad"` with "up" is bad;
  - with "down" it is good;
  - "flat" is neutral;
  - no indicator, no data, or stale data is unknown.
- `score`: factors weighted 3 good, 2 bad, 1 unknown give good 0.5000, bad 0.3333, neutral 0.0000, unknown 0.1667.
- `label`:
  - tailwind when good − bad ≥ 0.20;
  - headwind when bad − good ≥ 0.20;
  - neutral otherwise;
  - insufficient when unknown > 0.50, whatever the other shares;
  - `None` for a draft.

**Step 2:** Run `.venv/Scripts/python.exe -m pytest backend/tests/domain/test_value_chain.py -q -p no:warnings`. Expected: an ImportError (RED).

**Step 3: Implement.** The functions are `weight_for_share(share: str) -> str`, `read_indicator(indicator: str, points, *, today, max_age_days) -> dict | None`, `factor_status(when_up, reading) -> str`, `score(factors_with_status) -> dict[str, str]` and `label(score, *, approved: bool) -> str | None`. Reuse the 30-day base rule.

**Step 4:** Run the tests. Expected: PASS.

**Step 5:** Run the full backend suite, then commit (`feat: value-chain scoring …`).

### Task 2: Config loader and validator

**Files:**
- Create: `backend/src/investment_agent/market/value_chains.py` (pydantic models `Source`, `Ref`, `Item`, `Factor`, `Chain`, `ValueChains`; `load_value_chains(path=CONFIG_DIR / "value-chains.json")`)
- Create: `config/value-chains.json` (starts with the cement chain only, sourced from ACBS HT1 28/10/2026)
- Test: `backend/tests/market/test_value_chains.py`

**Step 1: Write the failing tests:**
- the loader rejects an item without sources;
- it rejects an unknown source id;
- it rejects an unknown indicator id (not in `macro-indicators.json`);
- it rejects a symbol that appears in two chains;
- it rejects a `weight` that disagrees with `share`;
- the real config loads, and every chain has at least one item in each stage and at least one factor.

**Step 2:** Run the tests. Expected: RED.

**Step 3: Implement** the models (`extra="forbid"`) and the cross-checks in a `model_validator`.

**Step 4:** Run the tests. Expected: PASS. Run the full suite, then commit.

### Task 3: Route `GET /internal/market/value-chains`

**Files:**
- Create: `backend/src/investment_agent/api/routes/value_chains.py` (prefix `/internal/market`)
- Modify: `backend/src/investment_agent/api/app.py` to register it.
- Test: `backend/tests/api/test_value_chains_route.py`

**Response shape:**
```
{"as_of", "uncovered": [...], "sources": {...},
 "chains": [{"id", "name", "icb", "status", "label", "score",
             "symbols": [{"symbol", "held"}],
             "stages": {...},
             "factors": [{..., "status", "reading"}]}]}
```

**Sort order:** tailwind → neutral → headwind → insufficient → drafts. Within each label, by good − bad, descending.

**Steps:**
1. Write the test, using a tmp data dir with macro observations, a watchlist and a config path override. Run it and see it fail.
2. Implement, then run the full suite and commit.

The proxy area `market` is already allowed in `apps/web/src/lib/server/python-proxy.ts`.

### Task 4: Web section

**Files:**
- Create: `apps/web/src/components/value-chains.tsx`
- Modify: `apps/web/src/components/market-view.tsx` to render `<ValueChains />` after "Diễn biến theo ngành".
- Modify: `apps/web/src/app/globals.css` (small `.vc-*` rules: card grid, weighted bar, three-column diagram that stacks below 720px).

**Steps:**
1. Build the component:
   - cards as buttons with `aria-expanded`;
   - the bar with a text legend ("tốt 55% · xấu 15% · …");
   - one open card at a time;
   - the diagram, with sources linking to `sources[id].url`;
   - factor chips that carry text ("tốt", "xấu", …), not colour only;
   - symbols linking to `/research/<mã>`.
2. Run typecheck and lint.

### Task 5: e2e

**Files:**
- Modify: `tests/e2e/fixture_backend.py` (synthetic macro observations for `wti` and `vn_interbank_on`)
- Create: `tests/e2e/value-chains.spec.ts`

**Checks:**
- the cards render with a label or "Chưa duyệt";
- opening a card shows "Đầu vào", "Trung gian" and "Đầu ra" and a source link;
- a symbol link opens the profile;
- there is no horizontal scroll at 375px.

### Task 6: Chain content for every watched symbol

**Files:**
- Modify: `config/value-chains.json`

Draft the chains from public documents you actually opened, citing each one by title, date, page or URL:
- ACBS "Báo cáo Ngành & Doanh nghiệp";
- the companies' annual reports;
- GSO and industry-association pages.

Group by chain, one commit per group. Groups:
1. banks; securities; insurance;
2. residential property; industrial parks; construction; building plastics;
3. steel; rubber; fertiliser; oil-gas services; gas; power;
4. ports; shipping; dairy; seafood; sugar; consumer staples; retail (ICT and jewellery); IT.

Every chain stays `draft`. Run the loader test after each group.

### Task 7: Verify and open the PR

**Steps:**
1. Run `scripts\windows\verify.ps1`.
2. Restore `apps/web/next-env.d.ts`.
3. Push `feat/value-chains` and hand over the PR link with a title and description.
4. Tell the owner the chains are drafts to read, and how to approve them (flip `status`).
