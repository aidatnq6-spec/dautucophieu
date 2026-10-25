import { randomBytes } from "node:crypto";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

// Specs live in the repository-level tests/e2e; resolve their imports from this app's node_modules.
const here = path.dirname(fileURLToPath(import.meta.url));
process.env.NODE_PATH = path.join(here, "node_modules");
(createRequire(import.meta.url)("module") as { _initPaths(): void })._initPaths();

// One-off secrets per run; the e2e session verifier is refused outside `next dev`.
const session = process.env.INVESTMENT_E2E_SESSION ?? randomBytes(24).toString("hex");
process.env.INVESTMENT_E2E_SESSION = session;
const env = {
  FIREBASE_OWNER_UID: "e2e-owner",
  INTERNAL_API_TOKEN: randomBytes(24).toString("hex"),
  INTERNAL_API_HMAC_SECRET: randomBytes(24).toString("hex"),
  APP_ORIGIN: "http://127.0.0.1:3100",
  PYTHON_API_ORIGIN: "http://127.0.0.1:8765",
  E2E_PYTHON_PORT: "8765",
  INVESTMENT_E2E_AUTH: "1",
  INVESTMENT_E2E_SESSION: session,
};

export default defineConfig({
  testDir: "../../tests/e2e",
  timeout: 60_000,
  workers: 1,
  use: { baseURL: env.APP_ORIGIN },
  webServer: [
    { command: "..\\..\\.venv\\Scripts\\python.exe ..\\..\\tests\\e2e\\fixture_backend.py", url: "http://127.0.0.1:8765/health", env, reuseExistingServer: false, timeout: 60_000 },
    { command: "npx next dev --hostname 127.0.0.1 --port 3100", url: "http://127.0.0.1:3100/login", env, reuseExistingServer: false, timeout: 180_000 },
  ],
});
