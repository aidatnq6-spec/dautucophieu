import "server-only";
import { timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE = "investment_session";
export const CSRF_COOKIE = "investment_csrf";
export const SESSION_SECONDS = 5 * 24 * 60 * 60;

export type Claims = { uid: string; auth_time: number; firebase?: { sign_in_provider?: string } };
export interface SessionAuth {
  verifyIdToken(token: string, checkRevoked: boolean): Promise<Claims>;
  createSessionCookie(token: string, options: { expiresIn: number }): Promise<string>;
  verifySessionCookie(cookie: string, checkRevoked: boolean): Promise<Claims>;
  revokeRefreshTokens(uid: string): Promise<void>;
}
export type SessionConfig = { ownerUid: string; origin: string };
export class SessionError extends Error {
  constructor(public readonly status = 401, public readonly code = "unauthorized", message = "Phiên đăng nhập không hợp lệ.") { super(message); }
}

export function sessionConfig(): SessionConfig {
  const config = { ownerUid: process.env.FIREBASE_OWNER_UID ?? "", origin: process.env.APP_ORIGIN ?? "" };
  if (!config.ownerUid || config.ownerUid.length > 128 || /[\x00-\x1f\x7f]/.test(config.ownerUid)) throw new SessionError(503, "auth_unavailable", "Chưa cấu hình xác thực.");
  cookieOptions(config);
  return config;
}

export function cookieOptions(config: SessionConfig) {
  let url: URL;
  try { url = new URL(config.origin); } catch { throw new SessionError(503, "auth_unavailable", "Chưa cấu hình địa chỉ ứng dụng."); }
  if (url.origin !== config.origin || !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) || !["http:", "https:"].includes(url.protocol)) {
    throw new SessionError(503, "auth_unavailable", "Địa chỉ ứng dụng phải là loopback.");
  }
  return { httpOnly: true, sameSite: "lax" as const, secure: url.protocol === "https:", path: "/", maxAge: SESSION_SECONDS };
}

export function assertRequestOrigin(request: Request, config: SessionConfig, mutation = false) {
  cookieOptions(config);
  // NextRequest normalizes loopback URL hostnames to localhost. Validate the
  // actual Host header against the configured authority, not that rewritten URL.
  const configured = new URL(config.origin);
  const received = new URL(request.url);
  if (request.headers.get("host") !== configured.host || received.protocol !== configured.protocol || received.port !== configured.port || (mutation && request.headers.get("origin") !== config.origin)) {
    throw new SessionError(403, "invalid_origin", "Nguồn yêu cầu không hợp lệ.");
  }
}

export function assertMutation(request: Request, csrfCookie: string | undefined, config: SessionConfig) {
  assertRequestOrigin(request, config, true);
  const token = request.headers.get("x-csrf-token");
  if (!token || !csrfCookie || !/^[a-f0-9]{64}$/.test(token) || !/^[a-f0-9]{64}$/.test(csrfCookie) || !timingSafeEqual(Buffer.from(token), Buffer.from(csrfCookie))) {
    throw new SessionError(403, "invalid_csrf", "Mã xác nhận yêu cầu không hợp lệ.");
  }
}

function assertOwner(claims: Claims, config: SessionConfig) {
  if (!config.ownerUid || claims.uid !== config.ownerUid || claims.firebase?.sign_in_provider !== "google.com") throw new SessionError();
}

export async function createOwnerSession(idToken: string, auth: SessionAuth, config: SessionConfig, now = Date.now() / 1000) {
  try {
    if (!idToken || idToken.length > 16384) throw new SessionError();
    const claims = await auth.verifyIdToken(idToken, true);
    assertOwner(claims, config);
    if (!Number.isFinite(claims.auth_time) || now - claims.auth_time > 300 || claims.auth_time > now + 30) throw new SessionError();
    return await auth.createSessionCookie(idToken, { expiresIn: SESSION_SECONDS * 1000 });
  } catch { throw new SessionError(); }
}

export async function verifyOwnerSession(cookie: string | undefined, auth: SessionAuth, config: SessionConfig) {
  try {
    if (!cookie || cookie.length > 16384) throw new SessionError();
    const claims = await auth.verifySessionCookie(cookie, true);
    assertOwner(claims, config);
    return { uid: claims.uid, role: "owner" as const };
  } catch { throw new SessionError(); }
}
