# Investment Agent

Local Windows scaffold for a Vietnamese stock research application. No financial
logic, live data, Firebase resources, AI calls, or Telegram delivery exists yet.

## Runtimes

Use Node **24 LTS**, npm 11, Git 2, and 64-bit CPython **3.11**. Python is limited
to 3.11 in the package metadata so the checked Windows wheel set stays reproducible.
This bootstrap was verified with Node 25.9.0, npm 11.12.1, Python 3.11.6 and Git
2.56.0.windows.2. Node 25 is EOL and is only the available verification runtime;
validation on the recommended Node 24 LTS remains outstanding.

References checked 2026-10-24: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation)
(Node >=20.9), [Node release policy](https://nodejs.org/en/about/previous-releases),
[pandas installation](https://pandas.pydata.org/docs/getting_started/install.html),
and [PyArrow installation](https://arrow.apache.org/docs/python/install.html).
The lock selects pandas 2.3.3 and PyArrow 23.0.1 with CPython 3.11 Windows wheels.

## Setup (PowerShell, repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e backend
npm.cmd --prefix apps/web ci
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/doctor.ps1
npm.cmd --prefix apps/web run dev
```

Open http://127.0.0.1:3000. Use `npm.cmd` to avoid invoking `npm.ps1`; no change to
system execution policy is needed. The doctor invocation sets execution policy for
that PowerShell process only.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
npm.cmd --prefix apps/web run typecheck
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run test -- --run
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web run test:e2e
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/test-doctor.ps1
```

No business tests exist at bootstrap: pytest exits 5 and Playwright exits 1 for
empty suites; Vitest explicitly permits an empty suite. These are not evidence
of tested product behavior. Future tasks add meaningful tests. Install Playwright
browsers when browser tests are introduced using `npx.cmd --prefix apps/web playwright install chromium`.

`.env.example` lists names only, with blank values. Local scaffold checks need no
credentials. `doctor.ps1` checks installed Node (>=22.12, <27), npm 11, Git 2,
and both global and project venv 64-bit Python 3.11; it warns when Node is not
the recommended 24 LTS. `doctor.ps1 -RequireServices` checks all listed names in the process
environment, never their values or remote validity. Optional services may remain
unset until their implementation is explicitly enabled. No `.env` auto-loading
is performed by doctor. Credentials, personal data, logs, and backups stay out of Git;
synthetic fixtures remain versioned. Firestore will own personal records; local
SQLite/Parquet will hold derived and market analysis state.
