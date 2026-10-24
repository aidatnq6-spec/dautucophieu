// @vitest-environment node
import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
vi.mock("server-only", () => ({}));
import { proxyIdentity, signInternalRequest } from "./python-client";

const config = { ownerUid: "owner-1", origin: "http://127.0.0.1:3000" };
const bridge = { origin: "http://127.0.0.1:8000", token: "a".repeat(32), hmacSecret: "b".repeat(32) };
const auth = { verifyIdToken: vi.fn(), createSessionCookie: vi.fn(), verifySessionCookie: vi.fn(), revokeRefreshTokens: vi.fn() };
const fetcher = vi.fn<typeof fetch>();
beforeEach(() => {
  vi.resetAllMocks();
  auth.verifySessionCookie.mockResolvedValue({ uid: "owner-1", auth_time: 1, firebase: { sign_in_provider: "google.com" } });
  fetcher.mockResolvedValue(Response.json({ uid: "owner-1", role: "owner", correlation_id: "correlation-1" }));
});
function request(cookie = "investment_session=cookie") {
  return new NextRequest(config.origin + "/api/account", { headers: { host: "127.0.0.1:3000", cookie, "x-owner-uid": "intruder", authorization: "Bearer browser-token", "x-request-signature": "browser-signature" } });
}
it("signs a deterministic context", () => {
  const headers = signInternalRequest(bridge, { uid: "owner-1", method: "GET", target: "/internal/identity", body: "", timestamp: 1800000000, nonce: "0123456789abcdef0123456789abcdef", correlationId: "correlation-1" });
  expect(headers["x-request-signature"]).toMatch(/^[a-f0-9]{64}$/);
  expect(headers.authorization).toBe(`Bearer ${bridge.token}`);
});
it("verifies cookie on every call and discards browser identity headers", async () => {
  await proxyIdentity(request(), auth, config, bridge, fetcher);
  expect(auth.verifySessionCookie).toHaveBeenCalledWith("cookie", true);
  const [url, options] = fetcher.mock.calls[0];
  expect(url).toBe("http://127.0.0.1:8000/internal/identity");
  expect(options).toMatchObject({ cache: "no-store", redirect: "error" });
  expect(options?.headers).toMatchObject({ "x-owner-uid": "owner-1", "x-owner-role": "owner", authorization: `Bearer ${bridge.token}` });
});
it.each(["", "investment_session=expired"])("rejects missing/revoked cookies before backend access", async (cookie) => {
  auth.verifySessionCookie.mockRejectedValue(new Error("revoked SECRET"));
  await expect(proxyIdentity(request(cookie), auth, config, bridge, fetcher)).rejects.toThrow();
  expect(fetcher).not.toHaveBeenCalled();
});
it("rejects arbitrary upstream addresses", async () => {
  await expect(proxyIdentity(request(), auth, config, { ...bridge, origin: "http://example.com" }, fetcher)).rejects.toThrow();
  expect(fetcher).not.toHaveBeenCalled();
});
it("hides backend errors", async () => {
  fetcher.mockResolvedValue(new Response("SECRET", { status: 500 }));
  await expect(proxyIdentity(request(), auth, config, bridge, fetcher)).rejects.toThrow("Dịch vụ nội bộ chưa sẵn sàng.");
});
