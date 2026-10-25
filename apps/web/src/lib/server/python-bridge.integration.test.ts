// @vitest-environment node
import { spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
import { signInternalRequest } from "./python-client";

let process: ChildProcess;
let origin: string;
const token = "integration-token-" + "a".repeat(32);
const hmacSecret = "integration-hmac-" + "b".repeat(32);
const root = fileURLToPath(new URL("../../../../../", import.meta.url));

beforeAll(async () => {
  const port = await new Promise<number>((resolve, reject) => {
    const socket = createServer();
    socket.on("error", reject);
    socket.listen(0, "127.0.0.1", () => {
      const address = socket.address();
      if (!address || typeof address === "string") return reject(new Error("No test port"));
      socket.close(() => resolve(address.port));
    });
  });
  origin = `http://127.0.0.1:${port}`;
  const python = fileURLToPath(new URL("../../../../../.venv/Scripts/python.exe", import.meta.url));
  process = spawn(python, ["-m", "uvicorn", "investment_agent.api.app:create_app", "--factory", "--host", "127.0.0.1", "--port", String(port), "--no-proxy-headers", "--no-access-log", "--log-level", "error"], {
    cwd: root, windowsHide: true, stdio: "ignore",
    env: { ...globalThis.process.env, FIREBASE_OWNER_UID: "owner-1", INTERNAL_API_TOKEN: token, INTERNAL_API_HMAC_SECRET: hmacSecret },
  });
  let failure: Error | undefined;
  process.on("error", (error) => { failure = error; });
  for (let i = 0; i < 100; i++) {
    if (failure) throw failure;
    try { if ((await fetch(origin + "/health")).ok) return; } catch { /* wait for local test server */ }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error("Python test server did not become ready");
}, 10000);
afterAll(() => { process?.kill(); });

it("accepts the TypeScript signature in Python, rejects replay and tampering over HTTP", async () => {
  const headers = signInternalRequest({ origin, token, hmacSecret }, { uid: "owner-1", method: "GET", target: "/internal/identity", body: "", timestamp: Math.floor(Date.now() / 1000), nonce: "0123456789abcdef0123456789abcdef", correlationId: "cross-language-1" });
  const response = await fetch(origin + "/internal/identity", { headers });
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ uid: "owner-1", role: "owner", correlation_id: "cross-language-1" });
  expect((await fetch(origin + "/internal/identity", { headers })).status).toBe(401);
  expect((await fetch(origin + "/internal/identity?changed=1", { headers })).status).toBe(401);
  expect((await fetch(origin + "/internal/identity")).status).toBe(401);
});

it("binds nonempty UTF-8 body bytes and the method across runtimes", async () => {
  const body = JSON.stringify({ note: "Cổ tức bằng tiền — dữ liệu kiểm thử", amount: "100000" });
  const headers = signInternalRequest({ origin, token, hmacSecret }, { uid: "owner-1", method: "POST", target: "/internal/identity", body, timestamp: Math.floor(Date.now() / 1000), nonce: "1123456789abcdef0123456789abcdef", correlationId: "cross-language-2" });
  // Correct authentication reaches routing (identity is GET-only); tampering
  // must instead be stopped by the authentication boundary before routing.
  expect((await fetch(origin + "/internal/identity", { method: "POST", headers, body: body + " " })).status).toBe(401);
  expect((await fetch(origin + "/internal/identity", { method: "POST", headers, body })).status).toBe(405);
});
