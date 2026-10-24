// @vitest-environment node
import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
vi.mock("server-only", () => ({}));
import { sessionHandlers } from "./session-handlers";

const origin = "http://127.0.0.1:3000";
const csrf = "a".repeat(64);
const auth = { verifyIdToken: vi.fn(), createSessionCookie: vi.fn(), verifySessionCookie: vi.fn(), revokeRefreshTokens: vi.fn() };
const factory = vi.fn(() => auth);
const handlers = sessionHandlers(factory, () => ({ ownerUid: "owner-1", origin }));
beforeEach(() => {
  vi.resetAllMocks();
  factory.mockReturnValue(auth);
  const claims = { uid: "owner-1", auth_time: Date.now() / 1000, firebase: { sign_in_provider: "google.com" } };
  auth.verifyIdToken.mockResolvedValue(claims);
  auth.verifySessionCookie.mockResolvedValue(claims);
  auth.createSessionCookie.mockResolvedValue("new-session");
});
function post(path: string, headers: Record<string, string> = {}, body = JSON.stringify({ idToken: "valid-id-token" })) {
  return new NextRequest(origin + path, { method: "POST", headers: { host: "127.0.0.1:3000", origin, "content-type": "application/json", cookie: `investment_csrf=${csrf}; investment_session=old-session`, "x-csrf-token": csrf, ...headers }, body });
}
it("issues csrf without touching Firebase", async () => {
  const response = await handlers.csrf(new NextRequest(origin + "/api/session", { headers: { host: "127.0.0.1:3000" } }));
  expect(response.status).toBe(200);
  expect((await response.json()).csrfToken).toMatch(/^[a-f0-9]{64}$/);
  expect(response.cookies.get("investment_csrf")?.httpOnly).toBe(true);
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(factory).not.toHaveBeenCalled();
});
it("sets HttpOnly session on authenticated login", async () => {
  const response = await handlers.login(post("/api/session"));
  expect(response.status).toBe(200);
  expect(response.cookies.get("investment_session")).toMatchObject({ value: "new-session", httpOnly: true, sameSite: "lax", path: "/" });
  expect(await response.json()).toEqual({ status: "authenticated" });
});
it.each<Record<string, string>>([{ origin: "http://evil.test" }, { "x-csrf-token": "" }, { cookie: "" }, { host: "evil.test:3000" }])("rejects invalid login before Firebase", async (headers) => {
  const response = await handlers.login(post("/api/session", headers));
  expect(response.status).toBe(403);
  expect(factory).not.toHaveBeenCalled();
});
it("rejects malformed JSON without leaking content", async () => {
  const response = await handlers.login(post("/api/session", {}, "SECRET"));
  expect(response.status).toBe(400);
  expect(await response.text()).not.toContain("SECRET");
});
it("revokes owner sessions and clears both cookies on logout", async () => {
  const response = await handlers.logout(post("/api/logout"));
  expect(response.status).toBe(200);
  expect(auth.revokeRefreshTokens).toHaveBeenCalledWith("owner-1");
  expect(response.cookies.get("investment_session")?.maxAge).toBe(0);
  expect(response.cookies.get("investment_csrf")?.maxAge).toBe(0);
});
it("does not revoke on cross-origin logout", async () => {
  expect((await handlers.logout(post("/api/logout", { origin: "http://evil.test" }))).status).toBe(403);
  expect(auth.revokeRefreshTokens).not.toHaveBeenCalled();
});
it("reports revoke failure safely and clears the local cookie", async () => {
  auth.revokeRefreshTokens.mockRejectedValue(new Error("SECRET"));
  const response = await handlers.logout(post("/api/logout"));
  expect(response.status).toBe(503);
  expect(response.cookies.get("investment_session")?.maxAge).toBe(0);
  expect(await response.text()).not.toContain("SECRET");
});
