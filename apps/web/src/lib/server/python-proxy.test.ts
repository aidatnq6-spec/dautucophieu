// @vitest-environment node
import { createHash, createHmac } from "node:crypto";
import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
vi.mock("server-only", () => ({}));
import { proxyInternal } from "./python-proxy";

const config = { ownerUid: "owner-1", origin: "http://127.0.0.1:3000" };
const bridge = { origin: "http://127.0.0.1:8000", token: "a".repeat(32), hmacSecret: "b".repeat(32) };
const auth = { verifyIdToken: vi.fn(), createSessionCookie: vi.fn(), verifySessionCookie: vi.fn(), revokeRefreshTokens: vi.fn() };
const fetcher = vi.fn<typeof fetch>();
const csrf = "c".repeat(64);
beforeEach(() => {
  vi.resetAllMocks();
  auth.verifySessionCookie.mockResolvedValue({ uid: "owner-1", auth_time: 1, firebase: { sign_in_provider: "google.com" } });
  fetcher.mockResolvedValue(Response.json({ version: 1 }, { status: 200 }));
});

function request(method: string, path: string, { body, token = csrf, origin = config.origin }: { body?: string; token?: string | null; origin?: string } = {}) {
  const headers: Record<string, string> = { host: "127.0.0.1:3000", cookie: `investment_session=s; investment_csrf=${csrf}`, origin };
  if (token) headers["x-csrf-token"] = token;
  if (body !== undefined) headers["content-type"] = "application/json";
  return new NextRequest(`${config.origin}/api/internal/${path}`, { method, headers, body });
}

it("forwards an allowlisted read with a fresh signature", async () => {
  const response = await proxyInternal(request("GET", "ledger"), ["ledger"], auth, config, bridge, fetcher);
  expect(response.status).toBe(200);
  const [url, options] = fetcher.mock.calls[0];
  expect(url).toBe("http://127.0.0.1:8000/internal/ledger");
  expect(options).toMatchObject({ method: "GET", cache: "no-store", redirect: "error" });
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("signs exactly the forwarded mutation body", async () => {
  const body = JSON.stringify({ event: { type: "deposit" }, expected_version: 0, request_id: "r1" });
  await proxyInternal(request("POST", "ledger/events", { body }), ["ledger", "events"], auth, config, bridge, fetcher);
  const [, options] = fetcher.mock.calls[0];
  const headers = options?.headers as Record<string, string>;
  expect(options?.body).toBe(body);
  const canonical = ["v1", headers["x-request-timestamp"], headers["x-request-nonce"], "owner-1", "owner", headers["x-correlation-id"], "POST",
    "/internal/ledger/events", createHash("sha256").update(body).digest("hex")].join("\n");
  expect(headers["x-request-signature"]).toBe(createHmac("sha256", bridge.hmacSecret).update(canonical).digest("hex"));
});

it.each([["admin"], ["identity"], ["ledger", ".."], ["profile", "a b"], []])("rejects non-allowlisted path %j", async (...segments) => {
  const response = await proxyInternal(request("GET", segments.join("/")), segments, auth, config, bridge, fetcher);
  expect(response.status).toBe(404);
  expect(fetcher).not.toHaveBeenCalled();
});

it.each([[null], ["d".repeat(64)]])("mutations need the CSRF token (%s)", async (token) => {
  const response = await proxyInternal(request("PUT", "profile", { body: "{}", token }), ["profile"], auth, config, bridge, fetcher);
  expect(response.status).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});

it("rejects cross-origin mutations", async () => {
  const response = await proxyInternal(request("POST", "ledger/events", { body: "{}", origin: "http://evil.example" }), ["ledger", "events"], auth, config, bridge, fetcher);
  expect(response.status).toBe(403);
});

it("rejects an invalid session before any backend call", async () => {
  auth.verifySessionCookie.mockRejectedValue(new Error("revoked"));
  const response = await proxyInternal(request("GET", "ledger"), ["ledger"], auth, config, bridge, fetcher);
  expect(response.status).toBe(401);
  expect(fetcher).not.toHaveBeenCalled();
});

it("passes backend business errors through but hides transport failures", async () => {
  fetcher.mockResolvedValueOnce(Response.json({ code: "version_conflict", message: "Dữ liệu đã được cập nhật" }, { status: 409 }));
  const conflict = await proxyInternal(request("POST", "ledger/events", { body: "{}" }), ["ledger", "events"], auth, config, bridge, fetcher);
  expect(conflict.status).toBe(409);
  expect((await conflict.json()).code).toBe("version_conflict");
  fetcher.mockRejectedValueOnce(new Error("ECONNREFUSED SECRET"));
  const down = await proxyInternal(request("GET", "ledger"), ["ledger"], auth, config, bridge, fetcher);
  expect(down.status).toBe(502);
  expect(await down.text()).not.toContain("SECRET");
});

it("rejects oversized bodies", async () => {
  const response = await proxyInternal(request("PUT", "profile", { body: "x".repeat(1_048_577) }), ["profile"], auth, config, bridge, fetcher);
  expect(response.status).toBe(413);
});
