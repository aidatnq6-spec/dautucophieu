// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
import { SessionError, createOwnerSession, verifyOwnerSession, assertMutation, cookieOptions } from "./session";

const now = 1_800_000_000;
const claims = { uid: "owner-1", auth_time: now - 10, firebase: { sign_in_provider: "google.com" } };
const config = { ownerUid: "owner-1", origin: "http://127.0.0.1:3000" };
const auth = {
  verifyIdToken: vi.fn(), createSessionCookie: vi.fn(), verifySessionCookie: vi.fn(), revokeRefreshTokens: vi.fn(),
};
beforeEach(() => {
  vi.resetAllMocks();
  auth.verifyIdToken.mockResolvedValue(claims);
  auth.createSessionCookie.mockResolvedValue("signed-cookie");
  auth.verifySessionCookie.mockResolvedValue(claims);
});
const csrf = "a".repeat(64);
function request(origin: string | null = config.origin, token: string | null = csrf) {
  const headers: Record<string, string> = { host: "127.0.0.1:3000" };
  if (origin) headers.origin = origin;
  if (token) headers["x-csrf-token"] = token;
  return new Request(`${config.origin}/api/session`, { method: "POST", headers });
}

describe("owner sessions", () => {
  it("creates a cookie only for a recently authenticated Google owner", async () => {
    expect(await createOwnerSession("id-token", auth, config, now)).toBe("signed-cookie");
    expect(auth.verifyIdToken).toHaveBeenCalledWith("id-token", true);
    expect(auth.createSessionCookie).toHaveBeenCalledWith("id-token", { expiresIn: 432000000 });
  });
  it.each([
    { ...claims, uid: "intruder" },
    { ...claims, firebase: { sign_in_provider: "password" } },
    { ...claims, auth_time: now - 301 },
    { ...claims, auth_time: now + 61 },
    { ...claims, auth_time: NaN },
  ])("rejects invalid claims before cookie creation: %j", async (value) => {
    auth.verifyIdToken.mockResolvedValue(value);
    await expect(createOwnerSession("id-token", auth, config, now)).rejects.toBeInstanceOf(SessionError);
    expect(auth.createSessionCookie).not.toHaveBeenCalled();
  });
  it.each(["expired", "revoked", "disabled"])("rejects %s sessions", async (error) => {
    auth.verifySessionCookie.mockRejectedValue(new Error(error + " SECRET"));
    await expect(verifyOwnerSession("cookie", auth, config)).rejects.toThrow("Phiên đăng nhập không hợp lệ.");
    expect(auth.verifySessionCookie).toHaveBeenCalledWith("cookie", true);
  });
  it("rechecks owner for every session", async () => {
    auth.verifySessionCookie.mockResolvedValue({ ...claims, uid: "intruder" });
    await expect(verifyOwnerSession("cookie", auth, config)).rejects.toBeInstanceOf(SessionError);
  });
  it("rejects missing cookie without calling Firebase", async () => {
    await expect(verifyOwnerSession(undefined, auth, config)).rejects.toBeInstanceOf(SessionError);
    expect(auth.verifySessionCookie).not.toHaveBeenCalled();
  });
  it("accepts matching origin and csrf", () => {
    expect(() => assertMutation(request(), csrf, config)).not.toThrow();
  });
  it.each([[null, csrf, csrf], ["http://evil.test", csrf, csrf], [config.origin, null, csrf], [config.origin, csrf, undefined], [config.origin, "b".repeat(64), csrf]])("rejects origin/csrf mismatch", (origin, token, cookie) => {
    expect(() => assertMutation(request(origin, token), cookie, config)).toThrow(SessionError);
  });
  it("uses HttpOnly cookies with explicit loopback HTTP exception", () => {
    expect(cookieOptions(config)).toMatchObject({ httpOnly: true, sameSite: "lax", secure: false, path: "/" });
    expect(cookieOptions({ ...config, origin: "https://localhost:3000" }).secure).toBe(true);
    expect(() => cookieOptions({ ...config, origin: "http://example.com" })).toThrow(SessionError);
  });
});
