# Task 4 report

Status: DONE. Base: `b1fdb13`.

## Files and interfaces

- `backend/src/investment_agent/market/base.py`: explicit `ProviderCapabilities` with verified/unavailable/unknown states and `MarketProvider` protocol for capabilities, prices, financials, actions and disclosures. No live provider is implemented.
- `backend/src/investment_agent/market/coverage.py`: `audit_case` returns issuer-level gaps, section evidence, synthetic/live labels and separate `eligible` versus `live_eligible` decisions. Checks current HOSE, continuous same-issuer exchange segments, 10 calendar years of verified continuous price and P/E/P/B history, 10 unique contiguous annual and 40 unique contiguous quarter periods, adjustment method, statements, actions, publication history and personal-analysis rights. Explained invalid ratio intervals are retained.
- `backend/src/investment_agent/cli.py`: `python -m investment_agent.cli data-audit --fixtures [--output-dir PATH]` writes `data-audit.json` and `data-audit.md` locally. Without `--fixtures` it fails closed.
- `tests/fixtures/market/coverage_cases.json`: synthetic passing transfer case and unverified source case.
- `backend/tests/market/test_coverage.py`: decision and boundary tests.
- `docs/data/source-evaluation-template.md`: evidence worksheet for real provider review.

## TDD and verification

RED: `./.venv/Scripts/python.exe -m pytest backend/tests/market/test_coverage.py -q` initially failed during collection with `ModuleNotFoundError: No module named 'investment_agent.market.coverage'` (exit 1). After first implementation, it exposed an enum serialization bug: `AttributeError: 'str' object has no attribute 'value'` (4 failed, exit 1). Fixed by converting supplied capability states to enum values.

GREEN: focused `./.venv/Scripts/python.exe -m pytest backend/tests/market/test_coverage.py -q` produced `11 passed in 0.10s` (exit 0). After moving fixture to the required root path and adding the unverified case, `./.venv/Scripts/python.exe -m pytest backend/tests -q` produced `49 passed in 0.61s` (exit 0). `python -m investment_agent.cli data-audit --fixtures --output-dir .superpowers/sdd/2026-10-24-vietnam-stock-investment-agent/task-4-audit-output` exited 0 and wrote both report formats. `git diff --check` exited 0.

## Self-review and limits

The passing fixture is explicitly synthetic, so its `live_eligible` is false. An unknown capability, right, revision history or timestamp causes a named gap; ticker reuse across issuers and endpoint-only price ranges do not establish continuity. The audit accepts documented continuity assertions from the fixture; it does not independently download or reconcile live exchange sessions. Provider rights and 50-issuer live coverage remain unverified for Task 5 and later source evaluation. The generated output files are local verification artifacts and are not committed.
