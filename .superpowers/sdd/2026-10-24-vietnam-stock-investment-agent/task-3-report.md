# Task 3 report — versioned local observations and snapshots

Status: DONE. Baseline: `383b0ac`. No live provider, AI, cloud, or personal ledger calls were made.

## Files

- `backend/src/investment_agent/market/parquet_store.py`: content-addressed Parquet files, generated filenames, temp write plus atomic replace, checksum and domain roundtrip.
- `backend/src/investment_agent/repositories/migrations/001_initial.sql`: schema version 1 catalog, jobs, manifests, snapshots, uniqueness constraints, and immutability triggers.
- `backend/src/investment_agent/repositories/sqlite.py`: observation revision catalog, idempotent retry/conflict rejection, manifest publication and validation, job identity, and read APIs.
- `backend/tests/repositories/test_snapshots.py`: real temporary SQLite/Parquet tests of revisions, retries, missing values, crash rollback/reopen/orphan, manifest integrity, paths, and immutable rows.
- `backend/pyproject.toml`: includes migration SQL in the built package.

## Interfaces and choices

`ParquetStore(root).write_observation/read_observation/resolve/checksum`; `LocalRepository(database, store).save_observation/list_observations/observation_path/record_job/publish_snapshot/get_snapshot`. `Snapshot` contains immutable ID, manifest ID, version tuple, observation IDs and validated observations. The logical observation key is entity, metric, period end, publication timestamp, revision ID and source ID. Same key and content is a retry; changed content at that key raises a conflict. Existing Parquet files are checked before reuse.

Files are written before a short SQLite transaction; a crash can leave an unreferenced file but cannot expose an incomplete catalog row or snapshot. Publication validates every referenced file, then inserts manifest and snapshot in one transaction. Reads recheck manifest hashes and file checksums. Provider IDs never form paths. Decimal values remain strings in Parquet and missing values remain null with reason. SQLite is derived/cache state; personal truth remains in Firestore.

## Evidence

- RED: `.\.venv\Scripts\python.exe -m pytest backend/tests/repositories/test_snapshots.py -q` failed at collection as expected (`ModuleNotFoundError: investment_agent.market`). Complete output: `task-3-red.log`.
- Initial GREEN: same focused command, 5 passed. Complete output: `task-3-green.log`.
- Final backend suite after path and immutability additions: `.\.venv\Scripts\python.exe -m pytest backend/tests -q` → 38 passed in 0.61s. Complete output: `task-3-suite.log`.
- Package check: `.\.venv\Scripts\python.exe -m pip wheel .\backend --no-deps --no-build-isolation --no-index -w .superpowers/sdd/2026-10-24-vietnam-stock-investment-agent/task-3-wheel` succeeded; wheel ZIP includes `investment_agent/repositories/migrations/001_initial.sql`. Complete output: `task-3-wheel.log`. An earlier `pip wheel backend` attempt interpreted `backend` as an index package and failed due an unrelated local CA bundle path; corrected to local `.\backend` and `--no-index`.
- `git diff --check` passed.

## Scope and concerns

Crash behavior is tested using a raised exception before SQLite commit, then closing/reopening the real database; unreferenced Parquet files are deliberately left for later cleanup. Cross-process kill/power-loss durability and live source ingestion are not claimed. Job metadata currently records initial identity/status; later scheduler work can add explicit state transitions without changing immutable observation/snapshot records.
